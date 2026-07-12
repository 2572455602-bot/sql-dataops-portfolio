# Tableau ADS CSV 字典

所有文件来自 `bi_exports/current/`，只包含聚合结果。不同 CSV 粒度不同，不做物理 join。业务定义以 [`../docs/metric_dictionary.md`](../docs/metric_dictionary.md) 为准。

## 公共发布字段

`ads_executive_kpis.csv` 额外带有：

| 字段 | 类型 | 说明 |
|---|---|---|
| `run_date` | DATE | 发布日期 |
| `data_mode` | STRING | `DEMO` 或 `PORTFOLIO` |
| `source_status` | STRING | `SYNTHETIC_FIXTURE` 或 `UNVERIFIED`；页面必须显示 |

## `ads_executive_kpis.csv`

粒度：完整观察窗口一行。

| 字段组 | 字段 | Tableau 类型/显示 |
|---|---|---|
| 日期范围 | `min_order_date`, `max_order_date`, `min_behavior_date`, `max_behavior_date` | Date |
| 订单 | `total_orders`, `ordering_customers`, `paid_orders`, `paid_customers`, `completed_orders`, `completed_customers` | Whole Number |
| 样本金额 | `all_order_amount`, `paid_gmv`, `completed_gmv`, `paid_aov`, `completed_aov` | Decimal/Number；`completed_gmv` 显示为“完成订单样本金额” |
| 风险 | `cancelled_or_refunded_orders`, `completion_rate`, `cancellation_refund_rate` | 整数 / Percentage |
| 重复完成 | `repeat_completed_customers`, `repeat_completed_customer_rate` | 整数 / Percentage |
| 行为 | `behavior_events`, `behavior_users` | Whole Number |
| 目录 | `registered_users`, `products`, `categories` | Whole Number |
| 质量 | `quarantined_rows` | Whole Number |

`paid_gmv`/`completed_gmv` 是代码历史字段名。来源与币种未验证时，不加货币符号，也不在 Tableau 标题中写企业 GMV 或收入。

## `ads_daily_trend.csv`

粒度：一个订单日期。

| 字段 | 类型 | 说明 |
|---|---|---|
| `order_date` | DATE | X 轴 |
| `total_orders`, `ordering_customers`, `units` | INTEGER | 订单、下单用户、商品数量 |
| `all_order_amount`, `paid_gmv`, `completed_gmv`, `discount_amount` | DECIMAL | 金额 |
| `paid_orders`, `completed_orders`, `completed_customers`, `cancelled_or_refunded_orders` | INTEGER | 状态计数 |
| `paid_aov`, `avg_review_score` | DECIMAL | 平均支付金额、完成订单平均评分 |

## `ads_order_status.csv`

粒度：一个源订单状态。

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_order_status` | STRING | 中文显示标签 |
| `status_code` | STRING | 稳定英文键 |
| `status_order` | INTEGER | 固定排序 |
| `order_count`, `customer_count` | INTEGER | 订单与用户数 |
| `order_amount`, `paid_gmv` | DECIMAL | 该状态金额 / 支付生命周期金额 |
| `order_share` | DECIMAL | 格式化为 Percentage |

## `ads_hourly_behavior.csv`

粒度：一个小时（0–23）。

| 字段 | 类型 | 说明 |
|---|---|---|
| `behavior_hour` | INTEGER | 以 `00`–`23` 显示 |
| `behavior_events`, `active_users` | INTEGER | 事件与用户数 |
| `browse_events`, `click_events`, `favorite_events`, `cart_events` | INTEGER | 四类行为事件数 |
| `avg_duration_seconds` | DECIMAL | 平均持续秒数 |

## `ads_category_performance.csv`

粒度：一个商品品类。

| 字段组 | 字段 | 类型 |
|---|---|---|
| 排名/目录 | `category_rank`, `category`, `products` | INTEGER / STRING / INTEGER |
| 行为 | `behavior_events`, `engaged_users`, `browse_users`, `intent_users` | INTEGER |
| 订单 | `total_orders`, `ordering_customers`, `paid_orders`, `paid_customers` | INTEGER |
| 支付金额 | `paid_gmv`, `paid_aov` | DECIMAL |
| 完成 | `completed_orders`, `completed_customers`, `completed_gmv` | INTEGER / INTEGER / DECIMAL |

排名由 SQL 按完成订单样本金额降序稳定生成；Tableau 不重新并列排名。

## `ads_customer_segments.csv`

粒度：一个互斥客户分群。

| 字段 | 类型 | 说明 |
|---|---|---|
| `segment_order` | INTEGER | 1–5 固定排序 |
| `customer_segment` | STRING | `repeat_paid_customer`, `single_paid_customer`, `order_without_payment`, `engaged_noncustomer`, `inactive` |
| `user_count` | INTEGER | 分群用户数 |
| `total_orders`, `paid_orders` | INTEGER | 分群订单数 |
| `paid_gmv` | DECIMAL | 分群支付生命周期金额 |
| `behavior_events` | INTEGER | 分群行为事件数 |
| `user_share` | DECIMAL | 格式化为 Percentage |

## `ads_sequential_funnel.csv`

粒度：一个用户级顺序阶段。

| 字段 | 类型 | 说明 |
|---|---|---|
| `stage_order` | INTEGER | 1–4 |
| `stage_name` | STRING | `browse`, `click_after_browse`, `intent_after_click`, `paid_order_after_intent` |
| `user_count` | INTEGER | 到达阶段的用户数 |
| `previous_stage_conversion` | DECIMAL | 当前/前一阶段 |
| `overall_conversion` | DECIMAL | 当前/首次浏览阶段 |

漏斗是跨商品用户级顺序，不是同商品归因。工具提示必须保留该说明。

## `ads_dataops_health.csv`

粒度：一项质量检查。

| 字段 | 类型 | 说明 |
|---|---|---|
| `check_name` | STRING | 稳定检查键 |
| `check_status` | STRING | `pass`, `warn`, `fail` |
| `observed_value`, `expected_value` | STRING | 实际与预期 |
| `severity` | STRING | `critical` 或 `warning` |
| `details` | STRING | 检查解释 |
| `checked_at` | DATETIME | 检查时间 |

`pass` 与 `warn` 不能只用颜色区分；状态文字必须可见。
