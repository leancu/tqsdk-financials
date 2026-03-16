# tqsdk-financials

> 基于 **TqSdk** 的金融期货策略集合，持续更新中。

## 项目简介

本仓库专注于**金融期货量化策略**，涵盖股指期货、国债期货等方向。  
所有策略使用 [天勤量化 TqSdk](https://github.com/shinnytech/tqsdk-python) 实现，可直接对接实盘账户。

## 策略列表

| # | 策略名称 | 类型 | 标的 | 文件 |
|---|---------|------|------|------|
| 01 | IF 股指期货趋势追踪策略 | 趋势跟踪 | IF | [01_if_trend.py](strategies/01_if_trend.py) |
| 02 | IC-IF 跨品种套利策略 | 跨品种套利 | IC, IF | [02_ic_if_spread.py](strategies/02_ic_if_spread.py) |
| 03 | IF 均值回归策略 | 均值回归 | IF | [03_if_mean_reversion.py](strategies/03_if_mean_reversion.py) |
| 04 | IC-IF 跨品种价差策略 | 跨品种套利 | IC, IF | [04_ic_if_spread.py](strategies/04_ic_if_spread.py) |
| 05 | IF 布林带突破策略 | 布林带突破 | IF | [05_if_breakout.py](strategies/05_if_breakout.py) |
| 06 | IF 多时间周期共振策略 | 多周期共振 | IF | [06_if_multi_timeframe.py](strategies/06_if_multi_timeframe.py) |
| 07 | IF 均线交叉策略 | 均线策略 | IF | [07_if_ma_crossover.py](strategies/07_if_ma_crossover.py) |
| 08 | IH-IC 跨品种价差策略 | 跨品种套利 | IH, IC | [08_ih_ic_spread.py](strategies/08_ih_ic_spread.py) |
| 09 | 国债期货趋势跟踪策略 | 趋势跟踪 | TF | [09_tf_trend.py](strategies/09_tf_trend.py) |
| 10 | TS 均线交叉策略 | 均线策略 | TS | [10_ts_ma_crossover.py](strategies/10_ts_ma_crossover.py) |
| 11 | IC 股指配对策略 | 配对交易 | IC | [11_if_ic_pairs.py](strategies/11_if_ic_pairs.py) |
| 12 | IF 趋势跟踪策略 | 趋势跟踪 | IF | [12_if_trend_following.py](strategies/12_if_trend_following.py) |
| 13 | TS 趋势跟踪策略 | 趋势跟踪 | TS | [13_ts_trend_following.py](strategies/13_ts_trend_following.py) |
| 14 | IM 多因子策略 | 多因子 | IM | [14_im_multi_factor.py](strategies/14_im_multi_factor.py) |
| 15 | IF 波动率突破策略 | 波动率策略 | IF | [15_if_vol_breakout.py](strategies/15_if_vol_breakout.py) |
| 16 | IC 动量策略 | 动量策略 | IC | [16_ic_momentum.py](strategies/16_ic_momentum.py) |
| 17 | IM 动量策略 | 动量策略 | IM | [17_im_momentum.py](strategies/17_im_momentum.py) |
| 18 | TS 均线交叉策略 | 均线策略 | TS | [18_ts_ma_crossover.py](strategies/18_ts_ma_crossover.py) |
| 19 | 中证1000布林带趋势策略 | 布林带趋势 | IM | [19_im_boll_trend.py](strategies/19_im_boll_trend.py) |
| 20 | 国债期货波动率套利策略 | 波动率策略 | TF | [20_tf_volatility.py](strategies/20_tf_volatility.py) |
| 21 | IF-IC跨品种价差量化策略 | 跨品种套利 | CFFEX.if + CFFEX.ic | [21_if_ic_spread.py](strategies/21_if_ic_spread.py) |
| 22 | 沪深300多因子量化策略 | 多因子策略 | CFFEX.if | [22_if_multi_factor.py](strategies/22_if_multi_factor.py) |

## 策略分类

### 📈 趋势跟踪（Trend Following）
基于均线、趋势线等技术指标捕捉价格趋势。

### 🔄 跨品种套利（Cross-Product Arbitrage）
利用股指期货不同品种之间的价差关系。

### 📊 多因子策略（Multi-Factor）
结合多个因子进行选股和交易。

### 📉 波动率策略（Volatility Trading）
基于波动率变化进行交易的策略。

## 环境要求

```bash
pip install tqsdk numpy pandas
```

## 风险提示

- 金融期货杠杆较高，请谨慎操作
- 跨品种套利需注意品种相关性变化
- 本仓库策略仅供学习研究，不构成投资建议

---

**持续更新中，欢迎 Star ⭐ 关注**

*更新时间：2026-03-13*
