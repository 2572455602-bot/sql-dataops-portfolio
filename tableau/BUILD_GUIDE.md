# Tableau 六表电商 Dashboard 制作指南

## 1. 发布前检查

1. 打开 `bi_exports/current/manifest.json`，确认 `status = success`、`published = true`、`quality.failed_checks = 0`。
2. 记录同一批次的 `run_id`、`data_mode`、`source_status` 与日期范围。
3. 当前外部样本必须显示 `PORTFOLIO / UNVERIFIED`；它不能改成真实公司、淘宝、阿里或生产数据。
4. warning 必须能在 `ads_dataops_health.csv` 中解释，不能为了“全绿”而隐藏。

外部六表运行命令是：

```bash
make full DATA_DIR=/absolute/path/dataset
```

## 2. 连接 ADS

Tableau 只连接以下 8 个汇总 CSV，不连接原始六表或 DWD 明细：

```text
ads_executive_kpis.csv
ads_daily_trend.csv
ads_order_status.csv
ads_hourly_behavior.csv
ads_category_performance.csv
ads_customer_segments.csv
ads_sequential_funnel.csv
ads_dataops_health.csv
```

每个文件粒度不同，为每类工作表使用独立数据源，不做物理 join，避免放大 KPI。日期设为 Date，排序/小时设为整数，比率设为 Decimal 并格式化为 Percentage，样本金额设为 Decimal/Number，不加货币符号。

## 3. 建议工作表

1. **4 张 KPI 卡**：`total_orders`、`completed_gmv`（显示名“完成订单样本金额”）、`completed_customers`、`completion_rate`。
2. **Daily trend**：`order_date` 为连续日期；展示 `total_orders` 与 `completed_gmv`，可补 `completed_orders`。
3. **Order status**：按 `status_order` 排序；展示 `order_count` 与 `order_share`。
4. **Category performance**：过滤 `category_rank <= 10`；比较 `completed_gmv`、`completed_orders`、`completed_customers`。
5. **Hourly behavior**：`behavior_hour` 00–23；展示 `browse_events`、`click_events`、`favorite_events`、`cart_events`。
6. **Customer segments**：按 `segment_order` 排序；展示 `user_count` 与 `user_share`。
7. **DataOps health**：显示 check、status、severity、observed/expected 和 details；FAIL/WARN 同时使用文字与颜色。
8. **Sequential funnel（技术下钻，可选）**：按 `stage_order` 展示 `user_count` 和转化率，并注明“用户级、跨商品，不代表归因”。

代码历史字段 `completed_gmv` 在展示层必须称“完成订单样本金额”。来源、币种和会计语义未核验，不加货币符号，也不使用“企业 GMV/收入”标题。

## 4. 组装 Dashboard

建议名称：`E-commerce SQL + DataOps Portfolio`，桌面尺寸 `1366 × 900`。

从上到下：

1. 标题 + `data_mode / source_status` + 日期范围；
2. 4 张 KPI；
3. 每日趋势；
4. 状态 + 品类；
5. 小时行为 + 客户分群；
6. DataOps Health 与 run ID。

外部样本顶栏必须醒目显示：

```text
PORTFOLIO DATA · SOURCE UNVERIFIED
```

DEMO 则显示：

```text
DEMO DATA · SYNTHETIC FIXTURE
```

Phone layout 按 KPI → trend → status → category → segments → health 单列排列。来源状态不能只靠颜色表达。

## 5. 对账

- KPI 与 `ads_executive_kpis.csv` 单行逐项一致；
- 每日订单合计回到 `total_orders`；
- 状态订单合计回到 `total_orders`；
- 五个客户分群人数合计回到 `registered_users`，占比约为 100%；
- 漏斗四阶段人数单调不增；
- 小时为 0–23；
- DataOps 检查条数与 manifest 一致；
- Dashboard 的 run ID、模式、来源状态与所有截图来自同一批次。

## 6. 保存与公开

建议本地路径：

```text
tableau/workbook/ecommerce_dataops_portfolio.twbx
tableau/screenshots/ecommerce_dashboard.png
```

只有在实际 Tableau 中完成对账后才加入工作簿或截图。发布 Tableau Public 前确认只有汇总数据、没有六张原始 CSV、明细、个人路径或凭证，并保留 `UNVERIFIED` 来源声明。

新的成功运行会原子切换 `bi_exports/current`。刷新时逐个 Refresh Extract，再更新 run ID 并重新完成上述对账；失败或 manifest 不完整时，保留上一版工作簿，不发布新截图。
