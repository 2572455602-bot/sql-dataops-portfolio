# 复现指南

## 目标

这份指南供代码评审者在新目录中验证：六表 fixture 能重建数仓、测试能通过、失败批次不会覆盖成功发布、Dashboard 只读取经过门禁的 ADS。

## 环境

- macOS 与 `make`
- Python 3.9+
- 首次安装依赖时可联网
- 数 GB 可用磁盘空间

项目固定使用 Java 17。若系统没有合适版本，bootstrap 会准备项目本地 JDK，不要求 Homebrew 或 Docker。

## 最短复现路径

```bash
make bootstrap
make demo
make test
make dashboard
```

预期结果：

- `make bootstrap` 完成 Java、SparkSession、Hive Metastore 与 Parquet smoke test；
- `make demo` 生成固定种子六表数据，并发布 `DEMO / SYNTHETIC_FIXTURE` manifest；
- `make test` 以非零失败/零成功的标准退出码报告测试结果；
- `make dashboard` 在 `http://127.0.0.1:8501` 打开最后一个成功发布版本。

检查机器证据：

```bash
python3 -m json.tool bi_exports/current/manifest.json
.venv/bin/python -c "import pandas as pd; print(pd.read_csv('bi_exports/current/ads_dataops_health.csv').to_string(index=False))"
```

manifest 至少应包含 run ID、数据模式、来源状态、六文件 SHA-256、合计行数、日期范围、Spark/SQL 版本、耗时、质量状态与发布状态。

## 构建展示产物

```bash
make pages
make package
```

- 极简静态页写入 `dist/pages/`。
- 可复现源码 ZIP 与 SHA-256 写入 `dist/`。
- 原始六表、虚拟环境、本地 JDK、Spark/Hive 运行目录、缓存、密钥和 Git 历史不会打包。

## 运行外部六表目录

先阅读 [`DATASET_NOTICE.md`](DATASET_NOTICE.md)，再运行：

```bash
make full DATA_DIR=/absolute/path/dataset
```

`DATA_DIR` 必须指向同时包含以下文件的目录：

```text
users.csv
products.csv
orders.csv
user_behaviors.csv
user_features.csv
product_features.csv
```

成功的外部运行记录为 `PORTFOLIO / UNVERIFIED`。这表示数据已通过项目工程检查，不表示来源真实或属于某家公司。

## 验证失败保护

```bash
make recording-demo
```

该流程应在隔离运行目录中先发布成功批次，再注入坏数据并证明最后一个成功版本的校验和没有变化。也可以运行原子发布相关的定向测试：

```bash
.venv/bin/pytest -q tests/unit/test_atomic_publish.py
```

## 常见问题

| 现象 | 检查 |
|---|---|
| 缺文件或表头不一致 | 对照 `DATASET_NOTICE.md` 的六个精确表头 |
| critical 质量检查失败 | 查看失败 manifest、quarantine 与 `ads_dataops_health.csv`，不要手工复制候选结果到 `current` |
| 有 warning | 判断是否属于已知且公开的源数据问题；warning 不应被隐藏 |
| Dashboard 缺数据 | 确认 `bi_exports/current` 指向成功 release，且 8 个 ADS CSV 与 manifest 同批次 |
| Spark 启动失败 | 重新运行 `make bootstrap`，确认可用磁盘与 Java 17 |

## 安全与诚实边界

- 不提交或分发六个原始 CSV。
- 不公开凭证、Cookie、Token、个人路径或明细样本。
- 不把 `PORTFOLIO` 写成“生产”或“真实公司”。
- 不把源金额汇总写成经审计企业收入。
- ZIP 是可复现源码包，不是包含全部依赖的离线镜像。
