#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略03 - 沪深300股指期货均值回归策略
原理：
    股指期货具有较强的均值回归特性，当价格偏离均线过多时，
    容易产生回归行情。
    
    本策略：
    1. 计算价格与均线的偏离度
    2. 当偏离超过阈值时反向交易
    3. 回归均线时平仓

参数：
    - 均线周期：20
    - 偏离阈值：2%
    - 持仓周期：日内

适用行情：震荡行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA
import pandas as pd

# ============ 参数配置 ============
SYMBOL = "IF2406"              # 沪深300股指期货
KLINE_DURATION = 5 * 60        # K线周期：5分钟
MA_PERIOD = 20                 # 均线周期
DEVIATION_THRESHOLD = 0.02     # 偏离阈值 2%
LOT_SIZE = 1                   # 开仓手数
CLOSE_HOUR = 14                # 强制平仓时间
CLOSE_MINUTE = 55

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print(f"启动：沪深300均值回归策略 | 合约: {SYMBOL}")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=MA_PERIOD + 10)
    
    position = 0  # 1: 多头, -1: 空头, 0: 空仓
    
    while True:
        api.wait_update(klines)
        
        if len(klines) < MA_PERIOD + 5:
            continue
        
        df = pd.DataFrame(klines)
        df['close'] = df['close'].astype(float)
        
        # 计算均线
        df['ma'] = MA(df['close'], MA_PERIOD)
        
        current_price = df['close'].iloc[-1]
        ma = df['ma'].iloc[-1]
        
        # 计算偏离度
        deviation = (current_price - ma) / ma
        
        # 尾盘平仓
        current_time = api.get_current_datetime()
        if current_time.hour >= CLOSE_HOUR and current_time.minute >= CLOSE_MINUTE:
            if position != 0:
                print(f"[{current_time}] 尾盘平仓")
                if position == 1:
                    api.insert_order(symbol=SYMBOL, direction="short", offset="close", volume=LOT_SIZE)
                else:
                    api.insert_order(symbol=SYMBOL, direction="long", offset="close", volume=LOT_SIZE)
                position = 0
            continue
        
        # 交易信号
        if position == 0:
            # 超卖：价格低于均线超过阈值，做多
            if deviation < -DEVIATION_THRESHOLD:
                print(f"做多 | 价格: {current_price}, 均线: {ma:.2f}, 偏离: {deviation:.2%}")
                api.insert_order(symbol=SYMBOL, direction="long", offset="open", volume=LOT_SIZE)
                position = 1
            
            # 超买：价格高于均线超过阈值，做空
            elif deviation > DEVIATION_THRESHOLD:
                print(f"做空 | 价格: {current_price}, 均线: {ma:.2f}, 偏离: {deviation:.2%}")
                api.insert_order(symbol=SYMBOL, direction="short", offset="open", volume=LOT_SIZE)
                position = -1
        
        elif position == 1:
            # 多头平仓：回归均线
            if deviation >= 0:
                print(f"平多 | 价格: {current_price}, 均线: {ma:.2f}, 偏离: {deviation:.2%}")
                api.insert_order(symbol=SYMBOL, direction="short", offset="close", volume=LOT_SIZE)
                position = 0
        
        elif position == -1:
            # 空头平仓：回归均线
            if deviation <= 0:
                print(f"平空 | 价格: {current_price}, 均线: {ma:.2f}, 偏离: {deviation:.2%}")
                api.insert_order(symbol=SYMBOL, direction="long", offset="close", volume=LOT_SIZE)
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
