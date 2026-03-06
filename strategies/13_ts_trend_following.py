#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略13 - 趋势策略：国债期货趋势跟踪策略
原理：
    国债期货（TS）采用均线交叉与趋势过滤结合的策略。
    价格站上均线且趋势向上时做多，反之做空。

参数：
    - 合约：CFFEX.TS2506
    - 均线周期：MA20, MA60
    - 止损：1.5% 
    - 止盈：3%

适用行情：利率趋势明显的行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.TS2506"         # 国债期货
KLINE_DURATION = 60 * 60        # 1小时K线
MA_SHORT = 20                   # 短周期
MA_LONG = 60                    # 长周期
STOP_LOSS = 0.015              # 1.5%止损
TAKE_PROFIT = 0.03              # 3%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：国债期货趋势跟踪策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=MA_LONG + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < MA_LONG:
                continue
                
            ma_short = MA(klines, MA_SHORT).iloc[-1]
            ma_long = MA(klines, MA_LONG).iloc[-1]
            
            # 前一根K线的均线值
            ma_short_prev = MA(klines, MA_SHORT).iloc[-2]
            ma_long_prev = MA(klines, MA_LONG).iloc[-2]
            
            current_price = klines['close'].iloc[-1]
            
            print(f"价格: {current_price}, MA20: {ma_short:.4f}, MA60: {ma_long:.4f}")
            
            if position == 0:
                # 做多信号：均线金叉且价格在均线上方
                if ma_short > ma_long and ma_short_prev <= ma_long_prev:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 均线金叉: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 均线死叉平仓
                elif ma_short < ma_long:
                    print(f"[平仓] 均线死叉")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
