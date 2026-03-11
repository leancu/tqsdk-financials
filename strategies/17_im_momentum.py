#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略17 - 动量策略：中证1000股指期货动量策略
原理：
    中证1000股指期货（IM）使用动量指标判断趋势方向。
    动量持续向上做多，持续向下做空。

参数：
    - 合约：中金所IM2506
    - K线周期：15分钟
    - 动量周期：8
    - 止损：2% 
    - 止盈：4%

适用行情：趋势行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.IM2506"         # 中证1000股指期货
KLINE_DURATION = 15 * 60        # 15分钟K线
MOMENTUM_PERIOD = 8             # 动量周期
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def calculate_momentum(klines, period):
    """计算动量"""
    close = klines['close']
    momentum = close.iloc[-1] - close.iloc[-period]
    return momentum

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：中证1000股指期货动量策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=MOMENTUM_PERIOD + 10)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    prev_momentum = None
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < MOMENTUM_PERIOD:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算动量
            momentum = calculate_momentum(klines, MOMENTUM_PERIOD)
            
            print(f"价格: {current_price}, 动量: {momentum:.2f}")
            
            if position == 0:
                # 做多信号：动量向上
                if momentum > 0:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] 动量向上: {current_price}")
                # 做空信号：动量向下
                elif momentum < 0:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] 动量向下: {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 动量转负平仓
                elif momentum < 0:
                    print(f"[平仓] 动量转负: {current_price}")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # 动量转正平仓
                elif momentum > 0:
                    print(f"[平仓] 动量转正: {current_price}")
                    position = 0
            
            prev_momentum = momentum

if __name__ == "__main__":
    main()
