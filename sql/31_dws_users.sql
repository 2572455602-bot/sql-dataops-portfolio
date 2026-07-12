-- DWS customer summaries, segments, and user-level sequential funnel.

DROP TABLE IF EXISTS dws_customer_summary;
CREATE TABLE dws_customer_summary USING PARQUET COMMENT 'Grain: one registered user across the observation window.' AS
WITH order_metrics AS (
    SELECT
        user_id,
        COUNT(*) AS total_orders,
        SUM(CASE WHEN is_paid_lifecycle THEN 1 ELSE 0 END) AS paid_orders,
        SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS completed_orders,
        ROUND(SUM(actual_payment), 2) AS all_order_amount,
        ROUND(SUM(paid_gmv), 2) AS paid_gmv,
        MIN(order_ts) AS first_order_ts,
        MAX(order_ts) AS last_order_ts
    FROM dwd_fact_order
    GROUP BY user_id
), behavior_metrics AS (
    SELECT
        user_id,
        COUNT(*) AS behavior_events,
        SUM(CASE WHEN behavior_code = 'browse' THEN 1 ELSE 0 END) AS browse_events,
        SUM(CASE WHEN behavior_code = 'click' THEN 1 ELSE 0 END) AS click_events,
        SUM(CASE WHEN behavior_code = 'favorite' THEN 1 ELSE 0 END) AS favorite_events,
        SUM(CASE WHEN behavior_code = 'cart' THEN 1 ELSE 0 END) AS cart_events,
        MIN(behavior_ts) AS first_behavior_ts,
        MAX(behavior_ts) AS last_behavior_ts
    FROM dwd_fact_behavior
    GROUP BY user_id
)
SELECT
    users.user_id,
    users.age_band,
    users.gender,
    users.province,
    users.city,
    users.member_level,
    COALESCE(orders.total_orders, 0) AS total_orders,
    COALESCE(orders.paid_orders, 0) AS paid_orders,
    COALESCE(orders.completed_orders, 0) AS completed_orders,
    COALESCE(orders.all_order_amount, 0) AS all_order_amount,
    COALESCE(orders.paid_gmv, 0) AS paid_gmv,
    orders.first_order_ts,
    orders.last_order_ts,
    COALESCE(behaviors.behavior_events, 0) AS behavior_events,
    COALESCE(behaviors.browse_events, 0) AS browse_events,
    COALESCE(behaviors.click_events, 0) AS click_events,
    COALESCE(behaviors.favorite_events, 0) AS favorite_events,
    COALESCE(behaviors.cart_events, 0) AS cart_events,
    behaviors.first_behavior_ts,
    behaviors.last_behavior_ts,
    CASE
        WHEN COALESCE(orders.paid_orders, 0) >= 2 THEN 'repeat_paid_customer'
        WHEN COALESCE(orders.paid_orders, 0) = 1 THEN 'single_paid_customer'
        WHEN COALESCE(orders.total_orders, 0) > 0 THEN 'order_without_payment'
        WHEN COALESCE(behaviors.behavior_events, 0) > 0 THEN 'engaged_noncustomer'
        ELSE 'inactive'
    END AS customer_segment
FROM dwd_dim_user users
LEFT JOIN order_metrics orders ON users.user_id = orders.user_id
LEFT JOIN behavior_metrics behaviors ON users.user_id = behaviors.user_id;

DROP TABLE IF EXISTS dws_sequential_funnel;
CREATE TABLE dws_sequential_funnel USING PARQUET COMMENT 'Grain: one user-level sequential funnel stage; stages need not reference the same product.' AS
WITH first_browse AS (
    SELECT user_id, MIN(behavior_ts) AS first_browse_ts
    FROM dwd_fact_behavior
    WHERE behavior_code = 'browse'
    GROUP BY user_id
), first_click_after_browse AS (
    SELECT events.user_id, MIN(events.behavior_ts) AS first_click_after_browse_ts
    FROM dwd_fact_behavior events
    INNER JOIN first_browse browse
        ON events.user_id = browse.user_id
       AND events.behavior_ts >= browse.first_browse_ts
    WHERE events.behavior_code = 'click'
    GROUP BY events.user_id
), first_intent_after_click AS (
    SELECT events.user_id, MIN(events.behavior_ts) AS first_intent_after_click_ts
    FROM dwd_fact_behavior events
    INNER JOIN first_click_after_browse click
        ON events.user_id = click.user_id
       AND events.behavior_ts >= click.first_click_after_browse_ts
    WHERE events.behavior_code IN ('favorite','cart')
    GROUP BY events.user_id
), first_paid_order_after_intent AS (
    SELECT orders.user_id, MIN(orders.order_ts) AS first_paid_order_after_intent_ts
    FROM dwd_fact_order orders
    INNER JOIN first_intent_after_click intent
        ON orders.user_id = intent.user_id
       AND orders.order_ts >= intent.first_intent_after_click_ts
    WHERE orders.is_paid_lifecycle
    GROUP BY orders.user_id
), counts AS (
    SELECT
        (SELECT COUNT(*) FROM first_browse) AS browse_users,
        (SELECT COUNT(*) FROM first_click_after_browse) AS click_after_browse_users,
        (SELECT COUNT(*) FROM first_intent_after_click) AS intent_after_click_users,
        (SELECT COUNT(*) FROM first_paid_order_after_intent) AS paid_after_intent_users
), stages AS (
    SELECT 1 AS stage_order, 'browse' AS stage_name, browse_users AS user_count FROM counts
    UNION ALL SELECT 2, 'click_after_browse', click_after_browse_users FROM counts
    UNION ALL SELECT 3, 'intent_after_click', intent_after_click_users FROM counts
    UNION ALL SELECT 4, 'paid_order_after_intent', paid_after_intent_users FROM counts
), ordered AS (
    SELECT
        stage_order,
        stage_name,
        user_count,
        LAG(user_count) OVER (ORDER BY stage_order) AS previous_user_count,
        MAX(CASE WHEN stage_order = 1 THEN user_count END) OVER () AS first_user_count
    FROM stages
)
SELECT
    stage_order,
    stage_name,
    user_count,
    ROUND(CASE WHEN stage_order = 1 THEN 1.0
               ELSE CAST(user_count AS DOUBLE) / NULLIF(previous_user_count, 0) END, 4)
        AS previous_stage_conversion,
    ROUND(CAST(user_count AS DOUBLE) / NULLIF(first_user_count, 0), 4) AS overall_conversion
FROM ordered;

DROP TABLE IF EXISTS dws_customer_segments;
CREATE TABLE dws_customer_segments USING PARQUET COMMENT 'Grain: one mutually exclusive customer segment.' AS
WITH segment_metrics AS (
    SELECT
        CASE customer_segment
            WHEN 'repeat_paid_customer' THEN 1
            WHEN 'single_paid_customer' THEN 2
            WHEN 'order_without_payment' THEN 3
            WHEN 'engaged_noncustomer' THEN 4
            ELSE 5
        END AS segment_order,
        customer_segment,
        COUNT(*) AS user_count,
        SUM(total_orders) AS total_orders,
        SUM(paid_orders) AS paid_orders,
        ROUND(SUM(paid_gmv), 2) AS paid_gmv,
        SUM(behavior_events) AS behavior_events
    FROM dws_customer_summary
    GROUP BY customer_segment
), totals AS (
    SELECT SUM(user_count) AS total_users FROM segment_metrics
)
SELECT
    metrics.*,
    ROUND(CAST(metrics.user_count AS DOUBLE) / NULLIF(totals.total_users, 0), 4) AS user_share
FROM segment_metrics metrics
CROSS JOIN totals;
