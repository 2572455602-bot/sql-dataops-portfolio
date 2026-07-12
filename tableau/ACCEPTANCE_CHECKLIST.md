# Tableau 验收清单

## 运行与来源

- [ ] Dashboard 使用 `bi_exports/current/` 同一成功 run 的 8 个 ADS CSV。
- [ ] 顶栏显示 run ID、日期范围、`data_mode` 与 `source_status`。
- [ ] 外部样本显示 `PORTFOLIO · SOURCE UNVERIFIED`，DEMO 显示 `DEMO · SYNTHETIC FIXTURE`。
- [ ] 页面没有真实公司、生产数据或经审计财务结果的暗示。
- [ ] manifest 的 `quality.failed_checks = 0`；warning 数与 health CSV 一致且可见。

## KPI 对账

- [ ] 有效订单 = `ads_executive_kpis.total_orders`。
- [ ] 完成订单样本金额 = `completed_gmv`，不带货币符号，显示名不是企业 GMV/收入。
- [ ] 完成购买用户 = `completed_customers`。
- [ ] 订单完成率 = `completion_rate`，格式为 Percentage。
- [ ] 所有数量、金额和比例都与 executive KPI 单行一致，无 Tableau 二次聚合放大。

## 图表对账

- [ ] 每日趋势的 `total_orders` 合计回到 KPI，有清楚的数量/金额轴单位。
- [ ] 订单状态按 `status_order` 排序，`order_count` 合计回到 KPI。
- [ ] 品类使用 SQL 提供的 `category_rank`，Top 10 不在 Tableau 重新并列排名。
- [ ] 小时按 00–23 排序，四类行为字段正确。
- [ ] 五个客户分群按 `segment_order` 排序，人数回到 `registered_users`，占比约为 100%。
- [ ] 若展示漏斗，四阶段按 `stage_order` 排序、人数单调不增，并注明跨商品用户级路径。

## DataOps Health

- [ ] 检查条数与 manifest `quality.total_checks` 一致。
- [ ] pass/warn/fail 使用文字或图标，不只依赖颜色。
- [ ] 每条检查可看到 observed、expected、severity 与 details。
- [ ] quarantine 数与 executive KPI/manifest 一致。
- [ ] warning 没有被筛掉或伪装成 pass。

## 视觉与可用性

- [ ] 桌面版在 1366 × 900 下无需横向滚动。
- [ ] Phone layout 单列可读，KPI、来源状态和质量状态优先出现。
- [ ] 字体、颜色和数字格式一致；金额、数量、比例单位明确。
- [ ] 工具提示简短，不出现内部路径或原始明细。
- [ ] 来源未验证声明在页面底部或顶栏持续可见。

## 安全与发布

- [ ] Tableau 只包含 ADS 汇总，没有六个原始 CSV、DWD 明细或明细抽样。
- [ ] 工作簿不含个人绝对路径、账号、Token、Cookie、邮箱或本地环境信息。
- [ ] Tableau Public 发布前已理解工作簿及其数据将公开。
- [ ] `.twb/.twbx` 和截图来自真实 Tableau 运行并完成本清单，不是手工伪造占位文件。
- [ ] 工作簿、截图、README 数字和视频引用同一个 run ID。

验收未完成时，只能把 Tableau 文件标为“制作中/未验证”，不能作为已交付证据。
