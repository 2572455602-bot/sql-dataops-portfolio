# 数据集声明

## 结论

当前外部六表数据的来源、生成方式、许可和公司归属均无法从随附文件中核验。数据结构与分布呈现明显的合成样本特征，因此 manifest 固定记录：

```text
data_mode = PORTFOLIO
source_status = UNVERIFIED
```

这只说明“外部样本已进入作品流水线”，**不代表真实公司数据，更不代表淘宝、阿里或任何特定企业的数据**。在获得可验证的原始发布页、许可条款、版本说明与校验值之前，不得改变这一表述。

## 六个输入文件

目录必须包含以下带表头 UTF-8 CSV；文件名、字段顺序和字段数量都属于阻断式契约。

### `users.csv`

```text
user_id,age,gender,province,city,registration_date,member_level,account_balance,credit_score
```

### `products.csv`

```text
product_id,product_name,category,brand,price,sales_count
```

### `orders.csv`

```text
order_id,user_id,product_id,quantity,order_date,order_status,payment_method,unit_price,total_amount,discount,actual_payment,delivery_date,receive_date,review_score,review_content
```

允许的订单状态为：`待付款`、`已付款`、`已发货`、`已收货`、`已完成`、`已取消`、`已退款`。

### `user_behaviors.csv`

```text
behavior_id,user_id,product_id,behavior_type,behavior_time,duration_seconds
```

允许的行为类型为：`浏览`、`点击`、`收藏`、`加购`。购买事实来自 `orders.csv`，不是行为枚举。

### `user_features.csv`

```text
user_id,total_spent,order_count,completed_orders,avg_order_amount,browse_count,click_count,favorite_count,cart_count,days_since_last_order,order_frequency,repurchase_indicator,purchase_intent,consumption_level,member_level_score
```

### `product_features.csv`

```text
product_id,total_revenue,total_sales,completed_count,cancel_count,加购_count,收藏_count,浏览_count,点击_count,conversion_rate,avg_review_score,popularity_score
```

两张 features 表是来源提供的派生快照，只用于与订单/行为事实的独立聚合结果对账。业务 KPI 不从这些预计算字段直接读取。

## 当前只读审计发现

- 六表合计 59,000 行；业务主键唯一，订单与行为的用户/商品外键完整。
- 474 条订单和 266 条行为早于用户注册时间，共 740 行，已进入 quarantine 并从业务指标排除。
- 大量记录存在 `unit_price × quantity != total_amount`；项目将其公开为 warning，不自行猜测定价规则。
- `actual_payment = total_amount - discount` 可对账，是当前金额指标采用的来源公式。
- 源文件没有可验证的币种字段；所有对外金额指标统一称为“样本金额”，不加货币符号。
- `days_since_last_order` 大量使用 `999` 哨兵值，因此不用于业务指标或建模。
- 省、市组合的可靠性不足，当前不提供地域经营分析。
- 特征快照能与当前源事实聚合对账，但这不能证明数据来自真实业务系统。

## 使用与分发

原始 CSV 必须留在仓库外。运行时只传绝对目录：

```bash
make full DATA_DIR=/absolute/path/dataset
```

禁止把以下内容提交到 Git、打入 ZIP、放入 Pages 或上传 Tableau Public：

- 六个原始 CSV 或它们的明细抽样；
- 账号、密码、Cookie、Token、下载会话或 `.env`；
- 含个人绝对路径的日志；
- 未核验来源却带有公司名称的描述。

可以公开的是经过检查的小型 ADS 汇总、manifest、质量结果和项目代码；即使如此，也必须保留 `UNVERIFIED` 声明。

## 何时可以更新来源状态

至少需要同时具备：可访问的原始发布页面、发布主体、许可/使用条款、数据版本、下载日期、官方校验值或可复核指纹，以及字段说明。完成这些核验只会更新“来源说明”；是否适合作为真实业务结论，还需要单独的数据质量与语义评估。
