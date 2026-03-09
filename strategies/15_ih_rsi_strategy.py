#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略15 - RSI策略：上证50股指期货RSI超买超卖策略
原理：
    上证50股指期货（IH）使用RSI指标判断超买超卖。
    RSI低于30时做多，RSI高于70时做空，RSI回到50时平仓。

参数：
    - 合约：中金所IH2506
    - K线周期：15分钟
    - RSI周期：14
    - 止损：2% 
    - 止盈：4%

适用行情：震荡整理行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import RSI
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.IH2506"         # 上证50股指期货
KLINE_DURATION = 15 * 60        # 15分钟K线
RSI_PERIOD = 14                 # RSI周期
RSI_OVERSOLD = 30               # RSI超卖阈值
RSI_OVERBOUGHT = 70             # RSI超买阈值
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：上证50股指期货RSI超买超卖策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=RSI_PERIOD + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < RSI_PERIOD:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算RSI
            rsi = RSI(klines['close'], RSI_PERIOD).iloc[-1]
            
            print(f"价格: {current_price}, RSI: {rsi:.2f}")
            
            if position == 0:
                # 做多信号：RSI超卖
                if rsi < RSI_OVERSOLD:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] RSI超卖: {rsi:.2f}")
                # 做空信号：RSI超买
                elif rsi > RSI_OVERBOUGHT:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] RSI超买: {rsi:.2f}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # RSI回到50以上平仓
                elif rsi > 50:
                    print(f"[平仓] RSI回到中性区域: {rsi:.2f}")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # RSI回到50以下平仓
                elif rsi < 50:
                    print(f"[平仓] RSI回到中性区域: {rsi:.2f}")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
