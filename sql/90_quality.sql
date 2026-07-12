-- Blocking and warning quality gates.
-- Grain: one named check for the current run.

DROP TABLE IF EXISTS ops_data_quality_results;
CREATE TABLE ops_data_quality_results USING PARQUET COMMENT 'Grain: one DataOps quality check.' AS
WITH raw_counts AS (
    SELECT
        (SELECT COUNT(*) FROM raw_users_contract) AS raw_users,
        (SELECT COUNT(*) FROM raw_products_contract) AS raw_products,
        (SELECT COUNT(*) FROM raw_orders_contract) AS raw_orders,
        (SELECT COUNT(*) FROM raw_user_behaviors_contract) AS raw_behaviors,
        (SELECT COUNT(*) FROM raw_user_features_contract) AS raw_user_features,
        (SELECT COUNT(*) FROM raw_product_features_contract) AS raw_product_features
), valid_counts AS (
    SELECT
        (SELECT COUNT(*) FROM ods_users_valid) AS valid_users,
        (SELECT COUNT(*) FROM ods_products_valid) AS valid_products,
        (SELECT COUNT(*) FROM ods_orders_valid) AS valid_orders,
        (SELECT COUNT(*) FROM ods_user_behaviors_valid) AS valid_behaviors,
        (SELECT COUNT(*) FROM ods_user_features_valid) AS valid_user_features,
        (SELECT COUNT(*) FROM ods_product_features_valid) AS valid_product_features,
        (SELECT COUNT(*) FROM ods_quarantine WHERE source_table = 'users') AS quarantine_users,
        (SELECT COUNT(*) FROM ods_quarantine WHERE source_table = 'products') AS quarantine_products,
        (SELECT COUNT(*) FROM ods_quarantine WHERE source_table = 'orders') AS quarantine_orders,
        (SELECT COUNT(*) FROM ods_quarantine WHERE source_table = 'user_behaviors') AS quarantine_behaviors,
        (SELECT COUNT(*) FROM ods_quarantine WHERE source_table = 'user_features') AS quarantine_user_features,
        (SELECT COUNT(*) FROM ods_quarantine WHERE source_table = 'product_features') AS quarantine_product_features,
        (SELECT COUNT(*) FROM ods_quarantine) AS quarantine_total,
        (SELECT COUNT(*) FROM ods_quarantine WHERE rejection_reasons LIKE '%event_before_registration%') AS pre_registration_quarantine,
        (SELECT COUNT(*)
         FROM ods_quarantine
         WHERE TRIM(COALESCE(rejection_reasons,'')) <> 'event_before_registration') AS non_temporal_quarantine
), duplicate_stats AS (
    SELECT
        (SELECT COUNT(*) - COUNT(DISTINCT user_id) FROM ods_users_valid)
      + (SELECT COUNT(*) - COUNT(DISTINCT product_id) FROM ods_products_valid)
      + (SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM ods_orders_valid)
      + (SELECT COUNT(*) - COUNT(DISTINCT behavior_id) FROM ods_user_behaviors_valid)
      + (SELECT COUNT(*) - COUNT(DISTINCT user_id) FROM ods_user_features_valid)
      + (SELECT COUNT(*) - COUNT(DISTINCT product_id) FROM ods_product_features_valid)
        AS duplicate_primary_keys
), fk_stats AS (
    SELECT
        (SELECT COUNT(*) FROM ods_orders_valid orders LEFT ANTI JOIN ods_users_valid users ON orders.user_id = users.user_id)
      + (SELECT COUNT(*) FROM ods_orders_valid orders LEFT ANTI JOIN ods_products_valid products ON orders.product_id = products.product_id)
      + (SELECT COUNT(*) FROM ods_user_behaviors_valid behavior LEFT ANTI JOIN ods_users_valid users ON behavior.user_id = users.user_id)
      + (SELECT COUNT(*) FROM ods_user_behaviors_valid behavior LEFT ANTI JOIN ods_products_valid products ON behavior.product_id = products.product_id)
        AS broken_foreign_keys
), amount_stats AS (
    SELECT
        SUM(CASE WHEN ABS(total_amount - discount - actual_payment) > 0.01 THEN 1 ELSE 0 END) AS amount_equation_mismatches,
        SUM(CASE WHEN ABS(unit_price * quantity - total_amount) > 0.01 THEN 1 ELSE 0 END) AS unit_price_total_mismatches
    FROM stg_orders_normalized
    WHERE rejection_reasons = ''
), lifecycle_stats AS (
    SELECT COUNT(*) AS lifecycle_date_violations
    FROM ods_orders_valid
    WHERE (order_status IN ('已发货','已收货','已完成') AND delivery_ts IS NULL)
       OR (order_status IN ('已收货','已完成') AND receive_ts IS NULL)
       OR delivery_ts < order_ts
       OR receive_ts < delivery_ts
), dwd_stats AS (
    SELECT
        (SELECT COUNT(*) FROM dwd_fact_order) AS dwd_orders,
        (SELECT COUNT(*) FROM dwd_fact_behavior) AS dwd_behaviors,
        (SELECT COUNT(*) FROM dwd_dim_user) AS dwd_users,
        (SELECT COUNT(*) FROM dwd_dim_product) AS dwd_products
), source_user_orders AS (
    SELECT
        user_id,
        COUNT(*) AS order_count,
        SUM(CASE WHEN order_status = '已完成' THEN 1 ELSE 0 END) AS completed_orders,
        ROUND(SUM(actual_payment), 2) AS total_spent
    FROM stg_orders_normalized
    WHERE rejection_reasons = ''
    GROUP BY user_id
), source_user_behaviors AS (
    SELECT
        user_id,
        SUM(CASE WHEN behavior_type = '浏览' THEN 1 ELSE 0 END) AS browse_count,
        SUM(CASE WHEN behavior_type = '点击' THEN 1 ELSE 0 END) AS click_count,
        SUM(CASE WHEN behavior_type = '收藏' THEN 1 ELSE 0 END) AS favorite_count,
        SUM(CASE WHEN behavior_type = '加购' THEN 1 ELSE 0 END) AS cart_count
    FROM stg_behaviors_normalized
    WHERE rejection_reasons = ''
    GROUP BY user_id
), user_feature_stats AS (
    SELECT
        SUM(CASE WHEN
            ABS(features.total_spent - COALESCE(orders.total_spent,0)) > 0.01
            OR features.order_count <> COALESCE(orders.order_count,0)
            OR features.completed_orders <> COALESCE(orders.completed_orders,0)
            OR features.browse_count <> COALESCE(behavior.browse_count,0)
            OR features.click_count <> COALESCE(behavior.click_count,0)
            OR features.favorite_count <> COALESCE(behavior.favorite_count,0)
            OR features.cart_count <> COALESCE(behavior.cart_count,0)
            THEN 1 ELSE 0 END) AS user_feature_mismatches,
        SUM(CASE WHEN features.days_since_last_order = 999 THEN 1 ELSE 0 END) AS last_order_sentinel_rows
    FROM ods_user_features_valid features
    LEFT JOIN source_user_orders orders ON features.user_id = orders.user_id
    LEFT JOIN source_user_behaviors behavior ON features.user_id = behavior.user_id
), source_product_orders AS (
    SELECT
        product_id,
        COUNT(*) AS total_sales,
        SUM(CASE WHEN order_status = '已完成' THEN 1 ELSE 0 END) AS completed_count,
        SUM(CASE WHEN order_status IN ('已取消','已退款') THEN 1 ELSE 0 END) AS cancel_count,
        ROUND(SUM(actual_payment), 2) AS total_revenue
    FROM stg_orders_normalized
    WHERE rejection_reasons = ''
    GROUP BY product_id
), source_product_behaviors AS (
    SELECT
        product_id,
        SUM(CASE WHEN behavior_type = '浏览' THEN 1 ELSE 0 END) AS browse_count,
        SUM(CASE WHEN behavior_type = '点击' THEN 1 ELSE 0 END) AS click_count,
        SUM(CASE WHEN behavior_type = '收藏' THEN 1 ELSE 0 END) AS favorite_count,
        SUM(CASE WHEN behavior_type = '加购' THEN 1 ELSE 0 END) AS cart_count
    FROM stg_behaviors_normalized
    WHERE rejection_reasons = ''
    GROUP BY product_id
), product_feature_stats AS (
    SELECT SUM(CASE WHEN
        ABS(features.total_revenue - COALESCE(orders.total_revenue,0)) > 0.01
        OR features.total_sales <> COALESCE(orders.total_sales,0)
        OR features.completed_count <> COALESCE(orders.completed_count,0)
        OR features.cancel_count <> COALESCE(orders.cancel_count,0)
        OR features.browse_count <> COALESCE(behavior.browse_count,0)
        OR features.click_count <> COALESCE(behavior.click_count,0)
        OR features.favorite_count <> COALESCE(behavior.favorite_count,0)
        OR features.cart_count <> COALESCE(behavior.cart_count,0)
        THEN 1 ELSE 0 END) AS product_feature_mismatches
    FROM ods_product_features_valid features
    LEFT JOIN source_product_orders orders ON features.product_id = orders.product_id
    LEFT JOIN source_product_behaviors behavior ON features.product_id = behavior.product_id
), fact_metrics AS (
    SELECT
        COUNT(*) AS fact_total_orders,
        COUNT(DISTINCT user_id) AS fact_ordering_customers,
        SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS fact_completed_orders,
        COUNT(DISTINCT CASE WHEN is_completed THEN user_id END) AS fact_completed_customers,
        ROUND(SUM(CASE WHEN is_completed THEN actual_payment ELSE 0 END),2) AS fact_completed_gmv,
        SUM(CASE WHEN status_code IN ('cancelled','refunded') THEN 1 ELSE 0 END) AS fact_cancelled_refunded_orders
    FROM dwd_fact_order
), behavior_metrics AS (
    SELECT COUNT(*) AS fact_behavior_events FROM dwd_fact_behavior
), repeat_metrics AS (
    SELECT COUNT(*) AS fact_repeat_completed_customers
    FROM (SELECT user_id FROM dwd_fact_order WHERE is_completed GROUP BY user_id HAVING COUNT(*) >= 2) repeated
), executive_stats AS (
    SELECT
        total_orders AS executive_total_orders,
        ordering_customers AS executive_ordering_customers,
        completed_orders AS executive_completed_orders,
        completed_customers AS executive_completed_customers,
        completed_gmv AS executive_completed_gmv,
        cancelled_or_refunded_orders AS executive_cancelled_refunded_orders,
        repeat_completed_customers AS executive_repeat_completed_customers,
        behavior_events AS executive_behavior_events,
        registered_users AS executive_registered_users,
        products AS executive_products,
        quarantined_rows AS executive_quarantined_rows
    FROM ads_executive_kpis
), daily_stats AS (
    SELECT SUM(total_orders) AS daily_orders, ROUND(SUM(completed_gmv),2) AS daily_completed_gmv
    FROM dws_daily_commerce
), funnel_ordered AS (
    SELECT stage_order, user_count, LAG(user_count) OVER (ORDER BY stage_order) AS previous_count
    FROM dws_sequential_funnel
), funnel_stats AS (
    SELECT COUNT(*) AS funnel_stages,
           SUM(CASE WHEN previous_count IS NOT NULL AND user_count > previous_count THEN 1 ELSE 0 END) AS funnel_violations
    FROM funnel_ordered
), segment_stats AS (
    SELECT SUM(user_count) AS segment_users, SUM(user_share) AS segment_share
    FROM dws_customer_segments
), ads_stats AS (
    SELECT
        (CASE WHEN (SELECT COUNT(*) FROM ads_executive_kpis) > 0 THEN 1 ELSE 0 END)
      + (CASE WHEN (SELECT COUNT(*) FROM ads_daily_trend) > 0 THEN 1 ELSE 0 END)
      + (CASE WHEN (SELECT COUNT(*) FROM ads_sequential_funnel) > 0 THEN 1 ELSE 0 END)
      + (CASE WHEN (SELECT COUNT(*) FROM ads_category_performance) > 0 THEN 1 ELSE 0 END)
      + (CASE WHEN (SELECT COUNT(*) FROM ads_hourly_behavior) > 0 THEN 1 ELSE 0 END)
      + (CASE WHEN (SELECT COUNT(*) FROM ads_customer_segments) > 0 THEN 1 ELSE 0 END)
      + (CASE WHEN (SELECT COUNT(*) FROM ads_order_status) > 0 THEN 1 ELSE 0 END)
        AS non_empty_ads_tables
), metrics AS (
    SELECT * FROM raw_counts
    CROSS JOIN valid_counts
    CROSS JOIN duplicate_stats
    CROSS JOIN fk_stats
    CROSS JOIN amount_stats
    CROSS JOIN lifecycle_stats
    CROSS JOIN dwd_stats
    CROSS JOIN user_feature_stats
    CROSS JOIN product_feature_stats
    CROSS JOIN fact_metrics
    CROSS JOIN behavior_metrics
    CROSS JOIN repeat_metrics
    CROSS JOIN executive_stats
    CROSS JOIN daily_stats
    CROSS JOIN funnel_stats
    CROSS JOIN segment_stats
    CROSS JOIN ads_stats
), checks AS (
    SELECT 'all_source_tables_non_empty' AS check_name,
           CASE WHEN LEAST(raw_users,raw_products,raw_orders,raw_behaviors,raw_user_features,raw_product_features) > 0 THEN 'pass' ELSE 'fail' END AS check_status,
           CONCAT_WS(',',raw_users,raw_products,raw_orders,raw_behaviors,raw_user_features,raw_product_features) AS observed_value,
           'all six tables > 0' AS expected_value,
           'critical' AS severity,
           'Every contracted source table must contain data.' AS details
    FROM metrics

    UNION ALL SELECT 'raw_ods_row_reconciliation',
        CASE WHEN raw_users=valid_users+quarantine_users
               AND raw_products=valid_products+quarantine_products
               AND raw_orders=valid_orders+quarantine_orders
               AND raw_behaviors=valid_behaviors+quarantine_behaviors
               AND raw_user_features=valid_user_features+quarantine_user_features
               AND raw_product_features=valid_product_features+quarantine_product_features
             THEN 'pass' ELSE 'fail' END,
        CONCAT('quarantine=',quarantine_total), 'raw=valid+quarantine for all tables', 'critical',
        'Every source row must land in exactly one ODS outcome.' FROM metrics

    UNION ALL SELECT 'non_temporal_quarantine_empty',
        CASE WHEN non_temporal_quarantine=0 THEN 'pass' ELSE 'fail' END,
        CAST(non_temporal_quarantine AS STRING), '0', 'critical',
        'Only pure pre-registration temporal anomalies may be quarantined without blocking publication.' FROM metrics

    UNION ALL SELECT 'primary_keys_unique', CASE WHEN duplicate_primary_keys=0 THEN 'pass' ELSE 'fail' END,
        CAST(duplicate_primary_keys AS STRING), '0', 'critical', 'All six business keys must be unique.' FROM metrics

    UNION ALL SELECT 'foreign_keys_complete', CASE WHEN broken_foreign_keys=0 THEN 'pass' ELSE 'fail' END,
        CAST(broken_foreign_keys AS STRING), '0', 'critical', 'Published order and behavior facts require valid user and product parents.' FROM metrics

    UNION ALL SELECT 'ods_dwd_order_reconciliation', CASE WHEN valid_orders=dwd_orders THEN 'pass' ELSE 'fail' END,
        CONCAT(valid_orders,'=',dwd_orders), 'ods_orders=dwd_orders', 'critical', 'DWD must retain every valid order.' FROM metrics

    UNION ALL SELECT 'ods_dwd_behavior_reconciliation', CASE WHEN valid_behaviors=dwd_behaviors THEN 'pass' ELSE 'fail' END,
        CONCAT(valid_behaviors,'=',dwd_behaviors), 'ods_behaviors=dwd_behaviors', 'critical', 'DWD must retain every valid behavior.' FROM metrics

    UNION ALL SELECT 'amount_equation_valid', CASE WHEN amount_equation_mismatches=0 THEN 'pass' ELSE 'fail' END,
        CAST(amount_equation_mismatches AS STRING), '0', 'critical', 'actual_payment must equal total_amount minus discount.' FROM metrics

    UNION ALL SELECT 'order_lifecycle_dates_valid', CASE WHEN lifecycle_date_violations=0 THEN 'pass' ELSE 'fail' END,
        CAST(lifecycle_date_violations AS STRING), '0', 'critical', 'Shipping and receipt timestamps must match lifecycle state and sequence.' FROM metrics

    UNION ALL SELECT 'user_feature_snapshot_reconciles', CASE WHEN user_feature_mismatches=0 THEN 'pass' ELSE 'fail' END,
        CAST(user_feature_mismatches AS STRING), '0', 'critical', 'Audit-only user feature counts must match independent source fact aggregation.' FROM metrics

    UNION ALL SELECT 'product_feature_snapshot_reconciles', CASE WHEN product_feature_mismatches=0 THEN 'pass' ELSE 'fail' END,
        CAST(product_feature_mismatches AS STRING), '0', 'critical', 'Audit-only product feature counts must match independent source fact aggregation.' FROM metrics

    UNION ALL SELECT 'executive_kpis_reconcile',
        CASE WHEN executive_total_orders=fact_total_orders
               AND executive_ordering_customers=fact_ordering_customers
               AND executive_completed_orders=fact_completed_orders
               AND executive_completed_customers=fact_completed_customers
               AND ABS(executive_completed_gmv-fact_completed_gmv)<=0.01
               AND executive_cancelled_refunded_orders=fact_cancelled_refunded_orders
               AND executive_repeat_completed_customers=fact_repeat_completed_customers
               AND executive_behavior_events=fact_behavior_events
               AND executive_registered_users=dwd_users
               AND executive_products=dwd_products
               AND executive_quarantined_rows=quarantine_total
             THEN 'pass' ELSE 'fail' END,
        CONCAT('orders=',executive_total_orders,',behaviors=',executive_behavior_events,',quarantine=',executive_quarantined_rows),
        'ADS equals independent DWD recomputation', 'critical', 'Published headline KPIs must reconcile to cleaned facts.' FROM metrics

    UNION ALL SELECT 'daily_orders_reconcile',
        CASE WHEN daily_orders=fact_total_orders AND ABS(daily_completed_gmv-fact_completed_gmv)<=0.01 THEN 'pass' ELSE 'fail' END,
        CONCAT('orders=',daily_orders,',completed=',daily_completed_gmv), 'daily totals = DWD totals', 'critical',
        'Daily commerce totals must reconcile to the order fact.' FROM metrics

    UNION ALL SELECT 'sequential_funnel_monotonic',
        CASE WHEN funnel_stages=4 AND funnel_violations=0 THEN 'pass' ELSE 'fail' END,
        CONCAT('stages=',funnel_stages,',violations=',funnel_violations), 'stages=4,violations=0', 'critical',
        'User-level sequential stage counts may never increase.' FROM metrics

    UNION ALL SELECT 'customer_segments_reconcile',
        CASE WHEN segment_users=dwd_users AND ABS(segment_share-1.0)<=0.001 THEN 'pass' ELSE 'fail' END,
        CONCAT('users=',segment_users,',share=',ROUND(segment_share,4)), 'segments cover all users exactly once', 'critical',
        'Customer segments must be mutually exclusive and exhaustive.' FROM metrics

    UNION ALL SELECT 'ads_outputs_non_empty', CASE WHEN non_empty_ads_tables=7 THEN 'pass' ELSE 'fail' END,
        CAST(non_empty_ads_tables AS STRING), '7', 'critical', 'All public aggregate tables must contain rows.' FROM metrics

    UNION ALL SELECT 'quarantined_source_rows_reported', CASE WHEN quarantine_total=0 THEN 'pass' ELSE 'warn' END,
        CAST(quarantine_total AS STRING), 'reported and excluded', 'warning',
        'Invalid source rows are isolated and excluded from business aggregates.' FROM metrics

    UNION ALL SELECT 'pre_registration_events_reported', CASE WHEN pre_registration_quarantine=0 THEN 'pass' ELSE 'warn' END,
        CAST(pre_registration_quarantine AS STRING), 'reported and excluded', 'warning',
        'Orders or behaviors before registration are quarantined as temporal anomalies.' FROM metrics

    UNION ALL SELECT 'unit_price_total_difference_reported', CASE WHEN unit_price_total_mismatches=0 THEN 'pass' ELSE 'warn' END,
        CAST(unit_price_total_mismatches AS STRING), 'reported only', 'warning',
        'unit_price × quantity is not treated as authoritative because the source total_amount uses an undocumented adjustment.' FROM metrics

    UNION ALL SELECT 'feature_last_order_sentinel_reported', CASE WHEN last_order_sentinel_rows=0 THEN 'pass' ELSE 'warn' END,
        CAST(last_order_sentinel_rows AS STRING), 'reported only', 'warning',
        'days_since_last_order sentinel values are not used in business metrics.' FROM metrics
)
SELECT check_name, check_status, observed_value, expected_value, severity, details,
       CURRENT_TIMESTAMP() AS checked_at
FROM checks;

DROP TABLE IF EXISTS ads_dataops_health;
CREATE TABLE ads_dataops_health USING PARQUET COMMENT 'Grain: one public aggregate quality check.' AS
SELECT * FROM ops_data_quality_results ORDER BY check_name;
