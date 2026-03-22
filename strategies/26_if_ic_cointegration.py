#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 26
策略名称: 金融期货协整套利策略
生成日期: 2026-03-22
仓库地址: tqsdk-financials
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技开发的专业期货量化交易框架，完全免费开源。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】

本策略基于协整套利思想，对沪深300(IF)和中证500(IC)的价比序列进行协整分析，
当价比偏离协整均衡时，预期价格回归，进行配对交易。

协整关系的核心思想：虽然两个非平稳序列的线性组合可能是平稳的（协整的），
这意味着它们之间存在长期均衡关系，短期偏离会被修复。

策略逻辑：
1. 计算 IF/IC 价比序列（IC_price / IF_price，反映大小盘相对强弱）
2. 用滚动窗口计算价比的均值和标准差
3. 当价比 z-score > 上阈值 → 大盘相对偏强，预期回归 → 做空IF/做多IC
4. 当价比 z-score < 下阈值 → 小盘相对偏强 → 做多IF/做空IC
5. 价比回归均值时平仓

【策略参数】

| 参数 | 默认值 | 说明 |
|------|--------|------|
| SYMBOL_IF | CFFEX.if2510 | 沪深300合约 |
| SYMBOL_IC | CFFEX.ic2510 | 中证500合约 |
| LOOKBACK | 60 | 协整窗口（交易日） |
| Z_ENTRY | 1.8 | 入场阈值（z-score） |
| Z_EXIT | 0.3 | 出场阈值（z-score） |
| Z_STOP | 3.0 | 止损阈值（z-score） |
| LOT_SIZE | 1 | 每边手数 |
| CLOSE_TIME | time(14,55) | 收盘前平仓时间 |

【风险提示】

- 协整关系可能随市场结构变化而失效
- 大小盘风格切换期间可能出现较大回撤
- 股指期货杠杆较高，请充分测试后再用于实盘
================================================================================
"""

from tqsdk import TqApi, TqAuth, TqSim
import pandas as pd
import numpy as np
from datetime import datetime, time

# ============ 参数配置 ============
SYMBOL_IF = "CFFEX.if2510"      # 沪深300
SYMBOL_IC = "CFFEX.ic2510"      # 中证500
KLINE_DURATION = 60 * 60 * 24   # 日K线
LOOKBACK = 60                   # 协整窗口（交易日）
Z_ENTRY = 1.8                   # 入场阈值
Z_EXIT = 0.3                    # 出场阈值
Z_STOP = 3.0                    # 止损阈值
LOT_SIZE = 1                    # 开仓手数
CLOSE_TIME = time(14, 55)       # 收盘前平仓


class CointegrationArbitrageStrategy:
    """金融期货协整套利策略"""

    def __init__(self, api):
        self.api = api
        self.position_if = 0     # IF持仓（正=多头，负=空头）
        self.position_ic = 0     # IC持仓
        self.entry_z = 0         # 入场时的z-score
        self.in_position = False

    def get_price_ratio(self, n=LOOKBACK + 10):
        """获取 IF/IC 价比序列"""
        try:
            if_kl = self.api.get_kline_serial(SYMBOL_IF, KLINE_DURATION, n)
            ic_kl = self.api.get_kline_serial(SYMBOL_IC, KLINE_DURATION, n)
            if len(if_kl) < n or len(ic_kl) < n:
                return []
            if_prices = if_kl['close'].values
            ic_prices = ic_kl['close'].values
            # 价比：IC/IF，反映大小盘相对强弱
            ratio = ic_prices / if_prices
            return ratio
        except Exception as e:
            print(f"获取价比失败: {e}")
            return []

    def calculate_z_score(self, ratios):
        """计算价比的 z-score"""
        if len(ratios) < LOOKBACK:
            return 0
        window = ratios[-LOOKBACK:]
        mean = np.mean(window)
        std = np.std(window)
        if std == 0:
            return 0
        current = ratios[-1]
        z = (current - mean) / std
        return z

    def open_pair_position(self, direction):
        """
        开设配对仓位
        direction > 0: 做多IF，做空IC（价比预期下降，即小盘强于大盘）
        direction < 0: 做空IF，做多IC（价比预期上升，即大盘强于小盘）
        """
        try:
            if direction > 0:
                # 预期价比上升（IC强于IF）→ 做多IC，做空IF
                self.api.insert_order(
                    symbol=SYMBOL_IF, direction="SELL", offset="OPEN", volume=LOT_SIZE
                )
                self.api.insert_order(
                    symbol=SYMBOL_IC, direction="BUY", offset="OPEN", volume=LOT_SIZE
                )
                self.position_if = -LOT_SIZE
                self.position_ic = LOT_SIZE
                print(f"[{datetime.now()}] 开仓: 做多IC/做空IF (价比上升)")
            else:
                # 预期价比下降（IF强于IC）→ 做多IF，做空IC
                self.api.insert_order(
                    symbol=SYMBOL_IF, direction="BUY", offset="OPEN", volume=LOT_SIZE
                )
                self.api.insert_order(
                    symbol=SYMBOL_IC, direction="SELL", offset="OPEN", volume=LOT_SIZE
                )
                self.position_if = LOT_SIZE
                self.position_ic = -LOT_SIZE
                print(f"[{datetime.now()}] 开仓: 做多IF/做空IC (价比下降)")
            self.in_position = True
        except Exception as e:
            print(f"开仓失败: {e}")

    def close_pair_position(self, reason=""):
        """平掉配对仓位"""
        try:
            if self.position_if > 0:
                self.api.insert_order(
                    symbol=SYMBOL_IF, direction="SELL", offset="CLOSE", volume=self.position_if
                )
            elif self.position_if < 0:
                self.api.insert_order(
                    symbol=SYMBOL_IF, direction="BUY", offset="CLOSE", volume=abs(self.position_if)
                )
            if self.position_ic > 0:
                self.api.insert_order(
                    symbol=SYMBOL_IC, direction="SELL", offset="CLOSE", volume=self.position_ic
                )
            elif self.position_ic < 0:
                self.api.insert_order(
                    symbol=SYMBOL_IC, direction="BUY", offset="CLOSE", volume=abs(self.position_ic)
                )
            pnl = abs(self.entry_z - self.z_score) if self.in_position else 0
            print(f"[{datetime.now()}] 平仓: {reason}, z变化={pnl:.3f}")
            self.position_if = 0
            self.position_ic = 0
            self.in_position = False
        except Exception as e:
            print(f"平仓失败: {e}")

    def should_close_all(self):
        """收盘前强平"""
        return datetime.now().time() >= CLOSE_TIME

    def run(self):
        """运行策略"""
        print("=" * 60)
        print("金融期货协整套利策略启动")
        print(f"IF/IC 协整套利，入场z={Z_ENTRY}，出场z={Z_EXIT}，止损z={Z_STOP}")
        print("=" * 60)

        while True:
            self.api.wait_update()

            ratios = self.get_price_ratio()
            if len(ratios) < LOOKBACK:
                continue

            self.z_score = self.calculate_z_score(ratios)
            current_ratio = ratios[-1]

            print(f"[{datetime.now()}] 价比={current_ratio:.4f}, z-score={self.z_score:.3f}, "
                  f"IF持仓={self.position_if}, IC持仓={self.position_ic}")

            # 入场逻辑
            if not self.in_position:
                if self.z_score > Z_ENTRY:
                    # 价比偏高（IC相对IF偏贵），预期回归
                    self.entry_z = self.z_score
                    self.open_pair_position(1)  # 做多IC/做空IF
                elif self.z_score < -Z_ENTRY:
                    # 价比偏低（IF相对IC偏贵），预期回归
                    self.entry_z = self.z_score
                    self.open_pair_position(-1)  # 做多IF/做空IC
            else:
                # 持仓中：出场或止损
                z_change = abs(self.z_score - self.entry_z)
                if z_change >= Z_STOP:
                    print(f"[{datetime.now()}] 触发止损，z变化={z_change:.3f}")
                    self.close_pair_position("止损")
                elif abs(self.z_score) <= Z_EXIT:
                    print(f"[{datetime.now()}] 价差回归，平仓")
                    self.close_pair_position("价差回归")

            # 收盘前强平
            if self.should_close_all() and self.in_position:
                print(f"\n[{datetime.now()}] 收盘前平仓")
                self.close_pair_position("收盘")
                break


# ============ 主函数 ============
if __name__ == "__main__":
    # 实盘账户
    api = TqApi(auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))

    # 模拟测试
    # api = TqApi(auth=TqSim())

    try:
        strategy = CointegrationArbitrageStrategy(api)
        strategy.run()
    except KeyboardInterrupt:
        print("\n策略停止")
    finally:
        api.close()
