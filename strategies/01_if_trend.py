"""
================================================================================
策略名称：沪深300股指期货日线趋势+小时线入场策略
文件名称：01_if_trend.py
合约品种：CFFEX.IF2503（沪深300股指期货2025年3月合约）
策略类型：趋势跟踪（日线方向过滤 + 小时线精确入场）
开发框架：TqSdk（天勤量化开发包）
创建日期：2026-03-02
版本号：v1.0
================================================================================

【TqSdk 框架简介】
TqSdk（天勤量化开发包）是由信易科技开发的专业量化交易开发框架，专为期货市场设计。
它提供了完整的数据获取、策略开发、回测、实盘交易一体化解决方案。

核心特性：
1. **实时数据**：支持全市场期货合约的 Tick 级别实时行情订阅，延迟极低。
2. **K线订阅**：支持任意周期 K 线（1s、1min、5min、1h、1d 等），并实时更新最新 K 线。
3. **回测引擎**：内置高精度回测引擎，支持 Tick 级别回测，可还原真实撮合过程。
4. **实盘对接**：直连期货公司交易系统，支持快期、TT、CTP 等主流接口。
5. **异步架构**：基于协程的异步架构，高效处理多合约并发策略。
6. **账户管理**：实时查询资金、持仓、委托、成交等账户信息。

TqSdk 策略开发流程：
- 实例化 TqApi（可传入回测参数 TqBacktest 或实盘账户 TqAccount）
- 订阅 K 线（api.get_kline_serial），获取 DataFrame 格式历史+实时 K 线
- 在主循环中调用 api.wait_update() 等待数据更新
- 检测到新 K 线或目标合约数据更新时执行策略逻辑
- 通过 api.insert_order() 下单，api.cancel_order() 撤单

【策略逻辑说明】
本策略采用经典的"大周期定方向、小周期找时机"双周期框架：

1. 日线趋势过滤：
   - 计算日线 20 周期 EMA（指数移动平均线）
   - 当日线收盘价 > 日线 EMA20：判断为多头趋势，只做多
   - 当日线收盘价 < 日线 EMA20：判断为空头趋势，只做空
   - 趋势过滤有效避免逆势交易，显著提升胜率

2. 小时线入场信号：
   - 计算小时 K 线的 MACD 指标（快线12，慢线26，信号线9）
   - 多头趋势下：MACD 金叉（DIF 向上穿越 DEA）触发做多
   - 空头趋势下：MACD 死叉（DIF 向下穿越 DEA）触发做空
   - MACD 作为动量确认指标，提升入场时机准确性

3. 止损止盈设置：
   - 固定止损：入场价格的 0.5%（约 20 个点，沪深300每点 300 元）
   - 固定止盈：入场价格的 1.0%（约 40 个点，风险回报比 1:2）
   - 每次只持有 1 手合约，严格控制风险

4. 仓位管理：
   - 同方向不重复开仓（已有持仓则跳过）
   - 出现反向信号时先平仓再反向开仓
   - 每日收盘前 30 分钟强制平仓（避免隔夜风险）

【风险提示】
期货交易具有高风险，本策略仅用于研究和学习目的。
实盘使用前请充分回测验证，并根据实际市场情况调整参数。
================================================================================
"""

import numpy as np
from datetime import time
from tqsdk import TqApi, TqAuth, TqBacktest, TqAccount
from tqsdk.tafunc import ema


# ============================================================
# 策略参数配置区域 —— 可根据需要调整
# ============================================================
SYMBOL = "CFFEX.IF2503"          # 交易合约：沪深300股指期货2503合约
TRADE_VOLUME = 1                  # 每次交易手数（股指期货1手=300元/点）

# 日线趋势参数
DAILY_EMA_PERIOD = 20             # 日线EMA均线周期（20日EMA）
DAILY_KLINE_LEN = 60             # 订阅日线K线数量

# 小时线MACD参数
MACD_FAST = 12                   # MACD快线周期
MACD_SLOW = 26                   # MACD慢线周期
MACD_SIGNAL = 9                  # MACD信号线周期
HOURLY_KLINE_LEN = 200           # 订阅小时K线数量

# 止损止盈参数
STOP_LOSS_PCT = 0.005            # 止损比例：入场价 × 0.5%
TAKE_PROFIT_PCT = 0.010          # 止盈比例：入场价 × 1.0%（风险回报比 1:2）

# 强制平仓时间：15:00（期货收盘前强制平仓）
FORCE_CLOSE_HOUR = 15
FORCE_CLOSE_MINUTE = 0


def calc_macd(close_series, fast=12, slow=26, signal=9):
    """
    手动计算 MACD 指标
    返回：(dif, dea, macd_bar)
    - DIF = EMA(fast) - EMA(slow)
    - DEA = EMA(DIF, signal)
    - MACD柱 = 2 × (DIF - DEA)
    """
    ema_fast = ema(close_series, fast)
    ema_slow = ema(close_series, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    macd_bar = 2 * (dif - dea)
    return dif, dea, macd_bar


def get_daily_trend(daily_klines):
    """
    判断日线趋势方向
    返回：1（多头）、-1（空头）、0（震荡/无明确趋势）
    """
    if len(daily_klines) < DAILY_EMA_PERIOD + 5:
        return 0   # 数据不足，不判断趋势

    close = daily_klines["close"]
    daily_ema = ema(close, DAILY_EMA_PERIOD)

    # 取倒数第2根K线（已完成收盘的K线，避免用未收盘数据）
    last_close = close.iloc[-2]
    last_ema = daily_ema.iloc[-2]

    if last_close > last_ema:
        return 1    # 多头趋势
    elif last_close < last_ema:
        return -1   # 空头趋势
    else:
        return 0    # 无明确趋势


def get_macd_signal(hourly_klines):
    """
    获取小时线MACD交叉信号
    返回：1（金叉做多）、-1（死叉做空）、0（无信号）
    """
    if len(hourly_klines) < MACD_SLOW + MACD_SIGNAL + 10:
        return 0

    close = hourly_klines["close"]
    dif, dea, _ = calc_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)

    # 检测K线倒数第2根（已完成），倒数第3根（上一根）
    # 金叉：前一根 DIF < DEA，当前 DIF > DEA
    if dif.iloc[-3] < dea.iloc[-3] and dif.iloc[-2] > dea.iloc[-2]:
        return 1    # MACD金叉，做多信号

    # 死叉：前一根 DIF > DEA，当前 DIF < DEA
    if dif.iloc[-3] > dea.iloc[-3] and dif.iloc[-2] < dea.iloc[-2]:
        return -1   # MACD死叉，做空信号

    return 0


def main():
    """
    策略主函数
    支持回测和实盘两种模式，通过注释切换
    """
    # ============================================================
    # 初始化 TqApi
    # 回测模式（注释掉实盘代码，取消注释以下两行）：
    # api = TqApi(backtest=TqBacktest(start_dt="2025-01-01", end_dt="2025-03-01"),
    #             auth=TqAuth("your_username", "your_password"))
    #
    # 实盘模式（取消注释以下行）：
    # api = TqApi(TqAccount("your_broker", "your_account", "your_password"),
    #             auth=TqAuth("your_username", "your_password"))
    #
    # 模拟盘模式（用于测试，无需实盘账户）：
    api = TqApi(auth=TqAuth("sim_user", "sim_password"))
    # ============================================================

    try:
        print(f"【策略启动】沪深300股指期货趋势策略 | 合约：{SYMBOL}")
        print(f"参数配置：日线EMA{DAILY_EMA_PERIOD} | MACD({MACD_FAST},{MACD_SLOW},{MACD_SIGNAL})")
        print(f"止损：{STOP_LOSS_PCT*100:.1f}% | 止盈：{TAKE_PROFIT_PCT*100:.1f}%")

        # 订阅行情数据
        quote = api.get_quote(SYMBOL)                                      # 实时行情
        daily_klines = api.get_kline_serial(SYMBOL, 86400, DAILY_KLINE_LEN)  # 日线K线（86400秒=1天）
        hourly_klines = api.get_kline_serial(SYMBOL, 3600, HOURLY_KLINE_LEN) # 小时K线（3600秒=1小时）

        # 获取账户和持仓信息
        account = api.get_account()
        position = api.get_position(SYMBOL)

        # 策略状态变量
        last_hourly_id = -1      # 上次处理的小时K线ID，用于检测新K线
        entry_price = 0.0        # 当前持仓入场价格
        stop_loss_price = 0.0    # 当前止损价格
        take_profit_price = 0.0  # 当前止盈价格

        print("【策略就绪】开始监听市场数据...")

        # ============================================================
        # 主循环：等待数据更新并执行策略逻辑
        # ============================================================
        while True:
            api.wait_update()    # 等待任意数据更新（阻塞直到有新数据）

            # ----------------------------------------------------------
            # 1. 检查强制平仓时间（收盘前平仓）
            # ----------------------------------------------------------
            current_time = quote.datetime
            if current_time:
                # 将时间戳转换为可比较的时间
                import datetime
                dt = datetime.datetime.fromtimestamp(current_time / 1e9)
                if dt.hour == FORCE_CLOSE_HOUR and dt.minute >= FORCE_CLOSE_MINUTE:
                    # 如果有多头持仓，强制平多
                    if position.pos_long > 0:
                        print(f"【强制平仓】收盘时间到，平多仓 {position.pos_long} 手")
                        api.insert_order(
                            symbol=SYMBOL,
                            direction="SELL",
                            offset="CLOSE",
                            volume=position.pos_long
                        )
                    # 如果有空头持仓，强制平空
                    if position.pos_short > 0:
                        print(f"【强制平仓】收盘时间到，平空仓 {position.pos_short} 手")
                        api.insert_order(
                            symbol=SYMBOL,
                            direction="BUY",
                            offset="CLOSE",
                            volume=position.pos_short
                        )

            # ----------------------------------------------------------
            # 2. 检查止损止盈（基于实时价格）
            # ----------------------------------------------------------
            current_price = quote.last_price
            if current_price and current_price == current_price:  # 检查非NaN

                # 多头止损/止盈检查
                if position.pos_long > 0 and entry_price > 0:
                    if current_price <= stop_loss_price:
                        print(f"【止损触发】多头止损 | 入场价:{entry_price:.2f} 当前:{current_price:.2f} 止损线:{stop_loss_price:.2f}")
                        api.insert_order(SYMBOL, "SELL", "CLOSE", position.pos_long)
                        entry_price = 0.0
                    elif current_price >= take_profit_price:
                        print(f"【止盈触发】多头止盈 | 入场价:{entry_price:.2f} 当前:{current_price:.2f} 止盈线:{take_profit_price:.2f}")
                        api.insert_order(SYMBOL, "SELL", "CLOSE", position.pos_long)
                        entry_price = 0.0

                # 空头止损/止盈检查
                if position.pos_short > 0 and entry_price > 0:
                    if current_price >= stop_loss_price:
                        print(f"【止损触发】空头止损 | 入场价:{entry_price:.2f} 当前:{current_price:.2f} 止损线:{stop_loss_price:.2f}")
                        api.insert_order(SYMBOL, "BUY", "CLOSE", position.pos_short)
                        entry_price = 0.0
                    elif current_price <= take_profit_price:
                        print(f"【止盈触发】空头止盈 | 入场价:{entry_price:.2f} 当前:{current_price:.2f} 止盈线:{take_profit_price:.2f}")
                        api.insert_order(SYMBOL, "BUY", "CLOSE", position.pos_short)
                        entry_price = 0.0

            # ----------------------------------------------------------
            # 3. 检测小时K线更新，执行信号逻辑
            # ----------------------------------------------------------
            # 只有当小时K线有新K线产生时才执行信号检测（避免重复信号）
            if api.is_changing(hourly_klines.iloc[-1], "datetime"):
                current_bar_id = hourly_klines.iloc[-1]["id"]

                if current_bar_id != last_hourly_id:
                    last_hourly_id = current_bar_id

                    # 获取日线趋势方向
                    daily_trend = get_daily_trend(daily_klines)

                    # 获取小时线MACD信号
                    macd_signal = get_macd_signal(hourly_klines)

                    print(f"【新K线】小时线更新 | 日线趋势:{'+多' if daily_trend==1 else '-空' if daily_trend==-1 else '震荡'} | MACD信号:{macd_signal}")

                    # --------------------------------------------------
                    # 信号处理：趋势方向与MACD信号一致时开仓
                    # --------------------------------------------------

                    # 做多条件：日线多头趋势 + MACD金叉
                    if daily_trend == 1 and macd_signal == 1:
                        if position.pos_long == 0:   # 无多仓才开仓
                            # 先平空仓（如有）
                            if position.pos_short > 0:
                                print(f"【平空建多】先平空仓 {position.pos_short} 手")
                                api.insert_order(SYMBOL, "BUY", "CLOSE", position.pos_short)

                            # 开多仓
                            entry_price = current_price
                            stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
                            take_profit_price = entry_price * (1 + TAKE_PROFIT_PCT)
                            print(f"【开多】价格:{entry_price:.2f} 止损:{stop_loss_price:.2f} 止盈:{take_profit_price:.2f}")
                            api.insert_order(SYMBOL, "BUY", "OPEN", TRADE_VOLUME)

                        else:
                            print(f"【忽略多信号】已有多仓 {position.pos_long} 手，跳过")

                    # 做空条件：日线空头趋势 + MACD死叉
                    elif daily_trend == -1 and macd_signal == -1:
                        if position.pos_short == 0:  # 无空仓才开仓
                            # 先平多仓（如有）
                            if position.pos_long > 0:
                                print(f"【平多建空】先平多仓 {position.pos_long} 手")
                                api.insert_order(SYMBOL, "SELL", "CLOSE", position.pos_long)

                            # 开空仓
                            entry_price = current_price
                            stop_loss_price = entry_price * (1 + STOP_LOSS_PCT)
                            take_profit_price = entry_price * (1 - TAKE_PROFIT_PCT)
                            print(f"【开空】价格:{entry_price:.2f} 止损:{stop_loss_price:.2f} 止盈:{take_profit_price:.2f}")
                            api.insert_order(SYMBOL, "SELL", "OPEN", TRADE_VOLUME)

                        else:
                            print(f"【忽略空信号】已有空仓 {position.pos_short} 手，跳过")

            # ----------------------------------------------------------
            # 4. 打印账户状态（每次循环简要记录）
            # ----------------------------------------------------------
            if api.is_changing(account):
                print(f"【账户】可用资金:{account.available:.2f} | 浮动盈亏:{account.float_profit:.2f} | 多:{position.pos_long}手 空:{position.pos_short}手")

    except Exception as e:
        print(f"【策略异常】{e}")
        raise

    finally:
        api.close()
        print("【策略停止】API连接已关闭")


# ============================================================
# 策略入口
# ============================================================
if __name__ == "__main__":
    main()
