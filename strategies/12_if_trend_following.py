#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略12 - 沪深300趋势跟踪策略
原理：
    使用双均线判断趋势，趋势确认后入场

参数：
    - 合约：SHFE.if2505
    - 周期：15分钟
    - 短期均线：10
    - 长期均线：30

适用行情：趋势行情
作者：leancu / tqsdk-financials
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
from tqsdk.tafunc import ma

# ============ 参数配置 ============
SYMBOL = "SHFE.if2505"           # 沪深300股指期货
KLINE_DURATION = 15 * 60        # 15分钟K线
MA_SHORT = 10                    # 短期均线
MA_LONG = 30                    # 长期均线
VOLUME = 1                      # 每次交易手数
DATA_LENGTH = 100               # 历史K线数量


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：沪深300趋势跟踪策略")
    
    klines = api.get_kline_serial(SYMBOL, KLINE_DURATION, DATA_LENGTH)
    target_pos = TargetPosTask(api, SYMBOL)
    
    position = 0  # 0: 空仓, 1: 多头, -1: 空头
    
    while True:
        api.wait_update()
        
        if api.is_changing(klines.iloc[-1], "datetime"):
            close = klines["close"]
            ma_s = ma(close, MA_SHORT)
            ma_l = ma(close, MA_LONG)
            
            price = close.iloc[-1]
            ma_s_val = ma_s.iloc[-1]
            ma_l_val = ma_l.iloc[-1]
            
            print(f"价格: {price:.2f}, MA10: {ma_s_val:.2f}, MA30: {ma_l_val:.2f}")
            
            if position == 0:
                # 金叉做多
                if ma_s.iloc[-1] > ma_l.iloc[-1] and ma_s.iloc[-2] <= ma_l.iloc[-2]:
                    print(f"[开仓] 金叉做多")
                    target_pos.set_target_volume(VOLUME)
                    position = 1
                # 死叉做空
                elif ma_s.iloc[-1] < ma_l.iloc[-1] and ma_s.iloc[-2] >= ma_l.iloc[-2]:
                    print(f"[开仓] 死叉做空")
                    target_pos.set_target_volume(-VOLUME)
                    position = -1
                    
            elif position == 1:
                # 死叉平多
                if ma_s.iloc[-1] < ma_l.iloc[-1]:
                    print(f"[平仓] 死叉平多")
                    target_pos.set_target_volume(0)
                    position = 0
            elif position == -1:
                # 金叉平空
                if ma_s.iloc[-1] > ma_l.iloc[-1]:
                    print(f"[平仓] 金叉平空")
                    target_pos.set_target_volume(0)
                    position = 0
    
    api.close()


if __name__ == "__main__":
    main()
