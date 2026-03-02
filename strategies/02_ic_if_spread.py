"""
================================================================================
策略名称：IC/IF股指期货价差对冲策略（大小盘轮动均值回归）
文件名称：02_ic_if_spread.py
合约品种：CFFEX.IC2503（中证500股指期货）+ CFFEX.IF2503（沪深300股指期货）
策略类型：统计套利 / 配对交易（Pairs Trading）—— IC-IF价差均值回归
开发框架：TqSdk（天勤量化开发包）
创建日期：2026-03-02
版本号：v1.0
================================================================================

【TqSdk 框架简介】
TqSdk（天勤量化开发包）是由信易科技开发的专业量化交易开发框架，专注于中国期货市场。
它将数据获取、策略逻辑、回测验证和实盘交易无缝整合，是量化期货领域最主流的开发工具之一。

核心模块说明：
1. **TqApi**：核心 API 对象，是整个 TqSdk 的入口。可连接实盘账户（TqAccount）、
   模拟账户或回测引擎（TqBacktest）。所有数据订阅、下单、查询均通过此对象完成。

2. **get_kline_serial()**：获取 K 线序列，返回 Pandas DataFrame，包含 open/high/low/close/
   volume/open_oi 等字段，并实时自动更新最新 K 线。支持任意秒数周期（如 60=1min, 3600=1h）。

3. **get_quote()**：获取合约实时行情快照，包含最新价、买一/卖一价、持仓量等信息。
   通过 api.is_changing(quote) 可检测行情是否发生变化。

4. **insert_order()**：提交委托单。参数包括合约代码（symbol）、方向（direction: BUY/SELL）、
   开平标志（offset: OPEN/CLOSE）、委托量（volume）和价格（price，不填则为市价单）。

5. **wait_update()**：策略主循环的核心方法。阻塞当前协程直到任意订阅数据发生更新，
   确保策略在数据驱动模式下运行，避免无效轮询消耗资源。

6. **TqBacktest**：回测引擎，支持指定起止日期，基于 Tick 数据精确模拟撮合过程，
   保证回测结果贴近真实交易。

TqSdk 的设计理念是"让量化交易像写 Python 脚本一样简单"，极大降低了期货量化策略的开发门槛。

【策略逻辑说明——IC/IF价差均值回归（大小盘轮动）】

一、策略背景与原理：

IC（中证500股指期货）代表中小盘股票走势，IF（沪深300股指期货）代表大盘蓝筹股走势。
历史上，IC 与 IF 的点位比值（IC/IF 或 IC-IF 价差归一化）在一定范围内震荡，
呈现出均值回归特性，这是实施统计套利的基础。

当市场风格偏向小盘股时（小盘股相对强势），IC 相对 IF 涨幅更大，价差扩大到高位；
当市场风格回归大盘时（大盘蓝筹相对强势），IC 相对 IF 下跌更多，价差收缩回均值。

利用这种"价差总会回到历史均值"的特性，可以在价差偏高时做空价差（空IC多IF），
在价差偏低时做多价差（多IC空IF），等待均值回归获利。

二、价差计算方式：

本策略使用"归一化价差"避免绝对价格量纲问题：
    归一化价差 = (IC收盘价 - IF收盘价) / IF收盘价 × 100（以百分比表示）

三、交易信号生成：

1. 计算最近 N 根 K 线（默认60根小时线）的归一化价差序列
2. 计算价差的滚动均值（mean）和标准差（std）
3. 布林带上轨 = mean + k × std（默认k=1.5）
4. 布林带下轨 = mean - k × std
5. 入场信号：
   - 价差突破上轨（IC相对强势，价差偏高）→ 做空价差：空IC + 多IF
   - 价差突破下轨（IF相对强势，价差偏低）→ 做多价差：多IC + 空IF
6. 出场信号：
   - 价差回归均值（回到 mean ± 0.3×std 区间）→ 平仓
   - 或触发最大亏损止损（价差进一步扩大至 2.5×std）→ 强制平仓

四、对冲比例设计：

IC 和 IF 的合约乘数不同（IC=200元/点，IF=300元/点），为使两腿名义价值接近：
    对冲比例 = round((IF价格 × 300) / (IC价格 × 200))
    即通常约为 1:1 到 2:1 不等，本策略简化为等手数（各1手）以便演示。

五、风险控制：

1. 最大亏损止损：价差偏离超过 2.5 个标准差时强制平仓
2. 收盘强制平仓：避免隔夜持仓风险
3. 两腿同步下单：先下主腿，再下对冲腿，尽量减少腿差风险
4. 单次交易量控制：每次仅开 1 手

【注意事项】
- IC 和 IF 合约均需足够的保证金（股指期货保证金率约 12-15%）
- 实盘需注意滑点和手续费对套利空间的侵蚀
- 本策略不适合流动性差的时段（如午休和收盘前最后几分钟）
- 建议回测时间不少于1年以验证策略的稳健性

【风险提示】
期货交易具有较高风险，套利策略并非无风险，请谨慎评估后使用。
================================================================================
"""

import numpy as np
import pandas as pd
from datetime import datetime
from tqsdk import TqApi, TqAuth, TqBacktest, TqAccount


# ============================================================
# 策略参数配置区域
# ============================================================

# 合约代码
SYMBOL_IC = "CFFEX.IC2503"    # 中证500股指期货（小盘股代表）
SYMBOL_IF = "CFFEX.IF2503"    # 沪深300股指期货（大盘股代表）

# 合约乘数（用于名义价值计算，参考）
MULT_IC = 200    # IC合约：每点200元
MULT_IF = 300    # IF合约：每点300元

# 交易手数（每腿各1手，简化演示）
TRADE_VOLUME = 1

# K线参数
KLINE_PERIOD = 3600       # 小时线（3600秒）
KLINE_LEN = 120           # 订阅K线数量（用于均值计算）

# 价差均值回归参数
SPREAD_WINDOW = 60        # 滚动窗口：计算均值和标准差的K线数量
ENTRY_Z = 1.5             # 开仓阈值：价差偏离均值多少个标准差时开仓
EXIT_Z = 0.3              # 平仓阈值：价差回归至均值 ±EXIT_Z 个标准差时平仓
STOP_Z = 2.5              # 止损阈值：价差偏离超过此值时强制止损

# 强制平仓时间
FORCE_CLOSE_HOUR = 14
FORCE_CLOSE_MINUTE = 45


# ============================================================
# 辅助函数
# ============================================================

def calc_normalized_spread(ic_close, if_close):
    """
    计算归一化价差序列
    归一化价差 = (IC - IF) / IF × 100（百分比）
    使用百分比形式避免绝对价格影响
    """
    spread = (ic_close - if_close) / if_close * 100
    return spread


def calc_spread_stats(spread_series, window):
    """
    计算价差的滚动均值和标准差
    返回：(mean, std, upper_band, lower_band)
    - upper_band = mean + ENTRY_Z × std
    - lower_band = mean - ENTRY_Z × std
    """
    if len(spread_series) < window:
        return None, None, None, None

    recent = spread_series.iloc[-window:]
    mean = recent.mean()
    std = recent.std()

    if std == 0 or np.isnan(std):
        return mean, std, None, None

    upper_band = mean + ENTRY_Z * std
    lower_band = mean - ENTRY_Z * std
    return mean, std, upper_band, lower_band


def calc_z_score(current_spread, mean, std):
    """
    计算当前价差的 Z-score
    Z-score = (当前价差 - 均值) / 标准差
    Z-score > 0：价差高于均值（IC相对强势）
    Z-score < 0：价差低于均值（IF相对强势）
    """
    if std is None or std == 0:
        return 0
    return (current_spread - mean) / std


# ============================================================
# 策略状态管理
# ============================================================

class SpreadPosition:
    """
    管理IC/IF价差持仓状态
    position_type:
      0 = 无持仓
      1 = 做多价差（多IC + 空IF）—— 价差偏低时买入
     -1 = 做空价差（空IC + 多IF）—— 价差偏高时卖出
    """
    def __init__(self):
        self.position_type = 0       # 当前持仓方向
        self.entry_spread = 0.0      # 入场时的价差值
        self.entry_ic_price = 0.0    # IC入场价格
        self.entry_if_price = 0.0    # IF入场价格

    def reset(self):
        """重置持仓状态"""
        self.position_type = 0
        self.entry_spread = 0.0
        self.entry_ic_price = 0.0
        self.entry_if_price = 0.0

    def __str__(self):
        type_str = {0: "空仓", 1: "多价差(多IC空IF)", -1: "空价差(空IC多IF)"}
        return (f"持仓={type_str.get(self.position_type,'未知')} | "
                f"入场价差={self.entry_spread:.4f}% | "
                f"IC入场={self.entry_ic_price:.2f} IF入场={self.entry_if_price:.2f}")


# ============================================================
# 下单辅助函数
# ============================================================

def open_long_spread(api, ic_quote, if_quote, spread_pos):
    """
    做多价差：多IC + 空IF
    价差偏低时（IC相对弱势），预期价差将回归上涨
    """
    print(f"【开仓-做多价差】IC现价:{ic_quote.last_price:.2f} IF现价:{if_quote.last_price:.2f}")
    print(f"  操作：买入IC {TRADE_VOLUME}手 + 卖出IF {TRADE_VOLUME}手")

    # 先开IC多仓
    order_ic = api.insert_order(
        symbol=SYMBOL_IC,
        direction="BUY",
        offset="OPEN",
        volume=TRADE_VOLUME,
    )
    # 再开IF空仓（对冲腿）
    order_if = api.insert_order(
        symbol=SYMBOL_IF,
        direction="SELL",
        offset="OPEN",
        volume=TRADE_VOLUME,
    )

    spread_pos.position_type = 1
    spread_pos.entry_ic_price = ic_quote.last_price
    spread_pos.entry_if_price = if_quote.last_price
    spread_pos.entry_spread = calc_normalized_spread(
        pd.Series([ic_quote.last_price]),
        pd.Series([if_quote.last_price])
    ).iloc[-1]

    return order_ic, order_if


def open_short_spread(api, ic_quote, if_quote, spread_pos):
    """
    做空价差：空IC + 多IF
    价差偏高时（IC相对强势），预期价差将回归下跌
    """
    print(f"【开仓-做空价差】IC现价:{ic_quote.last_price:.2f} IF现价:{if_quote.last_price:.2f}")
    print(f"  操作：卖出IC {TRADE_VOLUME}手 + 买入IF {TRADE_VOLUME}手")

    # 先开IC空仓
    order_ic = api.insert_order(
        symbol=SYMBOL_IC,
        direction="SELL",
        offset="OPEN",
        volume=TRADE_VOLUME,
    )
    # 再开IF多仓（对冲腿）
    order_if = api.insert_order(
        symbol=SYMBOL_IF,
        direction="BUY",
        offset="OPEN",
        volume=TRADE_VOLUME,
    )

    spread_pos.position_type = -1
    spread_pos.entry_ic_price = ic_quote.last_price
    spread_pos.entry_if_price = if_quote.last_price
    spread_pos.entry_spread = calc_normalized_spread(
        pd.Series([ic_quote.last_price]),
        pd.Series([if_quote.last_price])
    ).iloc[-1]

    return order_ic, order_if


def close_spread_position(api, spread_pos, ic_position, if_position, reason="均值回归"):
    """
    平仓价差头寸（同时平IC和IF）
    """
    print(f"【平仓】原因:{reason} | {spread_pos}")

    if spread_pos.position_type == 1:
        # 平多价差：卖IC + 买IF
        if ic_position.pos_long > 0:
            api.insert_order(SYMBOL_IC, "SELL", "CLOSE", min(TRADE_VOLUME, ic_position.pos_long))
        if if_position.pos_short > 0:
            api.insert_order(SYMBOL_IF, "BUY", "CLOSE", min(TRADE_VOLUME, if_position.pos_short))
        print(f"  操作：卖出IC {TRADE_VOLUME}手 + 买入IF {TRADE_VOLUME}手")

    elif spread_pos.position_type == -1:
        # 平空价差：买IC + 卖IF
        if ic_position.pos_short > 0:
            api.insert_order(SYMBOL_IC, "BUY", "CLOSE", min(TRADE_VOLUME, ic_position.pos_short))
        if if_position.pos_long > 0:
            api.insert_order(SYMBOL_IF, "SELL", "CLOSE", min(TRADE_VOLUME, if_position.pos_long))
        print(f"  操作：买入IC {TRADE_VOLUME}手 + 卖出IF {TRADE_VOLUME}手")

    spread_pos.reset()


# ============================================================
# 策略主函数
# ============================================================

def main():
    """
    IC/IF价差对冲策略主函数
    策略逻辑：统计套利 + 均值回归

    回测模式：取消注释 TqBacktest 行，注释掉模拟盘行
    实盘模式：取消注释 TqAccount 行，注释掉模拟盘行
    """
    # ----------------------------------------------------------
    # 初始化 API（选择其中一种模式）
    # ----------------------------------------------------------
    # 回测模式：
    # api = TqApi(backtest=TqBacktest(start_dt="2025-01-01", end_dt="2025-03-01"),
    #             auth=TqAuth("your_username", "your_password"))
    #
    # 实盘模式：
    # api = TqApi(TqAccount("your_broker_id", "your_account", "your_password"),
    #             auth=TqAuth("your_username", "your_password"))
    #
    # 模拟盘（测试用）：
    api = TqApi(auth=TqAuth("sim_user", "sim_password"))
    # ----------------------------------------------------------

    try:
        print("=" * 60)
        print("【策略启动】IC/IF价差对冲策略（大小盘轮动均值回归）")
        print(f"合约：{SYMBOL_IC}（IC中证500）vs {SYMBOL_IF}（IF沪深300）")
        print(f"参数：窗口={SPREAD_WINDOW}根K线 | 开仓阈值=±{ENTRY_Z}σ | 平仓阈值=±{EXIT_Z}σ | 止损=±{STOP_Z}σ")
        print("=" * 60)

        # 订阅两个合约的K线和实时行情
        ic_klines = api.get_kline_serial(SYMBOL_IC, KLINE_PERIOD, KLINE_LEN)
        if_klines = api.get_kline_serial(SYMBOL_IF, KLINE_PERIOD, KLINE_LEN)
        ic_quote = api.get_quote(SYMBOL_IC)
        if_quote = api.get_quote(SYMBOL_IF)

        # 获取持仓和账户信息
        account = api.get_account()
        ic_position = api.get_position(SYMBOL_IC)
        if_position = api.get_position(SYMBOL_IF)

        # 价差持仓状态管理对象
        spread_pos = SpreadPosition()

        # 记录上一根K线ID，用于检测新K线
        last_bar_id = -1

        print("【就绪】开始监听市场，等待价差信号...")

        # ============================================================
        # 策略主循环
        # ============================================================
        while True:
            api.wait_update()   # 等待数据更新

            # ----------------------------------------------------------
            # 1. 强制平仓时间检查
            # ----------------------------------------------------------
            try:
                ic_time = ic_quote.datetime
                if ic_time:
                    dt = datetime.fromtimestamp(ic_time / 1e9)
                    if dt.hour == FORCE_CLOSE_HOUR and dt.minute >= FORCE_CLOSE_MINUTE:
                        if spread_pos.position_type != 0:
                            close_spread_position(api, spread_pos, ic_position, if_position, "强制收盘平仓")
                            print("【收盘平仓完成】所有持仓已平")
            except Exception as e:
                pass   # 时间解析异常不影响主逻辑

            # ----------------------------------------------------------
            # 2. 检测新小时K线，执行价差信号逻辑
            # ----------------------------------------------------------
            if api.is_changing(ic_klines.iloc[-1], "datetime") or \
               api.is_changing(if_klines.iloc[-1], "datetime"):

                current_bar_id = ic_klines.iloc[-1]["id"]
                if current_bar_id == last_bar_id:
                    continue
                last_bar_id = current_bar_id

                # 确保两个合约K线数据都足够
                if len(ic_klines) < SPREAD_WINDOW + 5 or len(if_klines) < SPREAD_WINDOW + 5:
                    print(f"【数据不足】IC={len(ic_klines)}根 IF={len(if_klines)}根，需要{SPREAD_WINDOW+5}根，等待数据积累...")
                    continue

                # 对齐两合约K线数据（取收盘价）
                ic_close = ic_klines["close"].reset_index(drop=True)
                if_close = if_klines["close"].reset_index(drop=True)

                # 计算归一化价差序列
                min_len = min(len(ic_close), len(if_close))
                ic_close = ic_close.iloc[-min_len:]
                if_close = if_close.iloc[-min_len:]
                spread_series = calc_normalized_spread(ic_close, if_close)

                # 当前价差（已收盘K线，取倒数第2根）
                current_spread = spread_series.iloc[-2]

                # 计算统计量
                mean, std, upper_band, lower_band = calc_spread_stats(
                    spread_series.iloc[:-1], SPREAD_WINDOW
                )

                if mean is None or std is None or std == 0:
                    print("【统计量计算失败】数据异常，跳过本根K线")
                    continue

                # 当前Z-score
                z_score = calc_z_score(current_spread, mean, std)

                print(f"\n【价差分析】当前价差={current_spread:.4f}% | Z={z_score:.3f} | "
                      f"均值={mean:.4f}% | 上轨={upper_band:.4f}% | 下轨={lower_band:.4f}%")
                print(f"  IC={ic_quote.last_price:.2f} IF={if_quote.last_price:.2f} | {spread_pos}")

                # --------------------------------------------------
                # 3. 平仓逻辑（优先于开仓）
                # --------------------------------------------------
                if spread_pos.position_type != 0:
                    # 检查均值回归平仓条件
                    if abs(z_score) <= EXIT_Z:
                        close_spread_position(api, spread_pos, ic_position, if_position,
                                            f"均值回归(Z={z_score:.3f})")
                        continue

                    # 检查止损条件（价差进一步扩大超过STOP_Z）
                    if spread_pos.position_type == 1 and z_score < -STOP_Z:
                        close_spread_position(api, spread_pos, ic_position, if_position,
                                            f"多价差止损(Z={z_score:.3f})")
                        continue

                    if spread_pos.position_type == -1 and z_score > STOP_Z:
                        close_spread_position(api, spread_pos, ic_position, if_position,
                                            f"空价差止损(Z={z_score:.3f})")
                        continue

                    print(f"  持仓中，Z={z_score:.3f}，等待回归...")

                # --------------------------------------------------
                # 4. 开仓逻辑
                # --------------------------------------------------
                elif spread_pos.position_type == 0:
                    # 价差突破上轨（IC相对强势，价差偏高）→ 做空价差
                    if z_score > ENTRY_Z:
                        print(f"【信号-做空价差】价差偏高(Z={z_score:.3f}>{ENTRY_Z}) → 空IC + 多IF")
                        open_short_spread(api, ic_quote, if_quote, spread_pos)

                    # 价差突破下轨（IF相对强势，价差偏低）→ 做多价差
                    elif z_score < -ENTRY_Z:
                        print(f"【信号-做多价差】价差偏低(Z={z_score:.3f}<-{ENTRY_Z}) → 多IC + 空IF")
                        open_long_spread(api, ic_quote, if_quote, spread_pos)

                    else:
                        print(f"  无信号，价差在正常范围内(|Z|={abs(z_score):.3f}<{ENTRY_Z})")

            # ----------------------------------------------------------
            # 5. 账户信息更新输出
            # ----------------------------------------------------------
            if api.is_changing(account):
                total_profit = account.float_profit
                print(f"【账户更新】浮动盈亏:{total_profit:.2f}元 | 可用:{account.available:.2f}元 | "
                      f"IC持仓(多{ic_position.pos_long}空{ic_position.pos_short}) "
                      f"IF持仓(多{if_position.pos_long}空{if_position.pos_short})")

    except KeyboardInterrupt:
        print("\n【手动停止】策略被用户中断")

    except Exception as e:
        print(f"【策略异常】{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        # 程序退出前确保平仓
        try:
            if spread_pos.position_type != 0:
                print("【退出平仓】策略退出，强制平仓...")
                close_spread_position(api, spread_pos, ic_position, if_position, "策略退出平仓")
        except Exception:
            pass
        api.close()
        print("【策略停止】TqSdk API 连接已关闭")


# ============================================================
# 策略入口
# ============================================================
if __name__ == "__main__":
    main()
