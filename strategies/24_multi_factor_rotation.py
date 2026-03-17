#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 24
策略名称: 金融期货多因子轮动策略
生成日期: 2026-03-17
仓库地址: tqsdk-financials
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略是一个多因子轮动策略，结合均线、RSI、MACD、布林带四个技术因子，
对IF（沪深300）、IC（中证500）、IH（上证50）三个股指期货进行综合打分，
根据得分轮动持仓最强品种。

因子设计：
1. 均线因子：价格站上MA20得1分
2. RSI因子：RSI<30超卖得1分，RSI>70超买扣1分
3. MACD因子：MACD金叉得1分，死叉扣1分
4. 布林带因子：价格在中轨上方得1分

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOLS | IF, IC, IH | 交易品种 |
| MA_PERIOD | 20 | 均线周期 |
| RSI_PERIOD | 14 | RSI周期 |
| MACD_FAST | 12 | MACD快线 |
| MACD_SLOW | 26 | MACD慢线 |
| BB_PERIOD | 20 | 布林带周期 |
| LOT_SIZE | 1 | 开仓手数 |

【风险提示】

- 轮动策略可能在震荡行情中频繁换手
- 因子有效性可能随市场变化
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
MA_PERIOD = 20                  # 均线周期
RSI_PERIOD = 14                 # RSI周期
MACD_FAST = 12                  # MACD快线
MACD_SLOW = 26                  # MACD慢线
MACD_SIGNAL = 9                 # MACD信号线
BB_PERIOD = 20                  # 布林带周期
BB_STD = 2                      # 布林带标准差
LOT_SIZE = 1                    # 开仓手数


class MultiFactorRotationStrategy:
    def __init__(self, api):
        self.api = api
        self.position = {"symbol": None, "direction": 0}
        self.last_symbol = None
    
    def calculate_ma_factor(self, symbol, period=20):
        """均线因子：价格站上MA20得1分"""
        try:
            klines = self.api.get_kline_serial(symbol, 60*60*24, period+1)
            if len(klines) < period + 1:
                return 0
            close = klines['close'].values
            ma = np.mean(close[-period:])
            return 1 if close[-1] > ma else -1
        except:
            return 0
    
    def calculate_rsi_factor(self, symbol, period=14):
        """RSI因子：RSI<30超卖得1分，RSI>70超买卖1分"""
        try:
            klines = self.api.get_kline_serial(symbol, 60*60*24, period+2)
            if len(klines) < period + 2:
                return 0
            close = klines['close'].values
            delta = np.diff(close)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = np.mean(gain[-period:])
            avg_loss = np.mean(loss[-period:])
            if avg_loss == 0:
                return 1
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            if rsi < 30:
                return 1  # 超卖
            elif rsi > 70:
                return -1  # 超买
            return 0
        except:
            return 0
    
    def calculate_macd_factor(self, symbol, fast=12, slow=26, signal=9):
        """MACD因子：金叉得1分，死叉扣1分"""
        try:
            klines = self.api.get_kline_serial(symbol, 60*60*24, slow+signal+1)
            if len(klines) < slow + signal + 1:
                return 0
            close = klines['close'].values
            
            # 计算EMA
            ema_fast = pd.Series(close).ewm(span=fast).mean().values
            ema_slow = pd.Series(close).ewm(span=slow).mean().values
            macd_line = ema_fast - ema_slow
            signal_line = pd.Series(macd_line).ewm(span=signal).mean().values
            
            # 判断金叉死叉
            if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
                return 1  # 金叉
            elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
                return -1  # 死叉
            return 0
        except:
            return 0
    
    def calculate_bb_factor(self, symbol, period=20):
        """布林带因子：价格在中轨上方得1分"""
        try:
            klines = self.api.get_kline_serial(symbol, 60*60*24, period+1)
            if len(klines) < period + 1:
                return 0
            close = klines['close'].values
            ma = np.mean(close[-period:])
            std = np.std(close[-period:])
            upper = ma + BB_STD * std
            lower = ma - BB_STD * std
            
            if close[-1] > ma:
                return 1
            elif close[-1] < ma:
                return -1
            return 0
        except:
            return 0
    
    def calculate_total_score(self, symbol):
        """计算品种综合得分"""
        ma_score = self.calculate_ma_factor(symbol, MA_PERIOD)
        rsi_score = self.calculate_rsi_factor(symbol, RSI_PERIOD)
        macd_score = self.calculate_macd_factor(symbol, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
        bb_score = self.calculate_bb_factor(symbol, BB_PERIOD)
        
        total = ma_score + rsi_score + macd_score + bb_score
        return total, {
            "ma": ma_score,
            "rsi": rsi_score,
            "macd": macd_score,
            "bb": bb_score
        }
    
    def get_best_symbol(self):
        """获取最佳品种"""
        scores = {}
        for symbol in SYMBOLS:
            total, details = self.calculate_total_score(symbol)
            scores[symbol] = total
            print(f"{symbol}: MA={details['ma']}, RSI={details['rsi']}, MACD={details['macd']}, BB={details['bb']}, 总分={total}")
        
        best = max(scores.items(), key=lambda x: x[1])
        return best[0], best[1]
    
    def open_position(self, symbol, direction, volume):
        """开仓"""
        try:
            if direction > 0:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="OPEN", volume=volume)
            else:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="OPEN", volume=volume)
            self.position = {"symbol": symbol, "direction": direction}
            print(f"开仓: {symbol}, {'多' if direction > 0 else '空'}")
        except Exception as e:
            print(f"开仓失败: {e}")
    
    def close_position(self):
        """平仓"""
        if self.position["symbol"] is None:
            return
        try:
            symbol = self.position["symbol"]
            direction = self.position["direction"]
            if direction > 0:
                self.api.insert_order(symbol=symbol, direction="SELL", offset="CLOSE", volume=LOT_SIZE)
            else:
                self.api.insert_order(symbol=symbol, direction="BUY", offset="CLOSE", volume=LOT_SIZE)
            print(f"平仓: {symbol}")
            self.position = {"symbol": None, "direction": 0}
        except Exception as e:
            print(f"平仓失败: {e}")
    
    def run(self):
        """运行策略"""
        print("=" * 50)
        print("金融期货多因子轮动策略启动")
        print("=" * 50)
        
        while True:
            self.api.wait_update()
            
            best_symbol, best_score = self.get_best_symbol()
            print(f"\n最佳品种: {best_symbol}, 得分: {best_score}")
            
            # 如果最佳品种得分大于0且与当前持仓不同，换仓
            if best_score > 0 and best_symbol != self.position["symbol"]:
                self.close_position()
                self.open_position(best_symbol, 1, LOT_SIZE)
                self.last_symbol = best_symbol


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 模拟测试
    # api = TqApi(auth=TqSim())
    
    try:
        strategy = MultiFactorRotationStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
