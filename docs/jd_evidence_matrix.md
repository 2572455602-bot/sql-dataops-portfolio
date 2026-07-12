# JD—项目证据矩阵

## 使用方法

先把目标 JD 的关键词放到第一列，再用仓库中可打开、可运行的证据支撑。不能因为数据经过质量门禁，就把 `UNVERIFIED` 来源写成真实公司经验。

| 常见 JD 能力 | 项目证据 | 面试可演示 | 诚实边界 |
|---|---|---|---|
| SQL / 复杂聚合 | [`sql/`](../sql/) 中八个版本化 SparkSQL 文件 | 订单状态条件聚合、客户分群、窗口函数漏斗、品类排名 | 没在企业生产集群运行 |
| 数仓建模 | RAW/ODS/DWD/DWS/ADS；订单与行为双事实 | 解释表粒度、维度复用、feature snapshot 为何只审计 | 本地 Hive 不是企业数据平台 |
| Spark / 大数据处理 | PySpark 4.0.3、Hive Metastore、Parquet | `make demo` 重建完整分层 | 当前外部样本仅 59,000 行，不能夸大规模 |
| 数据质量 | [`sql/90_quality.sql`](../sql/90_quality.sql)、quarantine、20 项检查 | 展示 16 pass、0 fail、4 warning 与 740 隔离行 | pass 不证明来源真实；warning 不能隐藏 |
| DataOps / 可追溯 | manifest、六文件/SQL 哈希、不可变 release、原子切换 | 注入坏批次，证明 `current` 不变 | Make/Python 不是 Airflow/DataWorks 调度 |
| Python 工程 | [`ecommerce_dataops/`](../ecommerce_dataops/) 编排、契约、fixture、发布 | 解释“Python 管流程，SQL 管口径” | 不声称有两套独立业务逻辑 |
| 自动化测试 | [`tests/`](../tests/) 的契约、golden、异常、幂等、发布与 UI 测试 | `make test` 或定向失败保护测试 | 本地测试不等同生产 SLA |
| BI / Dashboard | [`dashboard/`](../dashboard/)、8 张 ADS 汇总 | KPI、趋势、状态、品类、小时、分群、质量 | Tableau 工作簿须在实际 Tableau 中另行验证 |
| 指标设计 | [指标字典](metric_dictionary.md) | 解释完成率、重复完成用户率、跨商品顺序漏斗 | 不写真实企业 GMV、归因或因果 |
| 文档与交接 | README、血缘、runbook、复现指南、ZIP | 让评审者用 4 条命令复跑 | 原始数据不进入交付包 |
| 数据治理诚信 | `PORTFOLIO / UNVERIFIED` 全链路声明 | 解释质量状态与来源状态为何分开 | 不能称淘宝、阿里或真实公司项目 |

## 当前外部样本可以引用的证据

以最新 [`manifest.json`](../bi_exports/current/manifest.json) 为准。当前记录：六表 59,000 行、有效 58,260 行、隔离 740 行、20 项检查中 0 fail。引用这些数字时必须同时写“来源未验证、疑似合成样本”。

## 不应对齐的 JD 项

以下能力当前没有仓库证据，应标为“未覆盖”或“可迁移思路”，不要硬贴标签：

- Airflow/DataWorks/Dagster 等生产调度；
- 云数仓、湖仓表格式与集群部署；
- 实时流、CDC、消息队列；
- 企业 IAM、数据分级、Catalog 与字段级自动血缘；
- SLA/SLO、PagerDuty/飞书告警、成本治理；
- 机器学习、LLM 自动洞察或因果实验；
- 真实公司业务成果或生产收入影响。

## 针对 JD 改写的公式

每条简历描述使用：

```text
动作 + 技术对象 + 可核验证据 + 业务/工程价值 + 边界
```

示例：

> 使用 SparkSQL 构建六表电商 RAW→ADS 五层数仓，将订单与行为拆分为双事实，并通过 20 项质量检查、quarantine 和原子发布保护 BI 当前版本；已在 59,000 行来源未验证的作品样本上完成端到端验证。

不要写：

> 为淘宝搭建生产 DataOps 平台，处理真实企业交易数据并提升收入。

前者每个主张都能在仓库核验；后者没有来源、生产或业务影响证据。
