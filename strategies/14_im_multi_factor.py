#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略14 - 多因子策略：股指期货IM多因子策略
原理：
    股指期货（IM）结合价格动量、波动率和成交量三个因子。
    多因子同时看多时做多，多因子看空时做空。

参数：
    - 合约：CFFEX.IM2506
    - 动量周期：20日
    - 波动率周期：20日
    - 止损：2% 
    - 止盈：4%

适用行情：波动率正常的市场
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA, ATR
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.IM2506"         # 股指期货IM
KLINE_DURATION = 60 * 60        # 1小时K线
MOMENTUM_PERIOD = 20            # 动量周期
VOLATILITY_PERIOD = 20          # 波动率周期
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：股指期货IM多因子策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=MOMENTUM_PERIOD + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < MOMENTUM_PERIOD:
                continue
                
            current_price = klines['close'].iloc[-1]
            price_20d_ago = klines['close'].iloc[-MOMENTUM_PERIOD]
            
            # 动量因子：20日涨跌幅
            momentum = (current_price - price_20d_ago) / price_20d_ago
            
            # 波动率因子：ATR比率
            atr = ATR(klines, VOLATILITY_PERIOD).iloc[-1]
            avg_price = MA(klines, VOLATILITY_PERIOD).iloc[-1]
            volatility_ratio = atr / avg_price
            
            # 成交量因子：成交量是否放大
            vol_current = klines['volume'].iloc[-1]
            vol_ma = MA(klines['volume'], VOLATILITY_PERIOD).iloc[-1]
            volume_ratio = vol_current / vol_ma if vol_ma > 0 else 1
            
            print(f"价格: {current_price}, 动量: {momentum*100:.2f}%, 波动率比: {volatility_ratio:.4f}, 成交量比: {volume_ratio:.2f}")
            
            # 多因子信号判断
            long_signal = momentum > 0 and volatility_ratio < 0.03 and volume_ratio > 0.8
            short_signal = momentum < 0 and volatility_ratio < 0.03 and volume_ratio > 0.8
            
            if position == 0:
                if long_signal:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 多因子看多: {current_price}")
                elif short_signal:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 多因子看空: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                elif short_signal:
                    print(f"[平仓] 转空")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                elif long_signal:
                    print(f"[平仓] 转多")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
