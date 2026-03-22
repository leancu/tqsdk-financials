#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 25
策略名称: 股指期货订单流多空策略
生成日期: 2026-03-22
仓库地址: tqsdk-financials
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个基于订单流的截面多空策略，同时监控沪深300(IF)、中证500(IC)、
上证50(IH)三个股指期货，通过分析 tick 级别的订单流（主动买入/卖出压力）
来判断各品种的资金流向，做多资金流入最强的品种，做空最弱的品种。

策略逻辑：
1. 采集 tick 数据，计算累计订单流（Delta = 主动买成交量 - 主动卖成交量）
2. 每5分钟汇总一次各品种的订单流强度
3. 计算标准化订单流（Delta / 成交量）
4. 做多标准化订单流最强的品种，做空最弱的品种
5. 每日尾盘平仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOLS | IF/IC/IH | 交易品种列表 |
| TICK_WINDOW | 300 | tick 采样窗口（秒） |
| REBALANCE_MINUTES | 5 | 调仓间隔（分钟） |
| LOT_SIZE | 1 | 单边开仓手数 |
| FLOW_THRESHOLD | 0.02 | 订单流入场阈值 |
| CLOSE_TIME | 14:55 | 收盘平仓时间 |

【风险提示】

- 订单流数据需要高频采集，对网络要求较高
- 股指期货杠杆较高，请谨慎设置仓位
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta

# ============ 参数配置 ============
SYMBOLS = [
    "CFFEX.if2510",   # 沪深300
    "CFFEX.ic2510",   # 中证500
    "CFFEX.ih2510",   # 上证50
]
REBALANCE_MINUTES = 5            # 调仓间隔（分钟）
LOT_SIZE = 1                      # 开仓手数
FLOW_THRESHOLD = 0.02            # 订单流入场阈值
CLOSE_TIME = time(14, 55)        # 收盘平仓时间


class OrderFlowStrategy:
    """股指期货订单流多空策略"""

    def __init__(self, api):
        self.api = api
        self.position = {}         # symbol -> position
        self.tick_accumulators = {sym: [] for sym in SYMBOLS}
        self.last_rebalance_time = None
        self.flow_history = {sym: [] for sym in SYMBOLS}

    def collect_tick(self, symbol):
        """采集 tick 数据"""
        try:
            tick = self.api.get_tick_serial(symbol)
            if tick is not None and len(tick) > 0:
                last_tick = tick.iloc[-1]
                # 主动买 = 成交量变化 * 价格上涨为真
                # 这里用简化方法：累计成交量变化
                vol = last_tick.get('volume', 0)
                last_price = last_tick.get('last_price', 0)
                bid_vol = last_tick.get('bid_volume1', 0)
                ask_vol = last_tick.get('ask_volume1', 0)
                return {
                    'volume': vol,
                    'price': last_price,
                    'bid_vol': bid_vol,
                    'ask_vol': ask_vol,
                    'time': last_tick.get('datetime', '')
                }
        except Exception:
            pass
        return None

    def calculate_order_flow(self, symbol):
        """
        计算订单流（Delta = 主动买 - 主动卖）
        简化方法：用盘口挂单量变化估算
        """
        try:
            tick_serial = self.api.get_tick_serial(symbol)
            if tick_serial is None or len(tick_serial) < 10:
                return 0
            df = tick_serial.tail(60)  # 最近60个tick

            # 简化订单流：价格变化方向 * 成交量
            prices = df['close'].values
            volumes = df['volume'].values
            diffs = np.diff(volumes)

            # 价格涨为主动买，价格跌为主动卖
            price_changes = np.diff(prices)
            buy_volume = np.sum(diffs[price_changes > 0])
            sell_volume = np.sum(diffs[price_changes < 0])

            delta = buy_volume - abs(sell_volume)

            # 标准化
            total_vol = np.sum(diffs)
            if total_vol == 0:
                return 0
            normalized_flow = delta / total_vol
            return normalized_flow
        except Exception as e:
            return 0

    def get_flow_scores(self):
        """获取各品种订单流评分"""
        scores = {}
        for symbol in SYMBOLS:
            flow = self.calculate_order_flow(symbol)
            scores[symbol] = flow
            print(f"  {symbol}: 订单流={flow:.4f}")
        return scores

    def get_rankings(self, scores):
        """排名"""
        sorted_symbols = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_symbols

    def rebalance(self, rankings):
        """调仓"""
        if len(rankings) < 2:
            return

        long_symbol = rankings[0][0]
        short_symbol = rankings[-1][0]
        long_flow = rankings[0][1]
        short_flow = rankings[-1][1]

        # 检查阈值
        if abs(long_flow - short_flow) < FLOW_THRESHOLD:
            print("  订单流差异不足，等待...")
            return

        # 平掉所有非目标仓位
        for symbol in list(self.position.keys()):
            if symbol not in [long_symbol, short_symbol]:
                self.close_position(symbol)

        # 做多最强
        if self.position.get(long_symbol, 0) != LOT_SIZE:
            self.close_position(long_symbol)
            self.open_position(long_symbol, 1, LOT_SIZE)

        # 做空最弱
        if self.position.get(short_symbol, 0) != -LOT_SIZE:
            self.close_position(short_symbol)
            self.open_position(short_symbol, -1, LOT_SIZE)

        print(f"  -> 做多 {long_symbol}(流={long_flow:.4f}), 做空 {short_symbol}(流={short_flow:.4f})")

    def open_position(self, symbol, direction, volume):
        """开仓"""
        try:
            if direction > 0:
                self.api.insert_order(
                    symbol=symbol, direction="BUY", offset="OPEN", volume=volume
                )
            else:
                self.api.insert_order(
                    symbol=symbol, direction="SELL", offset="OPEN", volume=volume
                )
            self.position[symbol] = direction * volume
        except Exception as e:
            print(f"开仓失败 {symbol}: {e}")

    def close_position(self, symbol):
        """平仓"""
        try:
            pos = self.position.get(symbol, 0)
            if pos > 0:
                self.api.insert_order(
                    symbol=symbol, direction="SELL", offset="CLOSE", volume=pos
                )
            elif pos < 0:
                self.api.insert_order(
                    symbol=symbol, direction="BUY", offset="CLOSE", volume=abs(pos)
                )
            self.position[symbol] = 0
        except Exception as e:
            print(f"平仓失败 {symbol}: {e}")

    def should_rebalance(self):
        """判断是否应该调仓"""
        if self.last_rebalance_time is None:
            return True
        elapsed = (datetime.now() - self.last_rebalance_time).total_seconds()
        return elapsed >= REBALANCE_MINUTES * 60

    def should_close(self):
        """判断是否应该收盘平仓"""
        return datetime.now().time() >= CLOSE_TIME

    def run(self):
        """运行策略"""
        print("=" * 60)
        print("股指期货订单流多空策略启动")
        print(f"调仓间隔: {REBALANCE_MINUTES}分钟 | 收盘平仓: {CLOSE_TIME}")
        print("=" * 60)

        while True:
            self.api.wait_update()

            # 收盘前强平
            if self.should_close():
                print(f"\n[{datetime.now()}] 收盘前平仓")
                for symbol in list(self.position.keys()):
                    if self.position.get(symbol, 0) != 0:
                        self.close_position(symbol)
                break

            # 定期调仓
            if self.should_rebalance():
                print(f"\n[{datetime.now()}] 订单流评分:")
                scores = self.get_flow_scores()
                rankings = self.get_rankings(scores)
                self.rebalance(rankings)
                self.last_rebalance_time = datetime.now()


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    # 模拟测试
    # api = TqApi(auth=TqSim())

    try:
        strategy = OrderFlowStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
