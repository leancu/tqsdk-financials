#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略05 - 股指期货：IF趋势突破策略
原理：
    股指期货（IF）采用成交量加权突破策略。
    放量突破20日高点时做多，放量跌破20日低点时做空。

参数：
    - 合约：IF2505
    - 周期：20根K线
    - 成交量倍数：1.5
    - 止损：2%
    - 止盈：5%

适用行情：趋势明显的单边行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.IF2505"         # 股指期货
KLINE_DURATION = 60 * 60        # 1小时K线
LOOKBACK = 20                    # 周期
VOLUME_MULT = 1.5               # 成交量倍数
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.05              # 5%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：IF趋势突破策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=LOOKBACK + 10)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < LOOKBACK:
                continue
                
            recent = klines.iloc[-LOOKBACK:]
            highest = recent['high'].max()
            lowest = recent['low'].min()
            avg_volume = recent['volume'].mean()
            
            current_price = klines['close'].iloc[-1]
            current_volume = klines['volume'].iloc[-1]
            
            print(f"价格: {current_price}, 20日高: {highest:.2f}, 20日低: {lowest:.2f}, 量: {current_volume}")
            
            if position == 0:
                # 放量突破高点
                if current_price > highest and current_volume > avg_volume * VOLUME_MULT:
                    position = 1
                    entry_price = current_price
                    print(f"[买入突破] 价格: {current_price}, 放量: {current_volume/avg_volume:.2f}倍")
                    
                # 放量跌破低点
                elif current_price < lowest and current_volume > avg_volume * VOLUME_MULT:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出突破] 价格: {current_price}, 放量: {current_volume/avg_volume:.2f}倍")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}")
                    position = 0
                elif current_price < lowest:
                    print(f"[平仓] 跌破20日低点")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}")
                    position = 0
                elif current_price > highest:
                    print(f"[平仓] 突破20日高点")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
