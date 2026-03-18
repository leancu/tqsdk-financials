#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 25
策略名称: 股指期货跨品种协整套利策略
生成日期: 2026-03-18
仓库地址: tqsdk-financials
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个跨品种协整套利策略，基于沪深300(IF)、中证500(IC)、中证1000(IM)
三个股指期货品种之间的长期均衡关系。当价差偏离理论均值时，
入场进行均值回归交易。

策略逻辑：
1. 计算IF-IC、IF-IM、IC-IM三个价差的协整关系
2. 使用滚动窗口计算价差的均值和标准差
3. 当价差偏离均值超过1.5个标准差时入场
4. 当价差回归均值时平仓
5. 每日收盘前平仓（不持隔夜仓）

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| PAIRS | 3个价差对 | 交易品种对 |
| LOOKBACK_PERIOD | 60 | 计算周期 |
| ZSCORE_ENTRY | 1.5 | 入场z-score阈值 |
| ZSCORE_EXIT | 0.3 | 出场z-score阈值 |
| LOT_SIZE | 1 | 单边开仓手数 |

【风险提示】

- 协整套利策略需关注协整关系变化
- 极端行情可能导致较大偏离
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time


# ============ 参数配置 ============
# 交易品种（注意使用近月合约，临近交割前切换）
SYMBOLS = {
    "IF": "CFFEX.IF2503",   # 沪深300
    "IC": "CFFEX.IC2503",   # 中证500
    "IM": "CFFEX.IM2503",   # 中证1000
}
KLINE_DURATION = 60 * 60 * 24       # 日K线
LOOKBACK_PERIOD = 60                # 计算周期
ZSCORE_ENTRY = 1.5                  # 入场z-score阈值
ZSCORE_EXIT = 0.3                   # 出场z-score阈值
LOT_SIZE = 1                        # 单边开仓手数
CLOSE_TIME = time(14, 55)           # 强平时间


class FuturesCointegrationStrategy:
    def __init__(self, api):
        self.api = api
        self.positions = {}      # pair_key -> position (1=多spread, -1=空spread)
        
    def get_close_prices(self):
        """获取各品种收盘价"""
        prices = {}
        for name, sym in SYMBOLS.items():
            try:
                klines = self.api.get_kline_serial(sym, KLINE_DURATION, 2)
                if len(klines) > 0:
                    prices[name] = klines['close'].values[-1]
            except Exception as e:
                print(f"获取价格失败 {name}: {e}")
        return prices
        
    def calculate_spread_history(self, sym1, sym2, period=60):
        """计算价差历史序列"""
        try:
            k1 = self.api.get_kline_serial(SYMBOLS[sym1], KLINE_DURATION, period + 1)
            k2 = self.api.get_kline_serial(SYMBOLS[sym2], KLINE_DURATION, period + 1)
            if len(k1) < period + 1 or len(k2) < period + 1:
                return None
            # 标准化后相减得到spread
            spread = k1['close'].values - k2['close'].values
            return spread
        except Exception:
            return None
            
    def calculate_zscore(self, spread):
        """计算当前z-score"""
        if spread is None or len(spread) < 10:
            return 0
        recent = spread[-LOOKBACK_PERIOD:]
        mean = np.mean(recent)
        std = np.std(recent)
        if std == 0:
            return 0
        current = spread[-1]
        return (current - mean) / std
        
    def check_pair_signals(self, sym1, sym2):
        """检查配对信号"""
        spread = self.calculate_spread_history(sym1, sym2, LOOKBACK_PERIOD + 5)
        if spread is None:
            return 0, False, False
        
        zscore = self.calculate_zscore(spread)
        pair_key = f"{sym1}_{sym2}"
        current_pos = self.positions.get(pair_key, 0)
        
        # 入场信号
        entry = False
        if abs(zscore) > ZSCORE_ENTRY and current_pos == 0:
            entry = True
            
        # 出场信号
        exit_signal = False
        if current_pos != 0 and abs(zscore) < ZSCORE_EXIT:
            exit_signal = True
            
        return zscore, entry, exit_signal
        
    def open_pair_position(self, sym1, sym2, zscore):
        """开仓"""
        pair_key = f"{sym1}_{sym2}"
        try:
            if zscore > ZSCORE_ENTRY:
                # spread偏高 -> 做空sym1，做多sym2（预期回归）
                self.api.insert_order(symbol=SYMBOLS[sym1], direction="SELL", offset="OPEN", volume=LOT_SIZE)
                self.api.insert_order(symbol=SYMBOLS[sym2], direction="BUY", offset="OPEN", volume=LOT_SIZE)
                self.positions[pair_key] = -1
                print(f"[{datetime.now()}] 开空{sym1}/多{sym2} spread, z={zscore:.3f}")
            elif zscore < -ZSCORE_ENTRY:
                # spread偏低 -> 做多sym1，做空sym2
                self.api.insert_order(symbol=SYMBOLS[sym1], direction="BUY", offset="OPEN", volume=LOT_SIZE)
                self.api.insert_order(symbol=SYMBOLS[sym2], direction="SELL", offset="OPEN", volume=LOT_SIZE)
                self.positions[pair_key] = 1
                print(f"[{datetime.now()}] 开多{sym1}/空{sym2} spread, z={zscore:.3f}")
        except Exception as e:
            print(f"开仓失败 {pair_key}: {e}")
            
    def close_pair_position(self, sym1, sym2):
        """平仓"""
        pair_key = f"{sym1}_{sym2}"
        if pair_key not in self.positions:
            return
        try:
            pos = self.positions[pair_key]
            if pos == 1:
                # 平多sym1，空sym2
                self.api.insert_order(symbol=SYMBOLS[sym1], direction="SELL", offset="CLOSE", volume=LOT_SIZE)
                self.api.insert_order(symbol=SYMBOLS[sym2], direction="BUY", offset="CLOSE", volume=LOT_SIZE)
            elif pos == -1:
                # 平空sym1，多sym2
                self.api.insert_order(symbol=SYMBOLS[sym1], direction="BUY", offset="CLOSE", volume=LOT_SIZE)
                self.api.insert_order(symbol=SYMBOLS[sym2], direction="SELL", offset="CLOSE", volume=LOT_SIZE)
            del self.positions[pair_key]
            print(f"[{datetime.now()}] 平仓 {pair_key}")
        except Exception as e:
            print(f"平仓失败 {pair_key}: {e}")
            
    def close_all(self):
        """平所有仓"""
        for pair_key in list(self.positions.keys()):
            syms = pair_key.split("_")
            self.close_pair_position(syms[0], syms[1])
            
    def run(self):
        """主运行循环"""
        print("=" * 60)
        print("股指期货跨品种协整套利策略启动")
        print("=" * 60)
        
        pairs = [
            ("IF", "IC"),
            ("IF", "IM"),
            ("IC", "IM"),
        ]
        
        last_trade_date = None
        
        while True:
            self.api.wait_update()
            
            now = datetime.now()
            trade_date = now.strftime("%Y-%m-%d")
            
            # 强平检查
            if now.time() >= CLOSE_TIME:
                self.close_all()
                continue
                
            # 每日评估
            if last_trade_date != trade_date:
                last_trade_date = trade_date
                print(f"\n[{trade_date}] 检查套利信号...")
                
                for sym1, sym2 in pairs:
                    zscore, entry, exit_signal = self.check_pair_signals(sym1, sym2)
                    pair_key = f"{sym1}_{sym2}"
                    current_pos = self.positions.get(pair_key, 0)
                    
                    print(f"[{sym1}-{sym2}] z={zscore:.3f} pos={current_pos}")
                    
                    if exit_signal and current_pos != 0:
                        self.close_pair_position(sym1, sym2)
                    elif entry:
                        self.open_pair_position(sym1, sym2, zscore)


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 模拟测试
    # api = TqApi(auth=TqSim())
    
    try:
        strategy = FuturesCointegrationStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
