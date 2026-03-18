# tqsdk-financials 股指期货策略库

> 基于 [TqSdk（天勤量化）](https://doc.shinnytech.com/tqsdk/latest/) 的股指期货量化策略集合。  
> 涵盖沪深300(IF)、中证500(IC)、中证1000(IM)、上证50(IH)等股指期货品种的趋势跟踪、均值回归、跨品种套利等多类策略。

---

## 📋 策略列表

| 编号 | 文件名 | 策略名称 | 品种 | 核心思路 | 上线日期 |
|------|--------|----------|------|----------|----------|
| 01 | [01_if_trend.py](strategies/01_if_trend.py) | IF趋势跟踪策略 | 沪深300 IF | 双均线趋势跟踪，10/30日均线金叉死叉 | 2026-03-02 |
| 02 | [02_ic_if_spread.py](strategies/02_ic_if_spread.py) | IC-IF跨品种套利 | 中证500/沪深300 | 跨品种均值回归套利 | 2026-03-02 |
| 03 | [03_if_mean_reversion.py](strategies/03_if_mean_reversion.py) | IF均值回归策略 | 沪深300 IF | 布林带均值回归 | 2026-03-03 |
| 04 | [04_ic_if_spread.py](strategies/04_ic_if_spread.py) | IC-IF统计套利 | 中证500/沪深300 | 统计套利策略 | 2026-03-03 |
| 05 | [05_if_breakout.py](strategies/05_if_breakout.py) | IF突破策略 | 沪深300 IF | 布林带突破策略 | 2026-03-04 |
| 06 | [06_if_ic_spread.py](strategies/06_if_ic_spread.py) | IF-IC跨期套利 | 沪深300/中证500 | 跨品种价差交易 | 2026-03-04 |
| 07 | [07_if_multi_timeframe.py](strategies/07_if_multi_timeframe.py) | IF多周期策略 | 沪深300 IF | 日线+4H共振趋势 | 2026-03-04 |
| 08 | [08_ih_ic_spread.py](strategies/08_ih_ic_spread.py) | IH-IC跨品种策略 | 上证50/中证500 | 跨品种对冲 | 2026-03-04 |
| 09 | [09_if_inter_temporal.py](strategies/09_if_inter_temporal.py) | IF跨周期策略 | 沪深300 IF | 多周期共振 | 2026-03-04 |
| 10 | [10_ts_ma_crossover.py](strategies/10_ts_ma_crossover.py) | TS均线交叉 | 沪深300 IF | 均线交叉趋势 | 2026-03-04 |
| 11 | [11_if_ic_pairs.py](strategies/11_if_ic_pairs.py) | IF-IC配对交易 | 沪深300/中证500 | 配对均值回归 | 2026-03-05 |
| 12 | [12_if_trend_following.py](strategies/12_if_trend_following.py) | IF趋势跟随 | 沪深300 IF | ATR动态止损趋势 | 2026-03-05 |
| 13 | [13_ts_trend_following.py](strategies/13_ts_trend_following.py) | TS趋势跟随 | 沪深300 IF | 趋势线跟随 | 2026-03-06 |
| 14 | [14_im_multi_factor.py](strategies/14_im_multi_factor.py) | IM多因子策略 | 中证1000 IM | 多因子综合打分 | 2026-03-06 |
| 15 | [15_ih_rsi_strategy.py](strategies/15_ih_rsi_strategy.py) | IH RSI策略 | 上证50 IH | RSI超买超卖 | 2026-03-09 |
| 16 | [16_if_macd_strategy.py](strategies/16_if_macd_strategy.py) | IF MACD策略 | 沪深300 IF | MACD趋势交易 | 2026-03-09 |
| 17 | [17_im_momentum.py](strategies/17_im_momentum.py) | IM动量策略 | 中证1000 IM | 动量指标交易 | 2026-03-11 |
| 17 | [17_ts_ma_crossover.py](strategies/17_ts_ma_crossover.py) | TS均线交叉 | 沪深300 IF | 多均线交叉 | 2026-03-11 |
| 18 | [18_ic_boll_breakout.py](strategies/18_ic_boll_breakout.py) | IC布林突破 | 中证500 IC | 布林带突破 | 2026-03-11 |
| 18 | [18_if_range_breakout.py](strategies/18_if_range_breakout.py) | IF区间突破 | 沪深300 IF | 价格区间突破 | 2026-03-11 |
| 19 | [19_im_boll_trend.py](strategies/19_im_boll_trend.py) | IM布林趋势 | 中证1000 IM | 布林带中轨趋势 | 2026-03-13 |
| 20 | [20_tf_volatility.py](strategies/20_tf_volatility.py) | 波动率交易策略 | 沪深300 IF | 波动率突破策略 | 2026-03-13 |
| 21 | [21_if_ic_spread.py](strategies/21_if_ic_spread.py) | IF-IC跨品种统计套利 | 沪深300/中证500 | 统计套利 | 2026-03-16 |
| 22 | [22_if_multi_factor.py](strategies/22_if_multi_factor.py) | IF多因子策略 | 沪深300 IF | 多因子综合打分 | 2026-03-16 |
| 23 | [23_if_ic_ih_cross_section.py](strategies/23_if_ic_ih_cross_section.py) | IF-IC-IH截面策略 | 三品种截面 | 截面排序做多做空 | 2026-03-17 |
| 24 | [24_multi_factor_rotation.py](strategies/24_multi_factor_rotation.py) | 多因子轮动策略 | 三品种轮动 | 因子轮动配置 | 2026-03-17 |
| 25 | [25_if_ic_im_cointegration.py](strategies/25_if_ic_im_cointegration.py) | 股指期货协整套利策略 | IF/IC/IM | 三品种协整天数回归套利 | 2026-03-18 |
| 26 | [26_if_dual_ma_vol_filter.py](strategies/26_if_dual_ma_vol_filter.py) | IF双均线波动率过滤策略 | 沪深300 IF | 双均线+ATR波动率过滤 | 2026-03-18 |

---

## 🏗️ 仓库结构

```
tqsdk-financials/
├── README.md                        # 本文档
└── strategies/                      # 策略文件目录
    ├── 01_if_trend.py               # IF趋势跟踪
    ├── 23_if_ic_ih_cross_section.py # 三品种截面策略
    └── 26_if_dual_ma_vol_filter.py  # 双均线波动率过滤策略
```

---

## ⚙️ 使用方法

### 安装依赖

```bash
pip install tqsdk pandas numpy
```

### 运行策略（模拟账户）

```bash
python strategies/01_if_trend.py
```

### 切换实盘账户

将策略文件中的 `TqSim()` 替换为真实账户：

```python
from tqsdk import TqAccount
api = TqApi(
    account=TqAccount("期货公司名称", "账号", "密码"),
    auth=TqAuth("天勤用户名", "天勤密码")
)
```

---

## ⚠️ 风险提示

> **本仓库内策略仅供学习研究使用，不构成任何投资建议。**  
> 期货交易存在较高风险，请在充分了解品种特性和策略逻辑后，  
> 先通过**模拟账户**或**历史回测**验证，再考虑实盘运行。  
> 实盘亏损由交易者自行承担，作者不对任何损失负责。

---

## 📅 更新日志

| 日期 | 变更 |
|------|------|
| 2026-03-18 | 新增第25、26号策略：协整套利策略、双均线波动率过滤策略 |
| 2026-03-17 | 新增第23、24号策略：三品种截面策略、多因子轮动策略 |
| 2026-03-16 | 新增第21、22号策略：IF-IC统计套利、多因子策略 |
| 2026-03-13 | 新增第19、20号策略：布林趋势、波动率策略 |
| 2026-03-11 | 新增第17、18号策略：动量策略、布林突破 |
| 2026-03-09 | 新增第15、16号策略：RSI策略、MACD策略 |
| 2026-03-06 | 新增第13、14号策略：趋势跟随、多因子策略 |
| 2026-03-05 | 新增第11、12号策略：配对交易、趋势跟随 |
| 2026-03-04 | 新增第9、10号策略：跨周期策略、均线交叉 |
| 2026-03-03 | 新增第3、4号策略：均值回归、统计套利 |
| 2026-03-02 | 初始化仓库，上传趋势跟踪和套利基础策略 |

---

*Powered by [TqSdk](https://doc.shinnytech.com/tqsdk/latest/) · 天勤量化*
