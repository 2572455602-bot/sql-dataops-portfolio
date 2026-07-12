# 指标字典

## 共同口径

所有业务指标只从通过 ODS 校验的 DWD 事实和维度重算。`user_features.csv` 与 `product_features.csv` 是审计快照，不直接提供 KPI。

| 术语 | 定义 |
|---|---|
| 有效订单 | 进入 `dwd_fact_order` 的一个唯一 `order_id` |
| 有效行为 | 进入 `dwd_fact_behavior` 的一个唯一 `behavior_id` |
| 支付生命周期订单 | 状态为已付款、已发货、已收货或已完成 |
| 完成订单 | 状态为已完成 |
| 取消/退款订单 | 状态为已取消或已退款 |
| 行为意向 | 收藏或加购 |
| 隔离行 | 违反项目规则、进入 `ods_quarantine` 且不进入业务事实的记录 |
| 数据模式 | `DEMO` 或 `PORTFOLIO` |
| 来源状态 | `SYNTHETIC_FIXTURE` 或 `UNVERIFIED` |

`PORTFOLIO / UNVERIFIED` 只代表外部样本运行，不代表真实公司数据。

## 核心 KPI

输出：`ads_executive_kpis.csv`，一行代表完整观察窗口。

| 字段 | 公式 | 解释 |
|---|---|---|
| `total_orders` | `COUNT(*)` on order fact | 有效源订单数 |
| `ordering_customers` | `COUNT(DISTINCT user_id)` on order fact | 至少一笔有效订单的用户 |
| `paid_orders` | 支付生命周期订单数 | 不含待付款、取消、退款 |
| `paid_customers` | 支付生命周期的去重用户 | 至少一笔支付生命周期订单 |
| `completed_orders` | 完成订单数 | 当前状态为已完成 |
| `completed_customers` | 完成订单去重用户 | 至少一笔完成订单 |
| `all_order_amount` | 所有有效订单 `actual_payment` 之和 | 包含各状态，只作审计辅助 |
| `paid_gmv` | 支付生命周期订单 `actual_payment` 之和 | 样本内部支付金额字段，不是经审计企业 GMV |
| `completed_gmv` | 完成订单 `actual_payment` 之和 | 页面称“完成订单样本金额”；币种未验证 |
| `paid_aov` | 支付生命周期订单的平均 `actual_payment` | 分母为支付生命周期订单数 |
| `completed_aov` | 完成订单的平均 `actual_payment` | 分母为完成订单数 |
| `completion_rate` | `completed_orders / total_orders` | 当前快照的订单完成占比 |
| `cancellation_refund_rate` | `(已取消 + 已退款) / total_orders` | 当前快照风险状态占比 |
| `repeat_completed_customers` | 完成订单数至少 2 的用户 | 按完成事实计数 |
| `repeat_completed_customer_rate` | `repeat_completed_customers / completed_customers` | 不是订单复购率或长期留存率 |
| `behavior_events` | 行为事实总数 | 浏览、点击、收藏、加购之和 |
| `behavior_users` | 行为事实去重用户 | 至少一次有效行为 |
| `registered_users` | 用户维度行数 | 有效注册用户数 |
| `products/categories` | 商品数 / 去重品类数 | 有效商品目录规模 |
| `quarantined_rows` | quarantine 行数 | 已从业务指标排除 |

金额均使用源字段 `actual_payment`。项目验证 `actual_payment = total_amount - discount`；由于 `unit_price × quantity` 与 `total_amount` 存在大量未解释差异，不使用前者重算金额。

## 每日趋势

输出：`ads_daily_trend.csv`，粒度为一个 `order_date`。

包含每日有效订单、下单用户、数量、所有/支付生命周期/完成金额、折扣、支付生命周期订单、完成订单/用户、取消退款订单、支付生命周期客单价和完成订单平均评分。每日合计订单数与完成金额必须回到 DWD 总计。

日期是源时间戳对应的自然日；项目不推断用户时区，也不把时间趋势解释成因果。

## 订单状态

输出：`ads_order_status.csv`，每个源订单状态一行。

| 字段 | 定义 |
|---|---|
| `order_count` | 该状态有效订单数 |
| `customer_count` | 该状态去重用户数 |
| `order_amount` | 该状态 `actual_payment` 之和 |
| `paid_gmv` | 仅支付生命周期状态保留金额，其他为 0 |
| `order_share` | 该状态订单数 / 全部有效订单数 |

状态是当前快照，不是状态变更历史，不能计算每一步真实处理时长或状态转移概率。

## 小时行为

输出：`ads_hourly_behavior.csv`，粒度为 0–23 的一个小时。

包含行为事件数、行为用户数、浏览/点击/收藏/加购事件数和平均持续秒数。它描述当前样本中的时间分布，不代表真实网站流量规律。

## 品类表现

输出：`ads_category_performance.csv`，粒度为一个商品品类，按完成订单样本金额降序排名。

| 指标组 | 字段 |
|---|---|
| 目录 | 商品数 |
| 行为 | 行为事件、参与用户、浏览用户、意向用户 |
| 订单 | 有效订单、下单用户、支付生命周期订单/用户/金额、平均支付金额 |
| 完成 | 完成订单、完成用户、完成订单样本金额 |

行为与订单可以按用户或品类描述性比较，但当前页面不声称同一行为导致同一商品的购买。

## 客户分群

输出：`ads_customer_segments.csv`。五类互斥且覆盖所有有效注册用户，优先级从上到下：

| 顺序 | 分群 | 规则 |
|---:|---|---|
| 1 | `repeat_paid_customer` | 支付生命周期订单数 ≥ 2 |
| 2 | `single_paid_customer` | 支付生命周期订单数 = 1 |
| 3 | `order_without_payment` | 有订单，但无支付生命周期订单 |
| 4 | `engaged_noncustomer` | 无订单，但有行为 |
| 5 | `inactive` | 无订单且无行为 |

`repeat_paid_customer` 使用支付生命周期订单，而 KPI 的 `repeat_completed_customer_rate` 使用完成订单；两者不能混写。

## 顺序漏斗

输出：`ads_sequential_funnel.csv`，用户级四阶段：

1. 至少一次浏览；
2. 在首次浏览之后至少一次点击；
3. 在上述点击之后至少一次收藏或加购；
4. 在上述意向之后至少一笔支付生命周期订单。

`previous_stage_conversion = 当前阶段用户 / 前一阶段用户`；`overall_conversion = 当前阶段用户 / 浏览用户`。分母为 0 时为 `NULL`。

该漏斗明确是**跨商品的用户级时序**：各阶段不要求同一 `product_id`，也没有会话、广告触点或归因窗口。因此它适合展示 SQL 时序逻辑，不适合作为产品转化率、营销归因或因果结论。

## 质量指标

输出：`ads_dataops_health.csv`，一项检查一行。

- critical：文件非空、层间行数、主外键、金额公式、生命周期、特征对账、KPI/每日/漏斗/分群/ADS 对账；失败阻断发布。
- warning：隔离行、注册前事件、`unit_price × quantity` 差异、`days_since_last_order` 哨兵；公开报告但不自动修复。

`quality.status = pass` 的含义是“没有 critical 失败”，允许存在已披露 warning。

## 当前不能可靠计算

| 分析 | 原因 |
|---|---|
| 真实企业 GMV、收入、利润 | 来源和会计口径未验证，数据疑似合成 |
| 同商品购买归因 | 行为与订单没有可靠会话/归因链，当前漏斗允许跨商品 |
| 地域经营表现 | 省市组合质量不足 |
| 长期留存、LTV、预测模型 | 观察窗口、来源与特征质量不足，且无未来真实标签 |
| 状态转移时长/SLA | 只有当前订单状态快照，没有完整状态事件历史 |
| 因果影响 | 没有实验或可识别的因果设计 |

任何对外数字都应与同一个成功 manifest 的 run ID 一起使用。
