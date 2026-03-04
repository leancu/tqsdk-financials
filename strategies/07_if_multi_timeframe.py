#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略07 - 趋势策略：股指期货多周期共振策略
原理：
    使用日线和4小时线的趋势共振来过滤假信号。
    只有当两个周期趋势一致时才开仓。

参数：
    - 合约：CFFEX.IF2505
    - 日线周期：日K
    - 4小时周期：4小时K
    - 均线参数：20
    - 止损：2%

适用行情：趋势共振时
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.IF2505"         # 沪深300
KLINE_DURATION_1 = 24 * 60 * 60 # 日线
KLINE_DURATION_2 = 4 * 60 * 60  # 4小时线
MA_PERIOD = 20                   # 均线周期
STOP_LOSS = 0.02                 # 2%止损

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：多周期共振策略")
    
    # 获取两个周期的K线
    klines_1d = api.get_kline_serial(SYMBOL, KLINE_DURATION_1, data_length=MA_PERIOD + 10)
    klines_4h = api.get_kline_serial(SYMBOL, KLINE_DURATION_2, data_length=MA_PERIOD + 10)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines_1d) or api.is_changing(klines_4h):
            if len(klines_1d) < MA_PERIOD or len(klines_4h) < MA_PERIOD:
                continue
                
            # 日线趋势
            ma_1d = MA(klines_1d, MA_PERIOD).iloc[-1]
            price_1d = klines_1d['close'].iloc[-1]
            trend_1d = 1 if price_1d > ma_1d else -1
            
            # 4小时趋势
            ma_4h = MA(klines_4h, MA_PERIOD).iloc[-1]
            price_4h = klines_4h['close'].iloc[-1]
            trend_4h = 1 if price_4h > ma_4h else -1
            
            print(f"日线: {price_1d:.2f}, MA: {ma_1d:.2f}, 趋势: {trend_1d}")
            print(f"4H: {price_4h:.2f}, MA: {ma_4h:.2f}, 趋势: {trend_4h}")
            
            # 共振判断
            if trend_1d == trend_4h:
                current_price = price_4h
                
                if position == 0:
                    if trend_1d == 1:
                        position = 1
                        entry_price = current_price
                        print(f"[买入] 多周期共振做多, 价格: {current_price}")
                    else:
                        position = -1
                        entry_price = current_price
                        print(f"[卖出] 多周期共振做空, 价格: {current_price}")
                        
                elif position == 1:
                    if trend_1d == -1:  # 共振结束
                        print(f"[平仓] 共振结束, 价格: {current_price}")
                        position = 0
                    elif current_price < entry_price * (1 - STOP_LOSS):
                        print(f"[止损] 价格: {current_price}")
                        position = 0
                        
                elif position == -1:
                    if trend_1d == 1:  # 共振结束
                        print(f"[平仓] 共振结束, 价格: {current_price}")
                        position = 0
                    elif current_price > entry_price * (1 + STOP_LOSS):
                        print(f"[止损] 价格: {current_price}")
                        position = 0
    
    api.close()

if __name__ == "__main__":
    main()
