#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略18 - 中证500布林带策略：中证500股指期货布林带策略
原理：
    中证500股指期货（IC）使用布林带进行区间突破交易。
    价格突破布林带上轨时做多，下轨时做空。

参数：
    - 合约：中金所IC2506
    - K线周期：15分钟
    - 布林带周期：20
    - 标准差：2
    - 止损：2% 
    - 止盈：4%

适用行情：震荡行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import BOLL
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.IC2506"         # 中证500股指期货
KLINE_DURATION = 15 * 60        # 15分钟K线
BOLL_PERIOD = 20                 # 布林带周期
BOLL_STD = 2                    # 标准差倍数
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：中证500股指期货布林带策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=BOLL_PERIOD + 20)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < BOLL_PERIOD + 10:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算布林带
            boll = BOLL(klines['close'], period=BOLL_PERIOD, dev=BOLL_STD)
            upper = boll['up'].iloc[-1]
            lower = boll['down'].iloc[-1]
            middle = boll['mid'].iloc[-1]
            
            # 计算价格变化
            price_change = (current_price - klines['close'].iloc[-2]) / klines['close'].iloc[-2]
            
            print(f"价格: {current_price}, 上轨: {upper:.2f}, 中轨: {middle:.2f}, 下轨: {lower:.2f}")
            
            if position == 0:
                # 做多信号：价格突破上轨
                if current_price > upper:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 价格突破上轨: {current_price}")
                # 做空信号：价格突破下轨
                elif current_price < lower:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 价格突破下轨: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 价格回到中轨平仓
                elif current_price < middle:
                    print(f"[平仓] 价格回到中轨")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 价格回到中轨平仓
                elif current_price > middle:
                    print(f"[平仓] 价格回到中轨")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
