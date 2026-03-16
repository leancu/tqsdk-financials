#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 22
策略名称: 沪深300多因子量化策略
生成日期: 2026-03-16
仓库地址: tqsdk-financials
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【TqSdk 简介】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TqSdk（天勤量化 SDK）是由信易科技（北京）有限公司开发的专业期货量化交易框架，
完全免费开源（Apache 2.0 协议），基于 Python 语言设计，支持 Python 3.6+ 环境。
TqSdk 已服务于数万名国内期货量化投资者，是国内使用最广泛的期货量化框架之一。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
GitHub: https://github.com/shinnytech/tqsdk-python
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个综合多因子的股指期货交易策略，结合以下因子：

1. 均线因子（MA）：价格站上20日均线看多
2. RSI动量因子：RSI<30超卖看多，RSI>70超买看空
3. 布林带因子：价格处于布林带中轨上方看多

策略规则：
- 至少2个因子看多时开多仓
- 至少2个因子看空时开空仓
- 信号消失时平仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL | CFFEX.if2510 | 沪深300股指期货 |
| MA_PERIOD | 20 | 均线周期 |
| RSI_PERIOD | 14 | RSI周期 |
| BB_PERIOD | 20 | 布林带周期 |
| LOT_SIZE | 1 | 开仓手数 |

【风险提示】

- 多因子策略需关注因子有效性变化
- 市场极端行情时可能导致较大亏损
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np

# ============ 参数配置 ============
SYMBOL = "CFFEX.if2510"         # 沪深300股指期货
KLINE_DURATION = 60 * 60        # 1小时K线
MA_PERIOD = 20                  # 均线周期
RSI_PERIOD = 14                 # RSI周期
BB_PERIOD = 20                  # 布林带周期
BB_STD = 2                      # 布林带标准差
LOT_SIZE = 1                    # 开仓手数


class MultiFactorStrategy:
    def __init__(self, api):
        self.api = api
        self.position = 0
        
    def calculate_rsi(self, prices, period=14):
        """计算RSI"""
        if len(prices) < period + 1:
            return 50
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    def get_signals(self, df):
        """获取各因子信号"""
        # 均线因子
        df['ma'] = df['close'].rolling(window=MA_PERIOD).mean()
        ma_signal = 1 if df['close'].iloc[-1] > df['ma'].iloc[-1] else -1 if pd.notna(df['ma'].iloc[-1]) else 0
        
        # RSI因子
        rsi = self.calculate_rsi(df['close'], RSI_PERIOD)
        rsi_signal = 1 if rsi < 30 else -1 if rsi > 70 else 0
        
        # 布林带因子
        df['bb_mid'] = df['close'].rolling(window=BB_PERIOD).mean()
        df['bb_std'] = df['close'].rolling(window=BB_PERIOD).std()
        bb_signal = 1 if df['close'].iloc[-1] > df['bb_mid'].iloc[-1] else -1 if df['close'].iloc[-1] < df['bb_mid'].iloc[-1] else 0
        
        return ma_signal, rsi_signal, bb_signal
    
    def update_position(self, signals):
        """更新仓位"""
        long_count = sum(1 for s in signals if s > 0)
        short_count = sum(1 for s in signals if s < 0)
        
        if self.position == 0:
            if long_count >= 2:
                self.position = 1
                print(f"开多仓: {long_count}个因子看多")
            elif short_count >= 2:
                self.position = -1
                print(f"开空仓: {short_count}个因子看空")
        elif self.position == 1 and short_count >= 2:
            self.position = 0
            print("平多仓")
        elif self.position == -1 and long_count >= 2:
            self.position = 0
            print("平空仓")
    
    def execute_orders(self):
        """执行下单"""
        try:
            pos = self.api.get_position(SYMBOL)
            
            if self.position == 1 and pos.pos_long == 0:
                self.api.insert_order(
                    symbol=SYMBOL, direction="BUY", offset="OPEN", volume=LOT_SIZE
                )
            elif self.position == -1 and pos.pos_short == 0:
                self.api.insert_order(
                    symbol=SYMBOL, direction="SELL", offset="OPEN", volume=LOT_SIZE
                )
            elif self.position == 0:
                if pos.pos_long > 0:
                    self.api.insert_order(
                        symbol=SYMBOL, direction="SELL", offset="CLOSE", volume=pos.pos_long
                    )
                if pos.pos_short > 0:
                    self.api.insert_order(
                        symbol=SYMBOL, direction="BUY", offset="CLOSE", volume=pos.pos_short
                    )
        except Exception as e:
            print(f"下单错误: {e}")
    
    def run(self):
        """运行策略"""
        print("沪深300多因子策略启动")
        
        self.api.subscribe([SYMBOL])
        
        while True:
            self.api.wait_update()
            klines = self.api.get_kline_serial(SYMBOL, KLINE_DURATION, 100)
            
            if len(klines) < BB_PERIOD + 1:
                continue
            
            df = pd.DataFrame({
                'open': klines['open'],
                'high': klines['high'],
                'low': klines['low'],
                'close': klines['close'],
                'volume': klines['volume']
            })
            
            ma_s, rsi_s, bb_s = self.get_signals(df)
            signals = [ma_s, rsi_s, bb_s]
            
            print(f"MA: {ma_s}, RSI: {rsi_s}, BB: {bb_s}, 持仓: {self.position}")
            
            self.update_position(signals)
            self.execute_orders()


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    try:
        strategy = MultiFactorStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("策略停止")
    finally:
        api.close()


if __name__ == "__main__":
    main()
