-- DWS category performance.
-- Grain: one product category across orders and behaviors.

DROP TABLE IF EXISTS dws_category_performance;
CREATE TABLE dws_category_performance USING PARQUET COMMENT 'Grain: one product category.' AS
WITH category_dimension AS (
    SELECT category, COUNT(*) AS products
    FROM dwd_dim_product
    GROUP BY category
), behavior_metrics AS (
    SELECT
        product.category,
        COUNT(*) AS behavior_events,
        COUNT(DISTINCT behavior.user_id) AS engaged_users,
        COUNT(DISTINCT CASE WHEN behavior.behavior_code = 'browse' THEN behavior.user_id END) AS browse_users,
        COUNT(DISTINCT CASE WHEN behavior.behavior_code IN ('favorite','cart') THEN behavior.user_id END) AS intent_users
    FROM dwd_fact_behavior behavior
    INNER JOIN dwd_dim_product product ON behavior.product_id = product.product_id
    GROUP BY product.category
), order_metrics AS (
    SELECT
        product.category,
        COUNT(*) AS total_orders,
        COUNT(DISTINCT orders.user_id) AS ordering_customers,
        SUM(CASE WHEN orders.is_paid_lifecycle THEN 1 ELSE 0 END) AS paid_orders,
        COUNT(DISTINCT CASE WHEN orders.is_paid_lifecycle THEN orders.user_id END) AS paid_customers,
        ROUND(SUM(orders.paid_gmv), 2) AS paid_gmv,
        ROUND(AVG(CASE WHEN orders.is_paid_lifecycle THEN orders.actual_payment END), 2) AS paid_aov
    FROM dwd_fact_order orders
    INNER JOIN dwd_dim_product product ON orders.product_id = product.product_id
    GROUP BY product.category
)
SELECT
    dimension.category,
    dimension.products,
    COALESCE(behavior.behavior_events, 0) AS behavior_events,
    COALESCE(behavior.engaged_users, 0) AS engaged_users,
    COALESCE(behavior.browse_users, 0) AS browse_users,
    COALESCE(behavior.intent_users, 0) AS intent_users,
    COALESCE(orders.total_orders, 0) AS total_orders,
    COALESCE(orders.ordering_customers, 0) AS ordering_customers,
    COALESCE(orders.paid_orders, 0) AS paid_orders,
    COALESCE(orders.paid_customers, 0) AS paid_customers,
    COALESCE(orders.paid_gmv, 0) AS paid_gmv,
    orders.paid_aov
FROM category_dimension dimension
LEFT JOIN behavior_metrics behavior ON dimension.category = behavior.category
LEFT JOIN order_metrics orders ON dimension.category = orders.category;
