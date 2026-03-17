#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 23
策略名称: 股指期货截面多空策略
生成日期: 2026-03-17
仓库地址: tqsdk-financials
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个截面多空策略，同时监控沪深300(IF)、中证500(IC)、上证50(IH)三个股指期货，
根据各品种的动量和趋势强度进行排名，做多最强品种，做空最弱品种。

策略逻辑：
1. 计算各品种的动量因子（20日收益率）
2. 计算趋势因子（MA20方向）
3. 计算波动率因子（ATR）
4. 综合打分排名
5. 做多排名Top1，做空排名Bottom1

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOLS | 股指期货列表 | IF, IC, IH |
| MOMENTUM_PERIOD | 20 | 动量周期 |
| MA_PERIOD | 20 | 均线周期 |
| LOT_SIZE | 1 | 单边开仓手数 |

【风险提示】

- 股指期货杠杆较高，请谨慎操作
- 截面策略需关注品种相关性变化
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from collections import deque

# ============ 参数配置 ============
SYMBOLS = [
    "CFFEX.if2510",   # 沪深300
    "CFFEX.ic2510",   # 中证500
    "CFFEX.ih2510",   # 上证50
]
KLINE_DURATION = 60 * 60        # 1小时K线
MOMENTUM_PERIOD = 20            # 动量周期
MA_PERIOD = 20                  # 均线周期
ATR_PERIOD = 14                 # ATR周期
LOT_SIZE = 1                    # 开仓手数


class IndexCrossSectionStrategy:
    def __init__(self, api):
        self.api = api
        self.position = {}  # symbol -> position
    
    def calculate_momentum(self, symbol, period=20):
        """计算动量因子"""
        try:
            klines = self.api.get_kline_serial(symbol, 60*60*24, period+1)
            if len(klines) < period + 1:
                return 0
            close_prices = klines['close'].values
            momentum = (close_prices[-1] - close_prices[0]) / close_prices[0]
            return momentum
        except:
            return 0
    
    def calculate_trend(self, symbol, period=20):
        """计算趋势因子（价格相对MA）"""
        try:
            klines = self.api.get_kline_serial(symbol, 60*60*24, period+1)
            if len(klines) < period + 1:
                return 0
            close_prices = klines['close'].values
            ma = np.mean(close_prices[-period:])
            current_price = close_prices[-1]
            # 价格在MA上方为正，下方为负
            return (current_price - ma) / ma
        except:
            return 0
    
    def calculate_volatility(self, symbol, period=14):
        """计算波动率因子"""
        try:
            klines = self.api.get_kline_serial(symbol, 60*60*24, period+1)
            if len(klines) < period + 1:
                return 0
            returns = np.diff(klines['close'].values) / klines['close'].values[:-1]
            volatility = np.std(returns)
            return volatility
        except:
            return 0
    
    def get_rankings(self):
        """获取品种排名"""
        scores = {}
        for symbol in SYMBOLS:
            momentum = self.calculate_momentum(symbol, MOMENTUM_PERIOD)
            trend = self.calculate_trend(symbol, MA_PERIOD)
            volatility = self.calculate_volatility(symbol, ATR_PERIOD)
            
            # 综合打分（动量权重0.5，趋势权重0.3，波动率负权重0.2）
            score = 0.5 * momentum + 0.3 * trend - 0.2 * volatility
            scores[symbol] = score
            print(f"{symbol}: 动量={momentum:.2%}, 趋势={trend:.2%}, 波动率={volatility:.2%}, 综合={score:.4f}")
        
        sorted_symbols = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_symbols
    
    def rebalance(self, rankings):
        """重新平衡仓位"""
        if len(rankings) < 2:
            return
        
        long_symbol = rankings[0][0]
        short_symbol = rankings[-1][0]
        
        # 平掉其他仓位
        for symbol in self.position:
            if symbol != long_symbol and symbol != short_symbol:
                self.close_position(symbol)
        
        # 做多最强
        if self.position.get(long_symbol, 0) != LOT_SIZE:
            self.close_position(long_symbol)
            self.open_position(long_symbol, 1, LOT_SIZE)
        
        # 做空最弱
        if self.position.get(short_symbol, 0) != -LOT_SIZE:
            self.close_position(short_symbol)
            self.open_position(short_symbol, -1, LOT_SIZE)
    
    def open_position(self, symbol, direction, volume):
        """开仓"""
        try:
            if direction > 0:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="OPEN", volume=volume)
            else:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="OPEN", volume=volume)
            self.position[symbol] = direction * volume
        except Exception as e:
            print(f"开仓失败: {e}")
    
    def close_position(self, symbol):
        """平仓"""
        try:
            pos = self.position.get(symbol, 0)
            if pos > 0:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="CLOSE", volume=pos)
            elif pos < 0:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="CLOSE", volume=abs(pos))
            self.position[symbol] = 0
        except Exception as e:
            print(f"平仓失败: {e}")
    
    def run(self):
        """运行策略"""
        print("=" * 50)
        print("股指期货截面多空策略启动")
        print("=" * 50)
        
        while True:
            self.api.wait_update()
            
            # 每日重新评分
            print(f"\n[{pd.Timestamp.now()}] 品种评分:")
            rankings = self.get_rankings()
            print("排名:", [s[0] for s in rankings])
            
            self.rebalance(rankings)


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 模拟测试
    # api = TqApi(auth=TqSim())
    
    try:
        strategy = IndexCrossSectionStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
