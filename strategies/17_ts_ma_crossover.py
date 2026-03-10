#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略17 - 国债期货趋势策略：中金所国债期货双均线策略
原理：
    国债期货（TS）使用双均线交叉来判断趋势。
    快速均线上穿慢速均线时做多，下穿时做空。

参数：
    - 合约：中金所TS2506
    - K线周期：15分钟
    - 快速均线：10周期
    - 慢速均线：30周期
    - 止损：0.8% 
    - 止盈：1.5%

适用行情：趋势明显的单边行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.TS2506"         # 国债期货
KLINE_DURATION = 15 * 60        # 15分钟K线
FAST_MA = 10                    # 快速均线周期
SLOW_MA = 30                    # 慢速均线周期
STOP_LOSS = 0.008               # 0.8%止损
TAKE_PROFIT = 0.015             # 1.5%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：国债期货双均线交叉策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=SLOW_MA + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < SLOW_MA:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算均线
            fast_ma = MA(klines['close'], FAST_MA).iloc[-1]
            slow_ma = MA(klines['close'], SLOW_MA).iloc[-1]
            fast_ma_prev = MA(klines['close'], FAST_MA).iloc[-2]
            slow_ma_prev = MA(klines['close'], SLOW_MA).iloc[-2]
            
            print(f"价格: {current_price}, 快速均线: {fast_ma:.4f}, 慢速均线: {slow_ma:.4f}")
            
            if position == 0:
                # 做多信号：快速均线上穿慢速均线
                if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 金叉: 快速均线上穿慢速均线: {current_price}")
                # 做空信号：快速均线下穿慢速均线
                elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 死叉: 快速均线下穿慢速均线: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 死叉平仓
                elif fast_ma < slow_ma:
                    print(f"[平仓] 死叉: 快速均线下穿慢速均线")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 金叉平仓
                elif fast_ma > slow_ma:
                    print(f"[平仓] 金叉: 快速均线上穿慢速均线")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
