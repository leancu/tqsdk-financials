#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略04 - 中证500与沪深300价差策略
原理：
    中证500（IC）和沪深300（IF）存在稳定的联动关系。
    两者都是股指期货，但成分股不同。
    当价差偏离历史均值时，进行均值回归交易。

参数：
    - 价差周期：60根K线
    - 开仓阈值：1.5倍标准差
    - 平仓阈值：0.3倍标准差
    - 止损：2.5倍标准差

适用行情：价差偏离均值时
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
import numpy as np
import pandas as pd

# ============ 参数配置 ============
IC_SYMBOL = "IC2406"           # 中证500
IF_SYMBOL = "IF2406"          # 沪深300
KLINE_DURATION = 15 * 60       # K线周期：15分钟
WINDOW = 60                   # 价差滚动窗口
OPEN_THRESHOLD = 1.5           # 开仓阈值
CLOSE_THRESHOLD = 0.3         # 平仓阈值
STOP_THRESHOLD = 2.5          # 止损阈值
LOT_SIZE = 1                   # 开仓手数

def calc_zscore(spread_series):
    """计算价差的 Z-Score"""
    mean = np.mean(spread_series)
    std = np.std(spread_series)
    if std == 0:
        return 0.0
    return (spread_series[-1] - mean) / std

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：中证500-沪深300价差策略")
    
    ic_quote = api.get_quote(IC_SYMBOL)
    if_quote = api.get_quote(IF_SYMBOL)
    
    ic_klines = api.get_kline_serial(IC_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    if_klines = api.get_kline_serial(IF_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    position = 0  # 1: 做多价差(多IC空IF), -1: 做空价差(空IC多IF), 0: 空仓
    
    while True:
        api.wait_update()
        
        if len(ic_klines) < WINDOW or len(if_klines) < WINDOW:
            continue
        
        # 计算价差序列（IC - IF）
        ic_prices = [k['close'] for k in ic_klines[-WINDOW:]]
        if_prices = [k['close'] for k in if_klines[-WINDOW:]]
        
        spreads = [ic - if_ for ic, if_ in zip(ic_prices, if_prices)]
        zscore = calc_zscore(spreads)
        
        current_spread = spreads[-1]
        
        if position == 0:
            # 做多价差：价差过低（IC相对便宜）
            if zscore < -OPEN_THRESHOLD:
                print(f"价差={current_spread:.2f}, Z={zscore:.2f} → 做多价差(多IC空IF)")
                api.insert_order(symbol=IC_SYMBOL, direction="long", offset="open", volume=LOT_SIZE)
                api.insert_order(symbol=IF_SYMBOL, direction="short", offset="open", volume=LOT_SIZE)
                position = 1
            
            # 做空价差：价差过高（IC相对昂贵）
            elif zscore > OPEN_THRESHOLD:
                print(f"价差={current_spread:.2f}, Z={zscore:.2f} → 做空价差(空IC多IF)")
                api.insert_order(symbol=IC_SYMBOL, direction="short", offset="open", volume=LOT_SIZE)
                api.insert_order(symbol=IF_SYMBOL, direction="long", offset="open", volume=LOT_SIZE)
                position = -1
        
        elif position == 1:
            # 做多价差仓位平仓
            if zscore > -CLOSE_THRESHOLD or zscore < -STOP_THRESHOLD:
                print(f"价差={current_spread:.2f}, Z={zscore:.2f} → 平多价差仓位")
                api.insert_order(symbol=IC_SYMBOL, direction="short", offset="close", volume=LOT_SIZE)
                api.insert_order(symbol=IF_SYMBOL, direction="long", offset="close", volume=LOT_SIZE)
                position = 0
        
        elif position == -1:
            # 做空价差仓位平仓
            if zscore < CLOSE_THRESHOLD or zscore > STOP_THRESHOLD:
                print(f"价差={current_spread:.2f}, Z={zscore:.2f} → 平空价差仓位")
                api.insert_order(symbol=IC_SYMBOL, direction="long", offset="close", volume=LOT_SIZE)
                api.insert_order(symbol=IF_SYMBOL, direction="short", offset="close", volume=LOT_SIZE)
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
