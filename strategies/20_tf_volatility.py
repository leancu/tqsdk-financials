#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略20 - 国债期货波动率套利策略：金融期货波动率交易策略
原理：
    国债期货(TF)基于波动率突破进行交易。
    当价格波动幅度显著放大时预示趋势行情到来，顺势开仓。

参数：
    - 合约：中金所TF2506
    - K线周期：15分钟
    - ATR周期：20
    - ATR倍数：1.5
    - 止损：2%
    - 止盈：4%

适用行情：波动率放大时的趋势行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import ATR
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.TF2506"         # 国债期货
KLINE_DURATION = 60 * 15       # 15分钟K线
ATR_PERIOD = 20                 # ATR周期
ATR_MULTI = 1.5                # ATR倍数
STOP_LOSS = 0.02               # 2%止损
TAKE_PROFIT = 0.04             # 4%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：国债期货波动率套利策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=ATR_PERIOD + 50)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < ATR_PERIOD + 20:
                continue
                
            high_prices = klines['high']
            low_prices = klines['low']
            close_prices = klines['close']
            current_price = close_prices.iloc[-1]
            
            # 计算ATR
            atr = ATR(high_prices, low_prices, close_prices, period=ATR_PERIOD)
            atr_value = atr.iloc[-1]
            atr_prev = atr.iloc[-2]
            
            # 计算当前波动率相对于平均水平的倍数
            atr_ma = atr.rolling(10).mean().iloc[-1]
            volatility_ratio = atr_value / atr_ma if atr_ma > 0 else 1
            
            # 计算趋势方向
            ma10 = close_prices.rolling(10).mean().iloc[-1]
            ma20 = close_prices.rolling(20).mean().iloc[-1]
            trend_up = ma10 > ma20
            
            print(f"价格: {current_price}, ATR: {atr_value:.4f}, 波动率比: {volatility_ratio:.2f}")
            
            if position == 0:
                # 波动率放大且价格上涨突破
                if volatility_ratio > ATR_MULTI and trend_up and current_price > close_prices.iloc[-2]:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 波动率放大且趋势向上: {current_price}")
                # 波动率放大且价格下跌
                elif volatility_ratio > ATR_MULTI and not trend_up and current_price < close_prices.iloc[-2]:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 波动率放大且趋势向下: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 趋势反转平仓
                elif ma10 < ma20:
                    print(f"[平仓] 趋势反转")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 趋势反转平仓
                elif ma10 > ma20:
                    print(f"[平仓] 趋势反转")
                    position = 0
    
    api.close()


if __name__ == "__main__":
    main()
