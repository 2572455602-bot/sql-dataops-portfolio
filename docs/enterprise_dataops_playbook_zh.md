# 企业级 DataOps 能力展示手册

## Audience

面向数据开发、数仓、BI、DataOps 岗位面试官。

## Purpose

说明这个作品项目如何映射到公司里的日常数据平台运作：持续接入数据、质量门禁、原子发布、监控告警、事故处理和版本追溯。本文强调能力证明，不把本地 MVP 包装成真实生产平台。

## Overview

当前项目已经实现的是“质量门禁保护的批处理发布”：

```text
source CSV
→ RAW / ODS / DWD / DWS / ADS
→ quality checks
→ candidate release
→ atomic current publish
→ Streamlit / GitHub Pages
```

企业环境里，同一套思想会扩展为“按分区持续运行的数据产品”：

```text
daily landing area
→ partitioned RAW
→ incremental ODS / DWD merge
→ DWS / ADS rebuild for affected windows
→ blocking quality gates
→ publish current only after pass
→ monitor freshness, volume, failures, and SLA
```

## Procedure Or Reference

### 1. 数据接入

| 公司场景 | 本项目如何体现 | 后续可扩展 |
|---|---|---|
| 每天新文件、API、CDC 或消息数据进入落地区 | `make full DATA_DIR=...` 接收外部六表目录 | 增加 `make incremental DATA_DIR=... RUN_DATE=...` |
| 原始数据不可变，便于重跑和审计 | `bi_exports/releases/` 保留不可变发布结果 | RAW 按 `dt=YYYY-MM-DD` 分区保存 |
| 输入必须有契约 | 六表文件名、表头、类型、枚举和主键检查 | 契约版本化，新增 schema compatibility check |

### 2. 增量处理

企业里不会每天无脑全量重算所有历史。更常见的策略是：

- 新数据按日期或批次进入 RAW 分区；
- ODS 只标准化新增分区；
- DWD 对订单、用户、商品等维度做幂等 upsert 或 overwrite affected partition；
- DWS/ADS 只重算受影响日期窗口；
- 对晚到数据和回填数据使用明确的 backfill run_id。

本项目当前是全量重跑 MVP，但已经具备增量化的关键前提：固定输入契约、SQL 分层、manifest、质量门禁、不可变 release 和原子 current。

### 3. 质量门禁

| 门禁类型 | 本项目已有证据 |
|---|---|
| 文件与 schema | 六表必需文件、字段和类型检查 |
| 必填字段 | ID、时间、状态、金额字段检查 |
| 枚举合法性 | 订单状态、行为类型等枚举检查 |
| 业务规则 | 金额公式、注册前事件隔离 |
| 层间对账 | RAW = valid ODS + quarantine，ODS/DWD/ADS 对账 |
| 发布保护 | 失败运行非零退出，不覆盖最后成功 `current` |

面试表达重点：我不是只做图，而是先保证进入 Dashboard 的数字可解释、可追溯、可阻断。

### 4. 发布与回滚

公司里的 BI 发布不应该直接覆盖线上表。本项目采用候选发布思想：

```text
candidate run directory
→ run quality checks
→ pass: atomically switch current
→ fail: keep previous current
```

这对应企业里的 blue/green、snapshot publish、table swap 或 view pointer 切换。核心能力是“失败批次不影响消费者”。

### 5. 监控与告警

企业级 DataOps 至少需要监控四类信号：

| 监控信号 | 当前项目证据 | 企业扩展 |
|---|---|---|
| Freshness | manifest 记录 run_id、运行时间、数据窗口 | SLA freshness alert |
| Volume | raw_rows、valid_rows、quarantine_rows | 同比/环比波动阈值 |
| Quality | pass/warn/fail 质量结果 | 失败发 Slack/邮件/工单 |
| Runtime | duration_seconds、Spark version | 超时告警和容量评估 |

Streamlit Dashboard 的 `Run health` 区块就是为了把这些信号展示给评审者。

### 6. 事故处理

如果某天新增数据导致门禁失败，处理流程应是：

1. 查看 manifest 和 quality table，确认失败检查。
2. 定位 quarantine 或对账差异。
3. 判断是源数据问题、schema 变更、SQL 逻辑问题还是迟到数据。
4. 修复后用同一 run_date 重跑，保持幂等。
5. 只有全部 blocking checks 通过后才发布。
6. 在 README、runbook 或 incident note 里记录根因和修复动作。

本项目可演示的能力：失败返回非零退出、上一版 Dashboard 不被覆盖、质量结果可在 Dashboard 中查看。

### 7. 权限与数据安全

当前仓库只提交汇总 ADS，不提交原始 CSV；作品 ZIP 也有 raw-data denylist。公司环境还会增加：

- 原始数据在受控对象存储或数仓权限域；
- Dashboard 只暴露聚合数据；
- 生产密钥放在 secret manager；
- CI/CD 日志禁止打印敏感字段；
- 不同角色使用最小权限访问。

## Risks Or Notes

- 当前样本来源仍是 `UNVERIFIED`，不能宣称真实公司生产数据。
- 当前调度是本地 `make` 和 GitHub Actions，不等同于 Airflow、DataWorks、Dagster 或云上生产调度。
- 当前增量命令是设计目标，不是已经上线的生产功能。
- Tableau Public 工作簿仍需在 Tableau 中另行制作与验证；当前在线 Dashboard 是 Streamlit。

## 面试讲法

> 这个项目我想展示的不是“做了几张图”，而是把一个数据产品从输入契约、SQL 分层、质量门禁、失败保护、manifest 追溯到 Dashboard 发布完整串起来。  
> 如果放到公司长期运营，我会把当前全量批处理扩展为按日期分区的增量流水线，用水位线控制每日新增数据，用 blocking quality gates 阻断坏批次，用不可变 release 和 current 指针保护线上 Dashboard，再用 freshness、volume、quality、runtime 四类信号做监控告警。
