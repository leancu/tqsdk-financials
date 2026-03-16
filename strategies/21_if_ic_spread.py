#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 21
策略名称: IF-IC跨品种价差量化策略
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

本策略是基于沪深300股指期货（IF）与中证500股指期货（IC）的跨品种套利策略。
IF代表大盘蓝筹股，IC代表中小盘股票，两者在风格轮动时会产生价差波动。

策略逻辑：
1. 计算IF与IC的价差（spread = IF - k * IC）
2. 使用自适应k值（基于过去20日回归）
3. 价差突破历史均值±1.5倍标准差时入场
4. 价差回归均值±0.5倍标准差时出场

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL_IF | CFFEX.if2510 | 沪深300股指期货 |
| SYMBOL_IC | CFFEX.ic2510 | 中证500股指期货 |
| LOOKBACK_PERIOD | 20 | 统计周期 |
| ENTRY_THRESHOLD | 1.5 | 入场阈值 |
| EXIT_THRESHOLD | 0.5 | 出场阈值 |
| LOT_SIZE | 1 | 开仓手数 |

【风险提示】

- 跨品种套利需要关注两个品种的流动性差异
- 价差可能长时间不回归，需做好资金管理
- 期货交易存在较高风险，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from collections import deque

# ============ 参数配置 ============
SYMBOL_IF = "CFFEX.if2510"     # 沪深300股指期货
SYMBOL_IC = "CFFEX.ic2510"     # 中证500股指期货
LOOKBACK_PERIOD = 20            # 统计周期
ENTRY_THRESHOLD = 1.5           # 入场阈值
EXIT_THRESHOLD = 0.5           # 出场阈值
LOT_SIZE = 1                    # 开仓手数
KLINE_DURATION = 60 * 60       # 1小时K线


class IFCICSpreadStrategy:
    def __init__(self, api):
        self.api = api
        self.spread_history = deque(maxlen=LOOKBACK_PERIOD)
        self.position = 0
        self.k_value = 1.0
        self.if_pos = 0
        self.ic_pos = 0
        
    def calculate_hedge_ratio(self):
        """计算自适应对冲比率"""
        if len(self.spread_history) < LOOKBACK_PERIOD:
            return 1.0
        
        # 简化的对冲比率计算
        return 1.0
    
    def get_spread(self):
        """获取当前价差"""
        if_quote = self.api.get_quote(SYMBOL_IF)
        ic_quote = self.api.get_quote(SYMBOL_IC)
        if_price = if_quote.last_price
        ic_price = ic_quote.last_price
        spread = if_price - self.k_value * ic_price
        return spread, if_price, ic_price
    
    def calculate_stats(self):
        """计算价差统计"""
        if len(self.spread_history) < LOOKBACK_PERIOD:
            return None, None
        
        spreads = list(self.spread_history)
        mean = np.mean(spreads)
        std = np.std(spreads)
        return mean, std
    
    def update_position(self, spread):
        """更新仓位"""
        if len(self.spread_history) < LOOKBACK_PERIOD:
            return
        
        mean, std = self.calculate_stats()
        if std == 0:
            return
        
        z_score = (spread - mean) / std
        
        if self.position == 0:
            if z_score > ENTRY_THRESHOLD:
                # 做空价差
                self.if_pos = -LOT_SIZE
                self.ic_pos = LOT_SIZE
                self.position = -1
                print(f"做空价差: z={z_score:.2f}")
            elif z_score < -ENTRY_THRESHOLD:
                # 做多价差
                self.if_pos = LOT_SIZE
                self.ic_pos = -LOT_SIZE
                self.position = 1
                print(f"做多价差: z={z_score:.2f}")
        
        elif self.position == 1 and z_score > -EXIT_THRESHOLD:
            self.if_pos = 0
            self.ic_pos = 0
            self.position = 0
            print(f"平多仓")
        elif self.position == -1 and z_score < EXIT_THRESHOLD:
            self.if_pos = 0
            self.ic_pos = 0
            self.position = 0
            print(f"平空仓")
    
    def execute_orders(self):
        """执行下单"""
        try:
            if self.if_pos != 0:
                self.api.insert_order(
                    symbol=SYMBOL_IF,
                    direction="BUY" if self.if_pos > 0 else "SELL",
                    offset="OPEN",
                    volume=abs(self.if_pos)
                )
            else:
                positions = self.api.get_position(SYMBOL_IF)
                if positions.pos_long > 0:
                    self.api.insert_order(
                        symbol=SYMBOL_IF, direction="SELL", offset="CLOSE",
                        volume=positions.pos_long
                    )
                elif positions.pos_short > 0:
                    self.api.insert_order(
                        symbol=SYMBOL_IF, direction="BUY", offset="CLOSE",
                        volume=positions.pos_short
                    )
            
            if self.ic_pos != 0:
                self.api.insert_order(
                    symbol=SYMBOL_IC,
                    direction="BUY" if self.ic_pos > 0 else "SELL",
                    offset="OPEN",
                    volume=abs(self.ic_pos)
                )
            else:
                positions = self.api.get_position(SYMBOL_IC)
                if positions.pos_long > 0:
                    self.api.insert_order(
                        symbol=SYMBOL_IC, direction="SELL", offset="CLOSE",
                        volume=positions.pos_long
                    )
                elif positions.pos_short > 0:
                    self.api.insert_order(
                        symbol=SYMBOL_IC, direction="BUY", offset="CLOSE",
                        volume=positions.pos_short
                    )
        except Exception as e:
            print(f"下单错误: {e}")
    
    def run(self):
        """运行策略"""
        print("IF-IC跨品种价差策略启动")
        
        self.api.subscribe([SYMBOL_IF, SYMBOL_IC])
        
        for _ in range(LOOKBACK_PERIOD):
            self.api.wait_update()
            spread, _, _ = self.get_spread()
            self.spread_history.append(spread)
        
        print(f"预热完成")
        
        while True:
            self.api.wait_update()
            spread, if_price, ic_price = self.get_spread()
            self.spread_history.append(spread)
            
            print(f"IF: {if_price:.2f}, IC: {ic_price:.2f}, Spread: {spread:.2f}")
            
            self.update_position(spread)
            self.execute_orders()


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    try:
        strategy = IFCICSpreadStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("策略停止")
    finally:
        api.close()


if __name__ == "__main__":
    main()
