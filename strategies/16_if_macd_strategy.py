#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略16 - MACD策略：沪深300股指期货MACD策略
原理：
    沪深300股指期货（IF）使用MACD指标的金叉死叉来判断趋势。
    MACD金叉时做多，死叉时做空，配合零轴位置过滤假信号。

参数：
    - 合约：中金所IF2506
    - K线周期：30分钟
    - DIF周期：12
    - DEA周期：26
    - 信号线：9
    - 止损：2% 
    - 止盈：4%

适用行情：趋势明显的单边行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MACD
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.IF2506"         # 沪深300股指期货
KLINE_DURATION = 30 * 60        # 30分钟K线
FAST_PERIOD = 12                # DIF周期
SLOW_PERIOD = 26                # DEA周期
SIGNAL_PERIOD = 9              # 信号线周期
STOP_LOSS = 0.02                # 2%止损
TAKE_PROFIT = 0.04              # 4%止盈

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：沪深300股指期货MACD策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, data_length=SLOW_PERIOD + 20)
    quote = api.get_quote(SYMBOL)
    
    position = 0
    entry_price = 0
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines):
            if len(klines) < SLOW_PERIOD + SIGNAL_PERIOD:
                continue
                
            current_price = klines['close'].iloc[-1]
            
            # 计算MACD
            macd = MACD(klines['close'], fast=FAST_PERIOD, slow=SLOW_PERIOD, signal=SIGNAL_PERIOD)
            dif = macd['diff'].iloc[-1]
            dea = macd['dea'].iloc[-1]
            dif_prev = macd['diff'].iloc[-2]
            dea_prev = macd['dea'].iloc[-2]
            macd_hist = dif - dea
            
            print(f"价格: {current_price}, DIF: {dif:.2f}, DEA: {dea:.2f}, MACD柱: {macd_hist:.2f}")
            
            if position == 0:
                # 做多信号：MACD金叉且在零轴下方
                if dif_prev <= dea_prev and dif > dea and dif < 0:
                    position = 1
                    entry_price = current_price
                    print(f"[买入] MACD金叉(零轴下): {current_price}")
                # 做空信号：MACD死叉且在零轴上方
                elif dif_prev >= dea_prev and dif < dea and dif > 0:
                    position = -1
                    entry_price = current_price
                    print(f"[卖出] MACD死叉(零轴上): {current_price}")
                    
            elif position == 1:
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # MACD死叉平仓
                elif dif < dea:
                    print(f"[平仓] MACD死叉")
                    position = 0
                    
            elif position == -1:
                pnl_pct = (entry_price - current_price) / entry_price
                
                if pnl_pct < -STOP_LOSS:
                    print(f"[止损] 价格: {current_price}, 亏损: {pnl_pct*100:.2f}%")
                    position = 0
                elif pnl_pct > TAKE_PROFIT:
                    print(f"[止盈] 价格: {current_price}, 盈利: {pnl_pct*100:.2f}%")
                    position = 0
                # MACD金叉平仓
                elif dif > dea:
                    print(f"[平仓] MACD金叉")
                    position = 0
    
    api.close()

if __name__ == "__main__":
    main()
