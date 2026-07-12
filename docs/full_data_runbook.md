# 外部六表运行手册

## 适用范围

用于运行一个仓库外的六表目录：

```bash
make full DATA_DIR=/absolute/path/dataset
```

当前外部样本来源未验证且疑似合成。成功运行只会生成 `PORTFOLIO / UNVERIFIED`，不得改写成真实公司、淘宝、阿里或生产数据。

## 1. 运行前来源记录

在仓库外记录：数据提供方、获得日期、原始页面或交付说明、许可条款、文件版本和官方校验值（若存在）。如果这些信息缺失，保留 `UNVERIFIED`。

不要把账号、密码、Cookie、Token、明细样本或原始文件放入仓库、issue、录屏或聊天记录。

## 2. 环境基线

```bash
df -h .
make bootstrap
make demo
make test
```

DEMO 或测试未通过时，不继续外部数据运行。完整运行期间避免电脑休眠，也不要并行启动另一个 `make demo`/`make full`。

## 3. 文件契约

目标目录必须包含：

```text
users.csv
products.csv
orders.csv
user_behaviors.csv
user_features.csv
product_features.csv
```

文件必须为带表头 UTF-8 CSV；精确表头见 [`../DATASET_NOTICE.md`](../DATASET_NOTICE.md)。流水线会检查文件存在、非空、精确表头、每行列宽和 SHA-256。

只做不会修改文件的检查：

```bash
find /absolute/path/dataset -maxdepth 1 -type f -name '*.csv' -print
du -sh /absolute/path/dataset
```

无需把明细打印到终端或复制进项目。

## 4. 保存当前成功版本基线

```bash
python3 -m json.tool bi_exports/current/manifest.json
find -L bi_exports/current -maxdepth 1 -type f -exec shasum -a 256 {} \; | sort
```

把基线保存在仓库外。不要手工删除或修改 `bi_exports/current`。

## 5. 执行

```bash
make full DATA_DIR=/absolute/path/dataset
```

- 退出码 `0`：候选批次通过所有 critical 检查并已发布；仍需人工复核。
- 非 `0`：批次未发布。检查错误、失败 manifest 与 quarantine；不要手工复制候选 CSV。

## 6. 成功复核

### Manifest

```bash
python3 -m json.tool bi_exports/current/manifest.json
```

确认：

- [ ] `data_mode = PORTFOLIO`、`source_status = UNVERIFIED`；
- [ ] `status = success`、`published = true`；
- [ ] 目录标识、六文件行数和 SHA-256 与本次输入一致；
- [ ] `RAW = valid + quarantine`，DWD 行数存在；
- [ ] 日期范围、Spark 版本、SQL bundle SHA-256、耗时均有记录；
- [ ] `quality.failed_checks = 0`；
- [ ] run ID 与 `current` 指向的 release 一致。

### Quality

```bash
.venv/bin/python -c "import pandas as pd; print(pd.read_csv('bi_exports/current/ads_dataops_health.csv').to_string(index=False))"
```

所有 `severity = critical` 必须 pass。warning 必须解释，不能隐藏。当前已知 warning 类型包括注册前事件、`unit_price × quantity` 差异和特征哨兵值。

### ADS

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import pandas as pd

for path in sorted(Path('bi_exports/current').glob('ads_*.csv')):
    frame = pd.read_csv(path)
    print(path.name, len(frame), list(frame.columns))
PY
```

确认 8 个 ADS 均非空，KPI 与质量页的模式/来源声明一致。然后运行：

```bash
make dashboard
make pages
```

## 7. 失败处理

| 问题 | 处理 |
|---|---|
| 缺文件、错表头、列宽错误 | 获取符合六表契约的版本，不让 SQL 猜列 |
| 主键重复或外键缺失 | 追查来源生成逻辑；不要任意去重或补父记录 |
| 金额公式 critical 失败 | 确认 `actual_payment = total_amount - discount` 语义与精度 |
| 生命周期失败 | 检查发货/收货时间与状态顺序 |
| 特征快照对账失败 | 以订单/行为事实为业务真值，调查快照生成时间与规则 |
| 注册前事件 | 保留 quarantine 与 warning，确认注册日期或事件时间是否可信 |
| Spark/磁盘失败 | 修复环境后用同一输入重跑；上一成功版本仍应可用 |

失败后重新运行前，再比较 `current` 文件校验和，确认上一版未变化。

## 8. 对外材料更新规则

外部运行成功后，可以引用本次 manifest 中的“样本行数、隔离数、项目计算结果和质量状态”，但必须同时保留 `UNVERIFIED` 与“疑似合成样本”说明。

不能使用：

- “真实公司数据”“生产数据”“淘宝/阿里数据”；
- “企业真实 GMV/收入/利润”；
- “质量通过所以来源真实”；
- 不同 run ID 混合出的数字、截图或耗时。

对外截图、视频和简历数字应引用同一个 run ID，并展示数据模式、来源状态与质量结果。
