#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略06 - 跨品种套利：IF-IC价差回归策略
原理：
    IF（沪深300）和 IC（中证500）走势高度相关，价差会回归。
    当价差偏离均值时进行套利。

参数：
    - IF合约：CFFEX.IF2505
    - IC合约：CFFEX.IC2505
    - 价差窗口：60根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：.30倍标准差

适用行情：价差偏离均值时
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
IF_SYMBOL = "CFFEX.IF2505"       # 沪深300
IC_SYMBOL = "CFFEX.IC2505"      # 中证500
KLINE_DURATION = 60 * 60        # 1小时K线
WINDOW = 60                      # 窗口
OPEN_THRESHOLD = 1.5            # 开仓阈值
CLOSE_THRESHOLD = 0.3           # 平仓阈值

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：IF-IC跨品种套利策略")
    
    if_quote = api.get_quote(IF_SYMBOL)
    ic_quote = api.get_quote(IC_SYMBOL)
    
    if_klines = api.get_kline_serial(IF_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    ic_klines = api.get_kline_serial(IC_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    spread_history = []
    position = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(if_quote) or api.is_changing(ic_quote):
            if_price = if_quote.last_price
            ic_price = ic_quote.last_price
            
            if if_price <= 0 or ic_price <= 0:
                continue
                
            spread = if_price - ic_price
            spread_history.append(spread)
            
            if len(spread_history) < WINDOW:
                continue
                
            recent = spread_history[-WINDOW:]
            zscore = (spread - np.mean(recent)) / np.std(recent)
            
            print(f"IF: {if_price}, IC: {ic_price}, 价差: {spread:.2f}, Z: {zscore:.2f}")
            
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空IF-IC价差")
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多IF-IC价差")
                    position = 1
                    
            elif position == 1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归")
                position = 0
            elif position == -1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归")
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
