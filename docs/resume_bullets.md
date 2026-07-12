# 简历项目描述

## 推荐标题

**电商六表 SparkSQL 数仓与 DataOps 分析平台｜个人作品项目**

不要在标题中加入淘宝、阿里、真实公司或生产数据。

## 中文四条版

- 使用 PySpark 4.0.3、SparkSQL、Hive Metastore 与 Parquet 构建 `RAW → ODS → DWD → DWS → ADS` 五层电商数仓，将用户、商品、订单、行为与两张特征快照按明确粒度建模，业务口径集中在版本化 SQL。
- 设计订单与行为双事实模型及 8 张 Dashboard ADS，覆盖完成订单样本金额/完成率、状态分布、每日趋势、小时行为、品类表现、互斥客户分群和用户级跨商品顺序漏斗。
- 实现 20 项 DataOps 检查、统一 quarantine、六文件/SQL SHA-256 manifest、不可变 release 与原子切换；critical 失败返回非零并保留最后一个成功 BI 版本。
- 通过固定种子六表 fixture、pytest、Streamlit 和可复现 ZIP 完成交付；外部作品样本运行 59,000 行，其中 58,260 行有效、740 行隔离、0 项 critical 失败，并明确标注来源未验证且疑似合成。

## 中文两条精简版

- 独立构建六表电商 SparkSQL/Hive 五层数仓与 Streamlit Dashboard，将订单、行为、客户、品类和质量指标统一输出为 8 张 ADS 汇总表。
- 建立 20 项质量检查、quarantine、run manifest 和失败安全原子发布；已在 59,000 行 `PORTFOLIO / UNVERIFIED` 样本完成端到端验证，不将其描述为真实公司数据。

## English version

- Built a five-layer SparkSQL/Hive warehouse for a six-table e-commerce schema, separating order and behavior facts and publishing eight aggregate ADS datasets for KPI, trend, status, category, segment, funnel, and data-quality views.
- Implemented 19 DataOps checks, quarantine, file/SQL fingerprints, run manifests, immutable releases, and atomic last-good publication; validated 59,000 source-unverified, apparently synthetic portfolio rows without presenting them as real company data.

## 面试一句话

> 我做的不只是电商 Dashboard，而是一条可以重跑、对账、阻断坏批次并追溯到输入与 SQL 版本的数据产品流水线；同时把质量通过和来源真实性分开管理。

## 可替换数字规则

数字只能从同一个成功 [`manifest.json`](../bi_exports/current/manifest.json) 与 ADS 批次复制。后续运行后，替换：

```text
<raw_rows> / <valid_rows> / <quarantine_rows>
<quality_total> / <failed_checks> / <warning_checks>
<duration_seconds> / <run_id>
```

如果来源仍没有可核验发布主体与许可，无论数据量多大都必须保留 `UNVERIFIED`，不能换成“真实公司数据”。

## 禁止表述

- “为淘宝/阿里搭建数据平台”
- “使用真实公司生产数据”
- “实现企业真实 GMV、收入或利润分析”
- “漏斗证明了浏览导致购买”
- “本地脚本达到企业级生产 DataOps”
- “质量检查通过，所以数据来源真实”

这些主张都超出当前证据。
