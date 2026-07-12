-- ADS recruiter/dashboard serving layer. All tables contain aggregates only.

DROP TABLE IF EXISTS ads_executive_kpis;
CREATE TABLE ads_executive_kpis USING PARQUET COMMENT 'Grain: one KPI snapshot for the complete observation window.' AS
WITH orders AS (
    SELECT
        MIN(order_date) AS min_order_date,
        MAX(order_date) AS max_order_date,
        COUNT(*) AS total_orders,
        COUNT(DISTINCT user_id) AS ordering_customers,
        SUM(CASE WHEN is_paid_lifecycle THEN 1 ELSE 0 END) AS paid_orders,
        COUNT(DISTINCT CASE WHEN is_paid_lifecycle THEN user_id END) AS paid_customers,
        SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS completed_orders,
        COUNT(DISTINCT CASE WHEN is_completed THEN user_id END) AS completed_customers,
        ROUND(SUM(actual_payment), 2) AS all_order_amount,
        ROUND(SUM(paid_gmv), 2) AS paid_gmv,
        ROUND(SUM(CASE WHEN is_completed THEN actual_payment ELSE 0 END), 2) AS completed_gmv,
        ROUND(AVG(CASE WHEN is_paid_lifecycle THEN actual_payment END), 2) AS paid_aov,
        ROUND(AVG(CASE WHEN is_completed THEN actual_payment END), 2) AS completed_aov,
        SUM(CASE WHEN status_code IN ('cancelled','refunded') THEN 1 ELSE 0 END) AS cancelled_or_refunded_orders
    FROM dwd_fact_order
), behaviors AS (
    SELECT
        MIN(behavior_date) AS min_behavior_date,
        MAX(behavior_date) AS max_behavior_date,
        COUNT(*) AS behavior_events,
        COUNT(DISTINCT user_id) AS behavior_users
    FROM dwd_fact_behavior
), population AS (
    SELECT COUNT(*) AS registered_users FROM dwd_dim_user
), catalog AS (
    SELECT COUNT(*) AS products, COUNT(DISTINCT category) AS categories FROM dwd_dim_product
), repeat_customers AS (
    SELECT COUNT(*) AS repeat_completed_customers
    FROM (
        SELECT user_id
        FROM dwd_fact_order
        WHERE is_completed
        GROUP BY user_id
        HAVING COUNT(*) >= 2
    ) repeated
), quarantine AS (
    SELECT COUNT(*) AS quarantined_rows FROM ods_quarantine
)
SELECT
    orders.min_order_date,
    orders.max_order_date,
    behaviors.min_behavior_date,
    behaviors.max_behavior_date,
    orders.total_orders,
    orders.ordering_customers,
    orders.paid_orders,
    orders.paid_customers,
    orders.completed_orders,
    orders.completed_customers,
    orders.all_order_amount,
    orders.paid_gmv,
    orders.completed_gmv,
    orders.paid_aov,
    orders.completed_aov,
    orders.cancelled_or_refunded_orders,
    ROUND(CAST(orders.completed_orders AS DOUBLE) / NULLIF(orders.total_orders, 0), 4) AS completion_rate,
    ROUND(CAST(orders.cancelled_or_refunded_orders AS DOUBLE) / NULLIF(orders.total_orders, 0), 4) AS cancellation_refund_rate,
    repeat.repeat_completed_customers,
    ROUND(CAST(repeat.repeat_completed_customers AS DOUBLE) / NULLIF(orders.completed_customers, 0), 4) AS repeat_completed_customer_rate,
    behaviors.behavior_events,
    behaviors.behavior_users,
    population.registered_users,
    catalog.products,
    catalog.categories,
    quarantine.quarantined_rows
FROM orders
CROSS JOIN behaviors
CROSS JOIN population
CROSS JOIN catalog
CROSS JOIN repeat_customers repeat
CROSS JOIN quarantine;

DROP TABLE IF EXISTS ads_daily_trend;
CREATE TABLE ads_daily_trend USING PARQUET COMMENT 'Grain: one order date.' AS
SELECT * FROM dws_daily_commerce ORDER BY order_date;

DROP TABLE IF EXISTS ads_sequential_funnel;
CREATE TABLE ads_sequential_funnel USING PARQUET COMMENT 'Grain: one user-level cross-product sequential stage.' AS
SELECT * FROM dws_sequential_funnel ORDER BY stage_order;

DROP TABLE IF EXISTS ads_category_performance;
CREATE TABLE ads_category_performance USING PARQUET COMMENT 'Grain: one category ranked by completed business value.' AS
WITH completed AS (
    SELECT product.category, COUNT(*) AS completed_orders,
           COUNT(DISTINCT orders.user_id) AS completed_customers,
           ROUND(SUM(orders.actual_payment), 2) AS completed_gmv
    FROM dwd_fact_order orders
    INNER JOIN dwd_dim_product product ON orders.product_id = product.product_id
    WHERE orders.is_completed
    GROUP BY product.category
), ranked AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY COALESCE(completed.completed_gmv,0) DESC, performance.category) AS category_rank,
        performance.*,
        COALESCE(completed.completed_orders,0) AS completed_orders,
        COALESCE(completed.completed_customers,0) AS completed_customers,
        COALESCE(completed.completed_gmv,0) AS completed_gmv
    FROM dws_category_performance performance
    LEFT JOIN completed ON performance.category = completed.category
)
SELECT * FROM ranked ORDER BY category_rank;

DROP TABLE IF EXISTS ads_hourly_behavior;
CREATE TABLE ads_hourly_behavior USING PARQUET COMMENT 'Grain: one behavior hour.' AS
SELECT * FROM dws_hourly_behavior ORDER BY behavior_hour;

DROP TABLE IF EXISTS ads_customer_segments;
CREATE TABLE ads_customer_segments USING PARQUET COMMENT 'Grain: one customer segment.' AS
SELECT * FROM dws_customer_segments ORDER BY segment_order;

DROP TABLE IF EXISTS ads_order_status;
CREATE TABLE ads_order_status USING PARQUET COMMENT 'Grain: one order status.' AS
SELECT * FROM dws_order_status_summary ORDER BY status_order;
