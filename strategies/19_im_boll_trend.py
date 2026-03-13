#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略19 - 中证1000布林带趋势策略：金融期货布林带趋势策略
原理：
    中证1000指数期货(IM)使用布林带与动量指标结合的趋势策略。
    价格突破布林带上轨且动量正向时做多，下轨且动量负向时做空。

参数：
    - 合约：中金所IM2505
    - K线周期：1小时
    - 布林带周期：20，标准差：2
    - 动量周期：10
    - 止损：3%
    - 止盈：6%

适用行情：趋势明显的单边行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import BOLL
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.IM2505"         # 中证1000指数期货
KLINE_DURATION = 60 * 60       # 1小时K线
BOLL_PERIOD = 20                # 布林带周期
BOLL_STD = 2                   # 标准差倍数
MOMENTUM_PERIOD = 10           # 动量周期
STOP_LOSS = 0.03               # 3%止损
TAKE_PROFIT = 0.06             # 6%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：中证1000期货布林带趋势策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=BOLL_PERIOD + 50)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < BOLL_PERIOD + 20:
                continue
                
            close_prices = klines['close']
            current_price = close_prices.iloc[-1]
            
            # 计算布林带
            boll = BOLL(close_prices, period=BOLL_PERIOD, dev=BOLL_STD)
            upper = boll['up'].iloc[-1]
            lower = boll['down'].iloc[-1]
            middle = boll['mid'].iloc[-1]
            
            # 计算动量指标
            momentum = close_prices.diff(MOMENTUM_PERIOD).iloc[-1]
            momentum_prev = close_prices.diff(MOMENTUM_PERIOD).iloc[-2]
            
            print(f"价格: {current_price}, 布林上轨: {upper:.2f}, 布林下轨: {lower:.2f}, 动量: {momentum:.2f}")
            
            if position == 0:
                # 做多信号：价格突破上轨且动量为正
                if current_price > upper and momentum > 0:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 价格突破上轨且动量正向: {current_price}")
                # 做空信号：价格突破下轨且动量为负
                elif current_price < lower and momentum < 0:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 价格突破下轨且动量负向: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 动量反转平仓
                elif momentum < 0:
                    print(f"[平仓] 动量反转")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 动量反转平仓
                elif momentum > 0:
                    print(f"[平仓] 动量反转")
                    position = 0
    
    api.close()


if __name__ == "__main__":
    main()
