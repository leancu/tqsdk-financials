#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略09 - 股指期货跨期策略
原理：
    基于股指期货不同到期月份合约的价差波动。
    当近月与远月价差超过阈值时顺势交易。

参数：
    - 近月合约：CFFEX.IF2505
    - 远月合约：CFFEX.IF2509
    - 周期：15分钟
    - 价差窗口：20根K线
    - 趋势阈值：30点

适用行情：指数趋势行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
NEAR_SYMBOL = "CFFEX.IF2505"     # 股指近月
FAR_SYMBOL = "CFFEX.IF2509"      # 股指远月
KLINE_DURATION = 15 * 60        # 15分钟K线
WINDOW = 20                     # 价差滚动窗口
TREND_THRESHOLD = 30            # 趋势阈值（点）

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：股指期货跨期策略")
    
    near_quote = api.get_quote(NEAR_SYMBOL)
    far_quote = api.get_quote(FAR_SYMBOL)
    
    near_klines = api.get_kline_serial(NEAR_SYMBOL, KLINE_DURATION, data_length=50)
    far_klines = api.get_kline_serial(FAR_SYMBOL, KLINE_DURATION, data_length=50)
    
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(near_klines) or api.is_changing(far_klines):
            near_price = near_quote.last_price
            far_price = far_quote.last_price
            
            if near_price <= 0 or far_price <= 0:
                continue
            
            spread = far_price - near_price
            
            if len(near_klines) >= WINDOW + 5:
                spread_history = []
                for i in range(WINDOW):
                    f_p = far_klines['close'].iloc[-WINDOW+i]
                    n_p = near_klines['close'].iloc[-WINDOW+i]
                    spread_history.append(f_p - n_p)
                
                spread_ma = np.mean(spread_history)
                trend = spread - spread_ma
                
                print(f"近月: {near_price}, 远月: {far_price}, 价差: {spread}, 均值: {spread_ma:.2f}, 趋势: {trend:.2f}")
                
                if position == 0:
                    if trend > TREND_THRESHOLD:
                        position = 1
                        print(f"[开仓] 做多价差")
                    elif trend < -TREND_THRESHOLD:
                        position = -1
                        print(f"[开仓] 做空价差")
                
                elif position == 1 and trend < 0:
                    position = 0
                    print(f"[平仓] 趋势反转")
                elif position == -1 and trend > 0:
                    position = 0
                    print(f"[平仓] 趋势反转")
    
    api.close()

if __name__ == "__main__":
    main()
