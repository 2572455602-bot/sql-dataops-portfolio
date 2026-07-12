-- DWS daily commerce and order-status summaries.

DROP TABLE IF EXISTS dws_daily_commerce;
CREATE TABLE dws_daily_commerce USING PARQUET COMMENT 'Grain: one order date.' AS
SELECT
    order_date,
    COUNT(*) AS total_orders,
    COUNT(DISTINCT user_id) AS ordering_customers,
    SUM(quantity) AS units,
    ROUND(SUM(actual_payment), 2) AS all_order_amount,
    ROUND(SUM(paid_gmv), 2) AS paid_gmv,
    ROUND(SUM(CASE WHEN is_completed THEN actual_payment ELSE 0 END), 2) AS completed_gmv,
    ROUND(SUM(discount), 2) AS discount_amount,
    SUM(CASE WHEN is_paid_lifecycle THEN 1 ELSE 0 END) AS paid_orders,
    SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS completed_orders,
    COUNT(DISTINCT CASE WHEN is_completed THEN user_id END) AS completed_customers,
    SUM(CASE WHEN status_code IN ('cancelled','refunded') THEN 1 ELSE 0 END) AS cancelled_or_refunded_orders,
    ROUND(AVG(CASE WHEN is_paid_lifecycle THEN actual_payment END), 2) AS paid_aov,
    ROUND(AVG(CASE WHEN is_completed THEN review_score END), 2) AS avg_review_score
FROM dwd_fact_order
GROUP BY order_date;

DROP TABLE IF EXISTS dws_order_status_summary;
CREATE TABLE dws_order_status_summary USING PARQUET COMMENT 'Grain: one order status.' AS
WITH status_metrics AS (
    SELECT
        source_order_status,
        status_code,
        status_order,
        COUNT(*) AS order_count,
        COUNT(DISTINCT user_id) AS customer_count,
        ROUND(SUM(actual_payment), 2) AS order_amount,
        ROUND(SUM(paid_gmv), 2) AS paid_gmv
    FROM dwd_fact_order
    GROUP BY source_order_status, status_code, status_order
), totals AS (
    SELECT SUM(order_count) AS total_orders FROM status_metrics
)
SELECT
    metrics.*,
    ROUND(CAST(metrics.order_count AS DOUBLE) / NULLIF(totals.total_orders, 0), 4) AS order_share
FROM status_metrics metrics
CROSS JOIN totals;

DROP TABLE IF EXISTS dws_hourly_behavior;
CREATE TABLE dws_hourly_behavior USING PARQUET COMMENT 'Grain: one hour of day across all behavior events.' AS
SELECT
    behavior_hour,
    COUNT(*) AS behavior_events,
    COUNT(DISTINCT user_id) AS active_users,
    SUM(CASE WHEN behavior_code = 'browse' THEN 1 ELSE 0 END) AS browse_events,
    SUM(CASE WHEN behavior_code = 'click' THEN 1 ELSE 0 END) AS click_events,
    SUM(CASE WHEN behavior_code = 'favorite' THEN 1 ELSE 0 END) AS favorite_events,
    SUM(CASE WHEN behavior_code = 'cart' THEN 1 ELSE 0 END) AS cart_events,
    ROUND(AVG(duration_seconds), 2) AS avg_duration_seconds
FROM dwd_fact_behavior
GROUP BY behavior_hour;
