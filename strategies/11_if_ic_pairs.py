#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略11 - 股指期货配对交易策略
原理：
    IF和IC具有高度相关性，当两者价差偏离历史均值时，
    进行价差回归交易。

参数：
    - IF合约：SHFE.if2505
    - IC合约：SHFE.ic2505
    - 周期：30分钟
    - 价差窗口：40根K线
    - 开仓阈值：1.8倍标准差
    - 平仓阈值：0.4倍标准差

适用行情：价差偏离均值时
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
import numpy as np

# ============ 参数配置 ============
IF_SYMBOL = "SHFE.if2505"        # 股指期货
IC_SYMBOL = "SHFE.ic2505"        # 中证500期货
KLINE_DURATION = 30 * 60        # 30分钟K线
WINDOW = 40                      # 价差滚动窗口
OPEN_THRESHOLD = 1.8            # 开仓阈值
CLOSE_THRESHOLD = 0.4           # 平仓阈值
VOLUME = 1                      # 每次交易手数


def calc_spread(if_price, ic_price):
    """计算IF-IC价差"""
    return if_price - ic_price


def calc_zscore(spread_series):
    """计算价差的Z-Score"""
    mean = np.mean(spread_series)
    std = np.std(spread_series)
    if std == 0:
        return 0.0
    return (spread_series[-1] - mean) / std


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：股指期货配对交易策略")
    
    if_quote = api.get_quote(IF_SYMBOL)
    ic_quote = api.get_quote(IC_SYMBOL)
    
    if_klines = api.get_kline_serial(IF_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    ic_klines = api.get_kline_serial(IC_SYMBOL, KLINE_DURATION, data_length=WINDOW + 1)
    
    target_pos_if = TargetPosTask(api, IF_SYMBOL)
    target_pos_ic = TargetPosTask(api, IC_SYMBOL)
    
    spread_history = []
    position = 0  # 0: 空仓, 1: 多IF空IC, -1: 空IF多IC
    
    while True:
        api.wait_update()
        
        if api.is_changing(if_quote) or api.is_changing(ic_quote):
            if_price = if_quote.last_price
            ic_price = ic_quote.last_price
            
            if if_price <= 0 or ic_price <= 0:
                continue
            
            spread = calc_spread(if_price, ic_price)
            spread_history.append(spread)
            
            if len(spread_history) < WINDOW:
                continue
            
            recent_spread = spread_history[-WINDOW:]
            zscore = calc_zscore(recent_spread)
            
            print(f"IF: {if_price}, IC: {ic_price}, 价差: {spread:.2f}, Z-Score: {zscore:.2f}")
            
            if position == 0:
                if zscore > OPEN_THRESHOLD:
                    print(f"[开仓] 做空价差(空IF多IC), Z-Score: {zscore:.2f}")
                    target_pos_if.set_target_volume(-VOLUME)
                    target_pos_ic.set_target_volume(VOLUME)
                    position = -1
                elif zscore < -OPEN_THRESHOLD:
                    print(f"[开仓] 做多价差(多IF空IC), Z-Score: {zscore:.2f}")
                    target_pos_if.set_target_volume(VOLUME)
                    target_pos_ic.set_target_volume(-VOLUME)
                    position = 1
                    
            elif position == 1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归, Z-Score: {zscore:.2f}")
                target_pos_if.set_target_volume(0)
                target_pos_ic.set_target_volume(0)
                position = 0
            elif position == -1 and abs(zscore) < CLOSE_THRESHOLD:
                print(f"[平仓] 价差回归, Z-Score: {zscore:.2f}")
                target_pos_if.set_target_volume(0)
                target_pos_ic.set_target_volume(0)
                position = 0
    
    api.close()


if __name__ == "__main__":
    main()
