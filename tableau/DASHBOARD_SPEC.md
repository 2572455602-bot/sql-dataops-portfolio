# Tableau Dashboard 规格

## 定位

单页招聘展示 Dashboard，目标是用 30 秒说明业务结果、用 2 分钟下钻分析、用质量区证明数字可追溯。数据只来自已发布 ADS。

## 顶栏

必须显示：

- 标题：`E-commerce SQL + DataOps Portfolio`
- `data_mode` 与 `source_status`
- 订单/行为日期范围
- 当前 run ID（可从 manifest 手工同步到文本或参数）

模式文案：

- `DEMO · SYNTHETIC FIXTURE`
- `PORTFOLIO · SOURCE UNVERIFIED`

来源状态必须用文字显示，不能只靠颜色。

## 桌面布局

建议 `1366 × 900`，Tiled 容器：

| 区域 | 工作表 | 视觉 | 默认指标 |
|---|---|---|---|
| 顶部 | Run context | 文本/状态胶囊 | 模式、来源、日期、run ID |
| 第一行 | Executive KPI | 4 张 KPI 卡 | 有效订单、完成订单样本金额、完成购买用户、订单完成率 |
| 第二行 | Daily trend | 双轴线/面积图 | 每日有效订单、完成订单样本金额 |
| 第三行左 | Order status | 水平条形图 | 各状态订单数与占比 |
| 第三行右 | Category performance | Top 10 水平条形图 | 完成订单样本金额/订单/用户 |
| 第四行左 | Hourly behavior | 多系列折线或热力图 | 浏览、点击、收藏、加购 |
| 第四行右 | Customer segments | 水平条形图 | 用户数与占比 |
| 底部 | DataOps Health | 状态卡 + 明细表 | pass/warn/fail、observed/expected |

顺序漏斗放在技术下钻页或折叠区，不占首页主视觉。

## 工作表规则

### KPI

- 每张卡只读取 `ads_executive_kpis.csv` 单行字段。
- `completed_gmv` 显示名称必须是“完成订单样本金额”，不加货币符号，不写企业 GMV/收入。
- 数量使用千分位；金额保留 0–2 位；比率用 Percentage。

### Daily trend

- `order_date` 连续日期，缺失日期不自行补零。
- 双轴时保证单位清楚，避免把订单数与金额共用同一无标签轴。
- 工具提示显示日期、有效订单、完成订单、完成用户、完成金额。

### Order status

- 严格按 `status_order` 排序。
- 标签显示 `source_order_status`；工具提示补 `customer_count`, `order_amount`, `order_share`。
- 这是当前状态快照，不展示为完整状态流转。

### Category performance

- 过滤 `category_rank <= 10`，按 rank 升序。
- 默认展示完成订单样本金额；工具提示补完成订单/用户、行为用户和支付生命周期数据。
- 不把行为与订单相关性写成归因或因果。

### Hourly behavior

- `behavior_hour` 按 00–23 排序。
- 四类行为使用一致颜色映射；工具提示显示事件数、用户数、平均持续时间。
- 不推断真实用户时区或网站运营规律。

### Customer segments

- 按 `segment_order` 排序，不按用户数重排语义顺序。
- 五类占比总和约为 100%。
- 重复支付客户分群与 KPI 的重复完成购买用户率口径不同，标题不能混用。

### Sequential funnel

- `stage_order` 1–4，坐标从 0 开始，人数必须单调不增。
- 显示 previous 与 overall conversion。
- 页面注明：阶段按用户时间连接、允许跨商品、不代表购买归因。

### DataOps Health

- 顶部显示总检查、失败数、warning 数和 quarantine 数。
- 明细显示 `check_name`, `check_status`, `severity`, `observed_value`, `expected_value`, `details`。
- `FAIL` 红色、`WARN` 琥珀色、`PASS` 绿色，同时保留文字和图标。

## 交互

- 品类选择可以过滤品类图自身，不联动 KPI，避免改变全窗口口径。
- 日期筛选只用于趋势探索；若 KPI 未同步过滤，应明确标注 KPI 为全窗口。
- 不跨不同 ADS 物理 join；需要跨图协调时用 Dashboard Action，不修改源粒度。

## 移动端

Phone layout 单列顺序：Run context → 4 KPI → trend → status → category → segments → health。漏斗与小时图可折叠或放第二屏。

## 来源与风险说明

底部固定文本：

> Portfolio sample; source unverified and apparently synthetic. Aggregates demonstrate SQL/DataOps implementation, not real-company performance.

公开版不得出现原始 CSV 明细、个人路径、账号或凭证。
