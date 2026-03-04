#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略10 - 国债期货趋势策略
原理：
    基于国债期货的均线交叉进行趋势交易。
    当短均线上穿长均线时做多，下穿时做空。

参数：
    - 合约：CFFEX.TS2506
    - 周期：30分钟
    - 短期均线：10
    - 长期均线：30
    - 止损：0.3%

适用行情：债券趋势行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.TS2506"          # 10年期国债期货
KLINE_DURATION = 30 * 60        # 30分钟K线
FAST_MA = 10                     # 快速均线
SLOW_MA = 30                     # 慢速均线
STOP_LOSS = 0.003               # 0.3%止损

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：国债期货趋势策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=SLOW_MA + 10)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < SLOW_MA + 5:
                continue
            
            # 计算均线
            fast_ma = klines['close'].iloc[-FAST_MA:].mean()
            slow_ma = klines['close'].iloc[-SLOW_MA:].mean()
            current_price = klines['close'].iloc[-1]
            
            print(f"价格: {current_price}, 快线: {fast_ma:.4f}, 慢线: {slow_ma:.4f}")
            
            if position == 0:
                # 金叉做多
                if fast_ma > slow_ma:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 金叉，快线上穿慢线")
                # 死叉做空
                elif fast_ma < slow_ma:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 死叉，快线下穿慢线")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}")
                    position = 0
                elif fast_ma < slow_ma:
                    print(f"[平仓] 死叉")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}")
                    position = 0
                elif fast_ma > slow_ma:
                    print(f"[平仓] 金叉")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
