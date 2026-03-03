# tqsdk-financials

> 基于 **TqSdk** 的金融期货策略，持续更新中。

## 项目简介

本仓库专注于**金融期货量化策略**，涵盖股指期货等品种。  
所有策略使用 [天勤量化 TqSdk](https://github.com/shinnytech/tqsdk-python) 实现。

## 策略列表

| # | 策略名称 | 类型 | 品种 | 文件 |
|---|---------|------|------|------|
| 01 | 沪深300股指期货趋势策略 | 趋势跟踪 | IF | [01_if_trend.py](strategies/01_if_trend.py) |
| 02 | IC-IF价差策略 | 价差套利 | IC + IF | [02_ic_if_spread.py](strategies/02_ic_if_spread.py) |
| 03 | 沪深300均值回归策略 | 均值回归 | IF | [03_if_mean_reversion.py](strategies/03_if_mean_reversion.py) |
| 04 | 中证500-沪深300价差策略 | 价差套利 | IC + IF | [04_ic_if_spread.py](strategies/04_ic_if_spread.py) |

## 更新日志

- 2026-03-03: 新增策略03（均值回归）、策略04（IC-IF价差）
