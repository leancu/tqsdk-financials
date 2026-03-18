#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 26
策略名称: 股指期货双均线趋势+波动率过滤策略
生成日期: 2026-03-18
仓库地址: tqsdk-financials
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个双均线趋势策略，增加了波动率过滤机制。交易沪深300(IF)期货，
在趋势明确且市场波动适中的环境下进行交易，避免在低波动（盘整）和
高波动（极端行情）时入场。

策略逻辑：
1. 使用双均线（10日/30日）判断趋势方向
2. 计算ATR波动率，当ATR处于历史中位区间（不过高也不过低）时允许交易
3. 金叉做多，死叉做空
4. 每日收盘前平仓（不持隔夜仓）

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL | IF主力合约 | 交易品种 |
| MA_SHORT | 10 | 短期均线周期 |
| MA_LONG | 30 | 长期均线周期 |
| ATR_PERIOD | 20 | ATR计算周期 |
| ATR_LOW_PCT | 0.3 | ATR下限百分位 |
| ATR_HIGH_PCT | 0.7 | ATR上限百分位 |
| LOT_SIZE | 1 | 开仓手数 |
| STOP_LOSS_ATR | 2.0 | 止损（ATR倍数） |
| TAKE_PROFIT_ATR | 3.0 | 止盈（ATR倍数） |

【风险提示】

- 双均线策略在趋势行情中有效，盘整期会产生亏损
- 波动率过滤可减少部分假信号，但无法完全避免
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time


# ============ 参数配置 ============
SYMBOL = "CFFEX.IF2503"           # 沪深300期货（近月）
KLINE_DURATION = 60 * 60 * 24      # 日K线
MA_SHORT = 10                       # 短期均线周期
MA_LONG = 30                        # 长期均线周期
ATR_PERIOD = 20                     # ATR计算周期
ATR_LOW_PCT = 0.3                   # ATR下限百分位（低于此值不交易）
ATR_HIGH_PCT = 0.7                  # ATR上限百分位（高于此值不交易）
LOT_SIZE = 1                        # 开仓手数
STOP_LOSS_ATR = 2.0                 # 止损（ATR倍数）
TAKE_PROFIT_ATR = 3.0              # 止盈（ATR倍数）
CLOSE_TIME = time(14, 55)           # 强平时间


class DualMaVolatilityFilterStrategy:
    def __init__(self, api):
        self.api = api
        self.position = 0           # 1=多头, -1=空头, 0=空仓
        self.entry_price = 0
        self.entry_atr = 0
        self.last_trade_date = None
        
    def calculate_ma(self, symbol, period):
        """计算均线"""
        try:
            klines = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 1)
            if len(klines) < period + 1:
                return 0
            closes = klines['close'].values
            return np.mean(closes[-period:])
        except Exception:
            return 0
            
    def calculate_atr(self, symbol, period=20):
        """计算ATR"""
        try:
            klines = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 2)
            if len(klines) < period + 2:
                return 0
            high = klines['high'].values
            low = klines['low'].values
            close = klines['close'].values
            tr1 = high[1:] - low[1:]
            tr2 = np.abs(high[1:] - close[:-1])
            tr3 = np.abs(low[1:] - close[:-1])
            tr = np.maximum(np.maximum(tr1, tr2), tr3)
            atr = np.mean(tr[-period:])
            return atr
        except Exception:
            return 0
            
    def get_atr_percentile(self, symbol, current_atr, period=60):
        """计算当前ATR在历史序列中的百分位"""
        try:
            klines = self.api.get_kline_serial(symbol, KLINE_DURATION, period + 2)
            if len(klines) < period + 2:
                return 0.5
            high = klines['high'].values
            low = klines['low'].values
            close = klines['close'].values
            tr1 = high[1:] - low[1:]
            tr2 = np.abs(high[1:] - close[:-1])
            tr3 = np.abs(low[1:] - close[:-1])
            tr = np.maximum(np.maximum(tr1, tr2), tr3)
            atr_series = np.array([np.mean(tr[max(0,i-ATR_PERIOD):i]) for i in range(ATR_PERIOD, len(tr)+1)])
            if len(atr_series) < 10:
                return 0.5
            percentile = (current_atr - np.min(atr_series)) / (np.max(atr_series) - np.min(atr_series) + 1e-9)
            return max(0, min(1, percentile))
        except Exception:
            return 0.5
            
    def check_signals(self):
        """检查交易信号"""
        ma_s = self.calculate_ma(SYMBOL, MA_SHORT)
        ma_l = self.calculate_ma(SYMBOL, MA_LONG)
        atr = self.calculate_atr(SYMBOL, ATR_PERIOD)
        atr_pct = self.get_atr_percentile(SYMBOL, atr)
        
        prices = {}
        try:
            klines = self.api.get_kline_serial(SYMBOL, KLINE_DURATION, MA_LONG + 1)
            if len(klines) >= MA_LONG + 1:
                prices['current'] = klines['close'].values[-1]
                prices['prev'] = klines['close'].values[-2]
                prices['prev_ma_s'] = np.mean(klines['close'].values[-MA_SHORT-1:-1])
                prices['prev_ma_l'] = np.mean(klines['close'].values[-MA_LONG-1:-1])
        except Exception:
            return None, atr, atr_pct
            
        # 均线交叉判断（前一根bar的相对位置）
        prev_cross = (prices['prev_ma_s'] - prices['prev_ma_l']) * (ma_s - ma_l)
        
        signal = 0  # 0=无信号, 1=金叉(做多), -1=死叉(做空)
        if prev_cross < 0 and ma_s > ma_l:
            signal = 1  # 金叉
        elif prev_cross > 0 and ma_s < ma_l:
            signal = -1  # 死叉
            
        print(f"[{datetime.now()}] MA10={ma_s:.2f} MA30={ma_l:.2f} ATR={atr:.2f} ATR%={atr_pct:.2f} signal={signal} pos={self.position}")
        
        return signal, atr, atr_pct, prices.get('current', 0)
        
    def open_long(self, price, atr):
        """开多仓"""
        if self.position == 0:
            self.api.insert_order(symbol=SYMBOL, direction="BUY", offset="OPEN", volume=LOT_SIZE)
            self.position = 1
            self.entry_price = price
            self.entry_atr = atr
            print(f"[{datetime.now()}] 开多 价格={price} ATR={atr:.2f}")
            
    def open_short(self, price, atr):
        """开空仓"""
        if self.position == 0:
            self.api.insert_order(symbol=SYMBOL, direction="SELL", offset="OPEN", volume=LOT_SIZE)
            self.position = -1
            self.entry_price = price
            self.entry_atr = atr
            print(f"[{datetime.now()}] 开空 价格={price} ATR={atr:.2f}")
            
    def close_position(self):
        """平仓"""
        if self.position == 1:
            self.api.insert_order(symbol=SYMBOL, direction="SELL", offset="CLOSE", volume=LOT_SIZE)
            print(f"[{datetime.now()}] 平多")
        elif self.position == -1:
            self.api.insert_order(symbol=SYMBOL, direction="BUY", offset="CLOSE", volume=LOT_SIZE)
            print(f"[{datetime.now()}] 平空")
        self.position = 0
        self.entry_price = 0
        self.entry_atr = 0
        
    def check_stop_loss_take_profit(self, current_price):
        """检查止损止盈"""
        if self.position == 0 or self.entry_atr == 0:
            return
        pnl = (current_price - self.entry_price) * self.position
        if self.position == 1:
            # 多头止损/止盈
            if current_price < self.entry_price - STOP_LOSS_ATR * self.entry_atr:
                print(f"[{datetime.now()}] 触发止损 pnl={pnl:.2f}")
                self.close_position()
            elif current_price > self.entry_price + TAKE_PROFIT_ATR * self.entry_atr:
                print(f"[{datetime.now()}] 触发止盈 pnl={pnl:.2f}")
                self.close_position()
        elif self.position == -1:
            # 空头止损/止盈
            if current_price > self.entry_price + STOP_LOSS_ATR * self.entry_atr:
                print(f"[{datetime.now()}] 触发止损 pnl={pnl:.2f}")
                self.close_position()
            elif current_price < self.entry_price - TAKE_PROFIT_ATR * self.entry_atr:
                print(f"[{datetime.now()}] 触发止盈 pnl={pnl:.2f}")
                self.close_position()
        
    def run(self):
        """主运行循环"""
        print("=" * 60)
        print("股指双均线+波动率过滤策略启动")
        print("=" * 60)
        
        last_trade_date = None
        
        while True:
            self.api.wait_update()
            
            now = datetime.now()
            trade_date = now.strftime("%Y-%m-%d")
            
            # 强平时间
            if now.time() >= CLOSE_TIME:
                self.close_position()
                continue
                
            # 每日评估
            if last_trade_date != trade_date:
                last_trade_date = trade_date
                print(f"\n[{trade_date}] 日线信号检查...")
                
                signal, atr, atr_pct, current_price = self.check_signals()
                
                if signal is None:
                    continue
                    
                # 波动率过滤：只在中位波动区间交易
                if signal != 0 and atr_pct >= ATR_LOW_PCT and atr_pct <= ATR_HIGH_PCT:
                    if signal == 1:
                        self.open_long(current_price, atr)
                    elif signal == -1:
                        self.open_short(current_price, atr)
                elif signal != 0:
                    print(f"波动率过滤: ATR百分位={atr_pct:.2f} 不在 [{ATR_LOW_PCT}, {ATR_HIGH_PCT}] 区间，不交易")
                    
            # 持仓中检查止损止盈
            if self.position != 0:
                try:
                    klines = self.api.get_kline_serial(SYMBOL, KLINE_DURATION, 2)
                    if len(klines) >= 2:
                        current = klines['close'].values[-1]
                        self.check_stop_loss_take_profit(current)
                except Exception:
                    pass


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 模拟测试
    # api = TqApi(auth=TqSim())
    
    try:
        strategy = DualMaVolatilityFilterStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
