#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略18 - 区间突破策略：沪深300股指期货区间突破策略
原理：
    沪深300股指期货（IF）使用价格区间突破判断趋势。
    价格突破区间上轨做多，跌破下轨做空。

参数：
    - 合约：中金所IF2506
    - K线周期：15分钟
    - 周期数：20根K线
    - 止损：2% 
    - 止盈：4%

适用行情：突破趋势行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.if2506"         # 沪深300股指期货
KLINE_DURATION = 15 * 60        # 15分钟K线
LOOKBACK_PERIOD = 20            # 周期数
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：沪深300股指期货区间突破策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=LOOKBACK_PERIOD + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < LOOKBACK_PERIOD:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算区间
            recent_high = klines['high'].iloc[-LOOKBACK_PERIOD:].max()
            recent_low = klines['low'].iloc[-LOOKBACK_PERIOD:].min()
            
            # 区间中轨
            mid_price = (recent_high + recent_low) / 2
            
            # 突破幅度
            breakout_threshold = (recent_high - recent_low) * 0.3
            
            print(f"价格: {current_price}, 区间高点: {recent_high:.2f}, 区间低点: {recent_low:.2f}")
            
            if position == 0:
                # 做多信号：突破区间上轨
                if current_price > recent_high + breakout_threshold:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 突破区间上轨: {current_price}")
                # 做空信号：跌破区间下轨
                elif current_price < recent_low - breakout_threshold:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 跌破区间下轨: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 跌回区间平仓
                elif current_price < mid_price:
                    print(f"[平仓] 跌回区间: {current_price}")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 涨回区间平仓
                elif current_price > mid_price:
                    print(f"[平仓] 涨回区间: {current_price}")
                    position = 0

if __name__ == "__main__":
    main()
