-- DWD conformed dimensions and facts.

DROP TABLE IF EXISTS dwd_dim_user;
CREATE TABLE dwd_dim_user USING PARQUET COMMENT 'Grain: one registered user.' AS
SELECT
    user_id,
    age,
    CASE
        WHEN age < 25 THEN '18-24'
        WHEN age < 35 THEN '25-34'
        WHEN age < 45 THEN '35-44'
        WHEN age < 55 THEN '45-54'
        ELSE '55+'
    END AS age_band,
    gender,
    province,
    city,
    TO_DATE(registration_ts) AS registration_date,
    member_level,
    account_balance,
    credit_score
FROM ods_users_valid;

DROP TABLE IF EXISTS dwd_dim_product;
CREATE TABLE dwd_dim_product USING PARQUET COMMENT 'Grain: one product.' AS
SELECT product_id, product_name, category, brand, price, sales_count
FROM ods_products_valid;

DROP TABLE IF EXISTS dwd_dim_order_status;
CREATE TABLE dwd_dim_order_status USING PARQUET COMMENT 'Grain: one supported source order status.' AS
SELECT * FROM VALUES
    ('待付款','pending_payment',1,FALSE,FALSE),
    ('已付款','paid',2,TRUE,FALSE),
    ('已发货','shipped',3,TRUE,FALSE),
    ('已收货','received',4,TRUE,FALSE),
    ('已完成','completed',5,TRUE,TRUE),
    ('已取消','cancelled',6,FALSE,FALSE),
    ('已退款','refunded',7,FALSE,FALSE)
AS status(source_status, status_code, status_order, is_paid_lifecycle, is_completed);

DROP TABLE IF EXISTS dwd_dim_behavior;
CREATE TABLE dwd_dim_behavior USING PARQUET COMMENT 'Grain: one supported behavior type.' AS
SELECT * FROM VALUES
    ('浏览','browse','engagement',1),
    ('点击','click','engagement',2),
    ('收藏','favorite','intent',3),
    ('加购','cart','intent',4)
AS behavior(source_behavior, behavior_code, behavior_group, stage_order);

DROP TABLE IF EXISTS dwd_fact_order;
CREATE TABLE dwd_fact_order USING PARQUET COMMENT 'Grain: one valid source order.' AS
SELECT
    orders.order_id,
    orders.user_id,
    orders.product_id,
    orders.quantity,
    orders.order_ts,
    TO_DATE(orders.order_ts) AS order_date,
    orders.order_status AS source_order_status,
    status.status_code,
    status.status_order,
    status.is_paid_lifecycle,
    status.is_completed,
    orders.payment_method,
    orders.unit_price,
    orders.total_amount,
    orders.discount,
    orders.actual_payment,
    CASE WHEN status.is_paid_lifecycle THEN orders.actual_payment ELSE CAST(0 AS DECIMAL(18,2)) END AS paid_gmv,
    orders.delivery_ts,
    orders.receive_ts,
    orders.review_score,
    orders.source_file,
    orders.ingested_at
FROM ods_orders_valid orders
INNER JOIN dwd_dim_order_status status
    ON orders.order_status = status.source_status;

DROP TABLE IF EXISTS dwd_fact_behavior;
CREATE TABLE dwd_fact_behavior USING PARQUET COMMENT 'Grain: one valid source behavior event.' AS
SELECT
    behavior.behavior_id,
    behavior.user_id,
    behavior.product_id,
    behavior.behavior_type AS source_behavior_type,
    dimension.behavior_code,
    dimension.behavior_group,
    dimension.stage_order,
    behavior.behavior_ts,
    TO_DATE(behavior.behavior_ts) AS behavior_date,
    HOUR(behavior.behavior_ts) AS behavior_hour,
    behavior.duration_seconds,
    behavior.source_file,
    behavior.ingested_at
FROM ods_user_behaviors_valid behavior
INNER JOIN dwd_dim_behavior dimension
    ON behavior.behavior_type = dimension.source_behavior;

DROP TABLE IF EXISTS dwd_feature_snapshot_user;
CREATE TABLE dwd_feature_snapshot_user USING PARQUET COMMENT 'Grain: one source-provided user feature snapshot; audit-only.' AS
SELECT * EXCEPT (source_file, ingested_at)
FROM ods_user_features_valid;

DROP TABLE IF EXISTS dwd_feature_snapshot_product;
CREATE TABLE dwd_feature_snapshot_product USING PARQUET COMMENT 'Grain: one source-provided product feature snapshot; audit-only.' AS
SELECT * EXCEPT (source_file, ingested_at)
FROM ods_product_features_valid;

DROP TABLE IF EXISTS dwd_dim_date;
CREATE TABLE dwd_dim_date USING PARQUET COMMENT 'Grain: one date present in an order or behavior fact.' AS
WITH represented_dates AS (
    SELECT order_date AS calendar_date FROM dwd_fact_order
    UNION
    SELECT behavior_date AS calendar_date FROM dwd_fact_behavior
)
SELECT
    calendar_date,
    YEAR(calendar_date) AS calendar_year,
    QUARTER(calendar_date) AS calendar_quarter,
    MONTH(calendar_date) AS calendar_month,
    DAY(calendar_date) AS day_of_month,
    WEEKOFYEAR(calendar_date) AS week_of_year,
    CAST(PMOD(DAYOFWEEK(calendar_date) + 5, 7) + 1 AS INT) AS day_of_week,
    CASE WHEN CAST(PMOD(DAYOFWEEK(calendar_date) + 5, 7) + 1 AS INT) IN (6,7)
         THEN TRUE ELSE FALSE END AS is_weekend
FROM represented_dates;
