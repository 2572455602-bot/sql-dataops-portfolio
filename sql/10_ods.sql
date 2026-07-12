-- ODS normalization and quarantine.
-- Each valid table preserves one source row. Invalid rows land once in a
-- unified quarantine table with semicolon-delimited reasons.

CREATE OR REPLACE TEMP VIEW stg_users_normalized AS
SELECT
    TRIM(user_id_raw) AS user_id,
    TRY_CAST(TRIM(age_raw) AS INT) AS age,
    TRIM(gender_raw) AS gender,
    TRIM(province_raw) AS province,
    TRIM(city_raw) AS city,
    TRY_CAST(TRIM(registration_date_raw) AS TIMESTAMP) AS registration_ts,
    TRIM(member_level_raw) AS member_level,
    TRY_CAST(TRIM(account_balance_raw) AS DECIMAL(18,2)) AS account_balance,
    TRY_CAST(TRIM(credit_score_raw) AS INT) AS credit_score,
    source_file,
    ingested_at,
    CONCAT_WS(
        ';',
        CASE WHEN corrupt_record IS NOT NULL AND TRIM(corrupt_record) <> '' THEN 'malformed_csv' END,
        CASE WHEN TRIM(COALESCE(user_id_raw,'')) = ''
                   OR NOT (TRIM(user_id_raw) RLIKE '^U[0-9]{6}$')
             THEN 'invalid_user_id' END,
        CASE WHEN TRY_CAST(TRIM(age_raw) AS INT) IS NULL THEN 'invalid_age_parse' END,
        CASE WHEN TRY_CAST(TRIM(age_raw) AS INT) NOT BETWEEN 13 AND 100 THEN 'invalid_age' END,
        CASE WHEN TRIM(COALESCE(gender_raw,'')) = ''
                   OR TRIM(gender_raw) NOT IN ('男','女','其他')
             THEN 'invalid_gender' END,
        CASE WHEN TRIM(COALESCE(province_raw,'')) = '' OR TRIM(COALESCE(city_raw,'')) = '' THEN 'missing_region' END,
        CASE WHEN TRY_CAST(TRIM(registration_date_raw) AS TIMESTAMP) IS NULL THEN 'invalid_registration_date' END,
        CASE WHEN TRIM(COALESCE(member_level_raw,'')) = ''
                   OR TRIM(member_level_raw) NOT IN ('普通会员','铜牌会员','银牌会员','金牌会员','钻石会员')
             THEN 'invalid_member_level' END,
        CASE WHEN TRY_CAST(TRIM(account_balance_raw) AS DECIMAL(18,2)) IS NULL THEN 'invalid_account_balance_parse' END,
        CASE WHEN TRY_CAST(TRIM(account_balance_raw) AS DECIMAL(18,2)) < 0 THEN 'invalid_account_balance' END,
        CASE WHEN TRY_CAST(TRIM(credit_score_raw) AS INT) IS NULL THEN 'invalid_credit_score_parse' END,
        CASE WHEN TRY_CAST(TRIM(credit_score_raw) AS INT) NOT BETWEEN 0 AND 1000 THEN 'invalid_credit_score' END
    ) AS rejection_reasons
FROM raw_users_contract;

CREATE OR REPLACE TEMP VIEW stg_products_normalized AS
SELECT
    TRIM(product_id_raw) AS product_id,
    TRIM(product_name_raw) AS product_name,
    TRIM(category_raw) AS category,
    TRIM(brand_raw) AS brand,
    TRY_CAST(TRIM(price_raw) AS DECIMAL(18,2)) AS price,
    TRY_CAST(TRIM(sales_count_raw) AS BIGINT) AS sales_count,
    source_file,
    ingested_at,
    CONCAT_WS(
        ';',
        CASE WHEN corrupt_record IS NOT NULL AND TRIM(corrupt_record) <> '' THEN 'malformed_csv' END,
        CASE WHEN TRIM(COALESCE(product_id_raw,'')) = ''
                   OR NOT (TRIM(product_id_raw) RLIKE '^P[0-9]{6}$')
             THEN 'invalid_product_id' END,
        CASE WHEN TRIM(COALESCE(product_name_raw,'')) = '' THEN 'missing_product_name' END,
        CASE WHEN TRIM(COALESCE(category_raw,'')) = '' THEN 'missing_category' END,
        CASE WHEN TRIM(COALESCE(brand_raw,'')) = '' THEN 'missing_brand' END,
        CASE WHEN TRY_CAST(TRIM(price_raw) AS DECIMAL(18,2)) IS NULL THEN 'invalid_price_parse' END,
        CASE WHEN TRY_CAST(TRIM(price_raw) AS DECIMAL(18,2)) < 0 THEN 'invalid_price' END,
        CASE WHEN TRY_CAST(TRIM(sales_count_raw) AS BIGINT) IS NULL THEN 'invalid_sales_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(sales_count_raw) AS BIGINT) < 0 THEN 'invalid_sales_count' END
    ) AS rejection_reasons
FROM raw_products_contract;

CREATE OR REPLACE TEMP VIEW stg_orders_normalized AS
SELECT
    TRIM(order_id_raw) AS order_id,
    TRIM(user_id_raw) AS user_id,
    TRIM(product_id_raw) AS product_id,
    TRY_CAST(TRIM(quantity_raw) AS INT) AS quantity,
    TRY_CAST(TRIM(order_date_raw) AS TIMESTAMP) AS order_ts,
    TRIM(order_status_raw) AS order_status,
    TRIM(payment_method_raw) AS payment_method,
    TRY_CAST(TRIM(unit_price_raw) AS DECIMAL(18,2)) AS unit_price,
    TRY_CAST(TRIM(total_amount_raw) AS DECIMAL(18,2)) AS total_amount,
    TRY_CAST(TRIM(discount_raw) AS DECIMAL(18,2)) AS discount,
    TRY_CAST(TRIM(actual_payment_raw) AS DECIMAL(18,2)) AS actual_payment,
    CASE WHEN TRIM(COALESCE(delivery_date_raw,'')) = '' THEN NULL ELSE TRY_CAST(TRIM(delivery_date_raw) AS TIMESTAMP) END AS delivery_ts,
    CASE WHEN TRIM(COALESCE(receive_date_raw,'')) = '' THEN NULL ELSE TRY_CAST(TRIM(receive_date_raw) AS TIMESTAMP) END AS receive_ts,
    CASE WHEN TRIM(COALESCE(review_score_raw,'')) = '' THEN NULL ELSE TRY_CAST(TRIM(review_score_raw) AS INT) END AS review_score,
    NULLIF(TRIM(review_content_raw), '') AS review_content,
    source_file,
    ingested_at,
    CONCAT_WS(
        ';',
        CASE WHEN corrupt_record IS NOT NULL AND TRIM(corrupt_record) <> '' THEN 'malformed_csv' END,
        CASE WHEN TRIM(COALESCE(order_id_raw,'')) = ''
                   OR NOT (TRIM(order_id_raw) RLIKE '^O[0-9]{8}$')
             THEN 'invalid_order_id' END,
        CASE WHEN TRIM(COALESCE(user_id_raw,'')) = ''
                   OR NOT (TRIM(user_id_raw) RLIKE '^U[0-9]{6}$')
             THEN 'invalid_user_id' END,
        CASE WHEN TRIM(COALESCE(product_id_raw,'')) = ''
                   OR NOT (TRIM(product_id_raw) RLIKE '^P[0-9]{6}$')
             THEN 'invalid_product_id' END,
        CASE WHEN TRY_CAST(TRIM(quantity_raw) AS INT) IS NULL THEN 'invalid_quantity_parse' END,
        CASE WHEN TRY_CAST(TRIM(quantity_raw) AS INT) <= 0 THEN 'invalid_quantity' END,
        CASE WHEN TRY_CAST(TRIM(order_date_raw) AS TIMESTAMP) IS NULL THEN 'invalid_order_date' END,
        CASE WHEN TRIM(COALESCE(order_status_raw,'')) = ''
                   OR TRIM(order_status_raw) NOT IN ('待付款','已付款','已发货','已收货','已完成','已取消','已退款')
             THEN 'invalid_order_status' END,
        CASE WHEN TRIM(COALESCE(payment_method_raw,'')) = '' THEN 'missing_payment_method' END,
        CASE WHEN TRY_CAST(TRIM(unit_price_raw) AS DECIMAL(18,2)) IS NULL THEN 'invalid_unit_price_parse' END,
        CASE WHEN TRY_CAST(TRIM(total_amount_raw) AS DECIMAL(18,2)) IS NULL THEN 'invalid_total_amount_parse' END,
        CASE WHEN TRY_CAST(TRIM(discount_raw) AS DECIMAL(18,2)) IS NULL THEN 'invalid_discount_parse' END,
        CASE WHEN TRY_CAST(TRIM(actual_payment_raw) AS DECIMAL(18,2)) IS NULL THEN 'invalid_actual_payment_parse' END,
        CASE WHEN TRY_CAST(TRIM(unit_price_raw) AS DECIMAL(18,2)) < 0
               OR TRY_CAST(TRIM(total_amount_raw) AS DECIMAL(18,2)) < 0
               OR TRY_CAST(TRIM(discount_raw) AS DECIMAL(18,2)) < 0
               OR TRY_CAST(TRIM(actual_payment_raw) AS DECIMAL(18,2)) < 0
             THEN 'invalid_amount' END,
        CASE WHEN ABS(
                    TRY_CAST(TRIM(total_amount_raw) AS DECIMAL(18,2))
                  - TRY_CAST(TRIM(discount_raw) AS DECIMAL(18,2))
                  - TRY_CAST(TRIM(actual_payment_raw) AS DECIMAL(18,2))
                 ) > 0.01 THEN 'amount_equation_mismatch' END,
        CASE WHEN TRIM(COALESCE(delivery_date_raw,'')) <> ''
                   AND TRY_CAST(TRIM(delivery_date_raw) AS TIMESTAMP) IS NULL
             THEN 'invalid_delivery_date' END,
        CASE WHEN TRIM(COALESCE(receive_date_raw,'')) <> ''
                   AND TRY_CAST(TRIM(receive_date_raw) AS TIMESTAMP) IS NULL
             THEN 'invalid_receive_date' END,
        CASE WHEN TRIM(COALESCE(review_score_raw,'')) <> ''
                   AND (TRY_CAST(TRIM(review_score_raw) AS INT) IS NULL
                        OR TRY_CAST(TRIM(review_score_raw) AS INT) NOT BETWEEN 1 AND 5)
             THEN 'invalid_review_score' END
    ) AS rejection_reasons
FROM raw_orders_contract;

CREATE OR REPLACE TEMP VIEW stg_behaviors_normalized AS
SELECT
    TRIM(behavior_id_raw) AS behavior_id,
    TRIM(user_id_raw) AS user_id,
    TRIM(product_id_raw) AS product_id,
    TRIM(behavior_type_raw) AS behavior_type,
    TRY_CAST(TRIM(behavior_time_raw) AS TIMESTAMP) AS behavior_ts,
    TRY_CAST(TRIM(duration_seconds_raw) AS INT) AS duration_seconds,
    source_file,
    ingested_at,
    CONCAT_WS(
        ';',
        CASE WHEN corrupt_record IS NOT NULL AND TRIM(corrupt_record) <> '' THEN 'malformed_csv' END,
        CASE WHEN TRIM(COALESCE(behavior_id_raw,'')) = ''
                   OR NOT (TRIM(behavior_id_raw) RLIKE '^B[0-9]{8}$')
             THEN 'invalid_behavior_id' END,
        CASE WHEN TRIM(COALESCE(user_id_raw,'')) = ''
                   OR NOT (TRIM(user_id_raw) RLIKE '^U[0-9]{6}$')
             THEN 'invalid_user_id' END,
        CASE WHEN TRIM(COALESCE(product_id_raw,'')) = ''
                   OR NOT (TRIM(product_id_raw) RLIKE '^P[0-9]{6}$')
             THEN 'invalid_product_id' END,
        CASE WHEN TRIM(COALESCE(behavior_type_raw,'')) = ''
                   OR TRIM(behavior_type_raw) NOT IN ('浏览','点击','收藏','加购')
             THEN 'invalid_behavior_type' END,
        CASE WHEN TRY_CAST(TRIM(behavior_time_raw) AS TIMESTAMP) IS NULL THEN 'invalid_behavior_time' END,
        CASE WHEN TRY_CAST(TRIM(duration_seconds_raw) AS INT) IS NULL THEN 'invalid_duration_parse' END,
        CASE WHEN TRY_CAST(TRIM(duration_seconds_raw) AS INT) < 0 THEN 'invalid_duration' END
    ) AS rejection_reasons
FROM raw_user_behaviors_contract;

CREATE OR REPLACE TEMP VIEW stg_user_features_normalized AS
SELECT
    TRIM(user_id_raw) AS user_id,
    TRY_CAST(TRIM(total_spent_raw) AS DECIMAL(18,2)) AS total_spent,
    CAST(TRY_CAST(TRIM(order_count_raw) AS DECIMAL(20,6)) AS BIGINT) AS order_count,
    CAST(TRY_CAST(TRIM(completed_orders_raw) AS DECIMAL(20,6)) AS BIGINT) AS completed_orders,
    TRY_CAST(TRIM(avg_order_amount_raw) AS DECIMAL(18,4)) AS avg_order_amount,
    CAST(TRY_CAST(TRIM(browse_count_raw) AS DECIMAL(20,6)) AS BIGINT) AS browse_count,
    CAST(TRY_CAST(TRIM(click_count_raw) AS DECIMAL(20,6)) AS BIGINT) AS click_count,
    CAST(TRY_CAST(TRIM(favorite_count_raw) AS DECIMAL(20,6)) AS BIGINT) AS favorite_count,
    CAST(TRY_CAST(TRIM(cart_count_raw) AS DECIMAL(20,6)) AS BIGINT) AS cart_count,
    TRY_CAST(TRIM(days_since_last_order_raw) AS INT) AS days_since_last_order,
    TRY_CAST(TRIM(order_frequency_raw) AS DOUBLE) AS order_frequency,
    TRY_CAST(TRIM(repurchase_indicator_raw) AS INT) AS repurchase_indicator,
    TRY_CAST(TRIM(purchase_intent_raw) AS DOUBLE) AS purchase_intent,
    TRIM(consumption_level_raw) AS consumption_level,
    TRY_CAST(TRIM(member_level_score_raw) AS INT) AS member_level_score,
    source_file,
    ingested_at,
    CONCAT_WS(
        ';',
        CASE WHEN corrupt_record IS NOT NULL AND TRIM(corrupt_record) <> '' THEN 'malformed_csv' END,
        CASE WHEN TRIM(COALESCE(user_id_raw,'')) = ''
                   OR NOT (TRIM(user_id_raw) RLIKE '^U[0-9]{6}$')
             THEN 'invalid_user_id' END,
        CASE WHEN TRY_CAST(TRIM(total_spent_raw) AS DECIMAL(18,2)) IS NULL THEN 'invalid_total_spent_parse' END,
        CASE WHEN TRY_CAST(TRIM(order_count_raw) AS DECIMAL(20,6)) IS NULL THEN 'invalid_order_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(order_count_raw) AS DECIMAL(20,6)) <> FLOOR(TRY_CAST(TRIM(order_count_raw) AS DECIMAL(20,6))) THEN 'invalid_order_count' END,
        CASE WHEN TRY_CAST(TRIM(completed_orders_raw) AS DECIMAL(20,6)) IS NULL THEN 'invalid_completed_orders_parse' END,
        CASE WHEN TRY_CAST(TRIM(completed_orders_raw) AS DECIMAL(20,6)) <> FLOOR(TRY_CAST(TRIM(completed_orders_raw) AS DECIMAL(20,6))) THEN 'invalid_completed_orders' END,
        CASE WHEN TRY_CAST(TRIM(avg_order_amount_raw) AS DECIMAL(18,4)) IS NULL THEN 'invalid_avg_order_amount_parse' END,
        CASE WHEN TRY_CAST(TRIM(browse_count_raw) AS DECIMAL(20,6)) IS NULL THEN 'invalid_browse_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(browse_count_raw) AS DECIMAL(20,6)) <> FLOOR(TRY_CAST(TRIM(browse_count_raw) AS DECIMAL(20,6))) THEN 'invalid_browse_count' END,
        CASE WHEN TRY_CAST(TRIM(click_count_raw) AS DECIMAL(20,6)) IS NULL THEN 'invalid_click_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(click_count_raw) AS DECIMAL(20,6)) <> FLOOR(TRY_CAST(TRIM(click_count_raw) AS DECIMAL(20,6))) THEN 'invalid_click_count' END,
        CASE WHEN TRY_CAST(TRIM(favorite_count_raw) AS DECIMAL(20,6)) IS NULL THEN 'invalid_favorite_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(favorite_count_raw) AS DECIMAL(20,6)) <> FLOOR(TRY_CAST(TRIM(favorite_count_raw) AS DECIMAL(20,6))) THEN 'invalid_favorite_count' END,
        CASE WHEN TRY_CAST(TRIM(cart_count_raw) AS DECIMAL(20,6)) IS NULL THEN 'invalid_cart_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(cart_count_raw) AS DECIMAL(20,6)) <> FLOOR(TRY_CAST(TRIM(cart_count_raw) AS DECIMAL(20,6))) THEN 'invalid_cart_count' END,
        CASE WHEN TRY_CAST(TRIM(days_since_last_order_raw) AS INT) IS NULL THEN 'invalid_days_since_last_order_parse' END,
        CASE WHEN TRY_CAST(TRIM(order_frequency_raw) AS DOUBLE) IS NULL THEN 'invalid_order_frequency_parse' END,
        CASE WHEN TRY_CAST(TRIM(repurchase_indicator_raw) AS INT) IS NULL THEN 'invalid_repurchase_indicator_parse' END,
        CASE WHEN TRY_CAST(TRIM(purchase_intent_raw) AS DOUBLE) IS NULL THEN 'invalid_purchase_intent_parse' END,
        CASE WHEN TRY_CAST(TRIM(member_level_score_raw) AS INT) IS NULL THEN 'invalid_member_level_score_parse' END,
        CASE WHEN TRY_CAST(TRIM(total_spent_raw) AS DECIMAL(18,2)) < 0
               OR TRY_CAST(TRIM(order_count_raw) AS DECIMAL(20,6)) < 0
               OR TRY_CAST(TRIM(completed_orders_raw) AS DECIMAL(20,6)) < 0
               OR TRY_CAST(TRIM(avg_order_amount_raw) AS DECIMAL(18,4)) < 0
               OR TRY_CAST(TRIM(browse_count_raw) AS DECIMAL(20,6)) < 0
               OR TRY_CAST(TRIM(click_count_raw) AS DECIMAL(20,6)) < 0
               OR TRY_CAST(TRIM(favorite_count_raw) AS DECIMAL(20,6)) < 0
               OR TRY_CAST(TRIM(cart_count_raw) AS DECIMAL(20,6)) < 0
             THEN 'invalid_feature_value' END,
        CASE WHEN TRY_CAST(TRIM(repurchase_indicator_raw) AS INT) NOT IN (0,1) THEN 'invalid_repurchase_indicator' END,
        CASE WHEN TRY_CAST(TRIM(purchase_intent_raw) AS DOUBLE) NOT BETWEEN 0 AND 1 THEN 'invalid_purchase_intent' END,
        CASE WHEN TRIM(COALESCE(consumption_level_raw,'')) = ''
                   OR TRIM(consumption_level_raw) NOT IN ('低','中','高')
             THEN 'invalid_consumption_level' END
    ) AS rejection_reasons
FROM raw_user_features_contract;

CREATE OR REPLACE TEMP VIEW stg_product_features_normalized AS
SELECT
    TRIM(product_id_raw) AS product_id,
    TRY_CAST(TRIM(total_revenue_raw) AS DECIMAL(18,2)) AS total_revenue,
    TRY_CAST(TRIM(total_sales_raw) AS BIGINT) AS total_sales,
    TRY_CAST(TRIM(completed_count_raw) AS BIGINT) AS completed_count,
    TRY_CAST(TRIM(cancel_count_raw) AS BIGINT) AS cancel_count,
    TRY_CAST(TRIM(cart_count_raw) AS BIGINT) AS cart_count,
    TRY_CAST(TRIM(favorite_count_raw) AS BIGINT) AS favorite_count,
    TRY_CAST(TRIM(browse_count_raw) AS BIGINT) AS browse_count,
    TRY_CAST(TRIM(click_count_raw) AS BIGINT) AS click_count,
    TRY_CAST(TRIM(conversion_rate_raw) AS DOUBLE) AS conversion_rate,
    CASE WHEN TRIM(COALESCE(avg_review_score_raw,'')) = '' THEN NULL ELSE TRY_CAST(TRIM(avg_review_score_raw) AS DOUBLE) END AS avg_review_score,
    TRY_CAST(TRIM(popularity_score_raw) AS DOUBLE) AS popularity_score,
    source_file,
    ingested_at,
    CONCAT_WS(
        ';',
        CASE WHEN corrupt_record IS NOT NULL AND TRIM(corrupt_record) <> '' THEN 'malformed_csv' END,
        CASE WHEN TRIM(COALESCE(product_id_raw,'')) = ''
                   OR NOT (TRIM(product_id_raw) RLIKE '^P[0-9]{6}$')
             THEN 'invalid_product_id' END,
        CASE WHEN TRY_CAST(TRIM(total_revenue_raw) AS DECIMAL(18,2)) IS NULL THEN 'invalid_total_revenue_parse' END,
        CASE WHEN TRY_CAST(TRIM(total_sales_raw) AS BIGINT) IS NULL THEN 'invalid_total_sales_parse' END,
        CASE WHEN TRY_CAST(TRIM(completed_count_raw) AS BIGINT) IS NULL THEN 'invalid_completed_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(cancel_count_raw) AS BIGINT) IS NULL THEN 'invalid_cancel_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(cart_count_raw) AS BIGINT) IS NULL THEN 'invalid_cart_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(favorite_count_raw) AS BIGINT) IS NULL THEN 'invalid_favorite_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(browse_count_raw) AS BIGINT) IS NULL THEN 'invalid_browse_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(click_count_raw) AS BIGINT) IS NULL THEN 'invalid_click_count_parse' END,
        CASE WHEN TRY_CAST(TRIM(conversion_rate_raw) AS DOUBLE) IS NULL THEN 'invalid_conversion_rate_parse' END,
        CASE WHEN TRY_CAST(TRIM(popularity_score_raw) AS DOUBLE) IS NULL THEN 'invalid_popularity_score_parse' END,
        CASE WHEN TRY_CAST(TRIM(total_revenue_raw) AS DECIMAL(18,2)) < 0
               OR TRY_CAST(TRIM(total_sales_raw) AS BIGINT) < 0
               OR TRY_CAST(TRIM(completed_count_raw) AS BIGINT) < 0
               OR TRY_CAST(TRIM(cancel_count_raw) AS BIGINT) < 0
               OR TRY_CAST(TRIM(cart_count_raw) AS BIGINT) < 0
               OR TRY_CAST(TRIM(favorite_count_raw) AS BIGINT) < 0
               OR TRY_CAST(TRIM(browse_count_raw) AS BIGINT) < 0
               OR TRY_CAST(TRIM(click_count_raw) AS BIGINT) < 0
             THEN 'invalid_feature_value' END,
        CASE WHEN TRY_CAST(TRIM(conversion_rate_raw) AS DOUBLE) NOT BETWEEN 0 AND 1 THEN 'invalid_conversion_rate' END,
        CASE WHEN TRIM(COALESCE(avg_review_score_raw,'')) <> ''
                   AND (TRY_CAST(TRIM(avg_review_score_raw) AS DOUBLE) IS NULL
                        OR TRY_CAST(TRIM(avg_review_score_raw) AS DOUBLE) NOT BETWEEN 1 AND 5)
             THEN 'invalid_review_score' END
    ) AS rejection_reasons
FROM raw_product_features_contract;

CREATE OR REPLACE TEMP VIEW stg_orders_validated AS
SELECT
    orders.*,
    CONCAT_WS(
        ';',
        NULLIF(orders.rejection_reasons, ''),
        CASE WHEN users.user_id IS NULL OR users.rejection_reasons <> '' THEN 'broken_user_fk' END,
        CASE WHEN products.product_id IS NULL OR products.rejection_reasons <> '' THEN 'broken_product_fk' END,
        CASE WHEN users.registration_ts IS NOT NULL AND orders.order_ts < users.registration_ts
             THEN 'event_before_registration' END
    ) AS final_rejection_reasons
FROM stg_orders_normalized orders
LEFT JOIN stg_users_normalized users ON orders.user_id = users.user_id
LEFT JOIN stg_products_normalized products ON orders.product_id = products.product_id;

CREATE OR REPLACE TEMP VIEW stg_behaviors_validated AS
SELECT
    behaviors.*,
    CONCAT_WS(
        ';',
        NULLIF(behaviors.rejection_reasons, ''),
        CASE WHEN users.user_id IS NULL OR users.rejection_reasons <> '' THEN 'broken_user_fk' END,
        CASE WHEN products.product_id IS NULL OR products.rejection_reasons <> '' THEN 'broken_product_fk' END,
        CASE WHEN users.registration_ts IS NOT NULL AND behaviors.behavior_ts < users.registration_ts
             THEN 'event_before_registration' END
    ) AS final_rejection_reasons
FROM stg_behaviors_normalized behaviors
LEFT JOIN stg_users_normalized users ON behaviors.user_id = users.user_id
LEFT JOIN stg_products_normalized products ON behaviors.product_id = products.product_id;

CREATE OR REPLACE TEMP VIEW stg_user_features_validated AS
SELECT
    features.*,
    CONCAT_WS(
        ';',
        NULLIF(features.rejection_reasons, ''),
        CASE WHEN users.user_id IS NULL OR users.rejection_reasons <> '' THEN 'broken_user_fk' END
    ) AS final_rejection_reasons
FROM stg_user_features_normalized features
LEFT JOIN stg_users_normalized users ON features.user_id = users.user_id;

CREATE OR REPLACE TEMP VIEW stg_product_features_validated AS
SELECT
    features.*,
    CONCAT_WS(
        ';',
        NULLIF(features.rejection_reasons, ''),
        CASE WHEN products.product_id IS NULL OR products.rejection_reasons <> '' THEN 'broken_product_fk' END
    ) AS final_rejection_reasons
FROM stg_product_features_normalized features
LEFT JOIN stg_products_normalized products ON features.product_id = products.product_id;

DROP TABLE IF EXISTS ods_users_valid;
CREATE TABLE ods_users_valid USING PARQUET COMMENT 'Grain: one valid source user.' AS
SELECT user_id, age, gender, province, city, registration_ts, member_level,
       account_balance, credit_score, source_file, ingested_at
FROM stg_users_normalized WHERE rejection_reasons = '';

DROP TABLE IF EXISTS ods_products_valid;
CREATE TABLE ods_products_valid USING PARQUET COMMENT 'Grain: one valid source product.' AS
SELECT product_id, product_name, category, brand, price, sales_count, source_file, ingested_at
FROM stg_products_normalized WHERE rejection_reasons = '';

DROP TABLE IF EXISTS ods_orders_valid;
CREATE TABLE ods_orders_valid USING PARQUET COMMENT 'Grain: one valid source order.' AS
SELECT order_id, user_id, product_id, quantity, order_ts, order_status, payment_method,
       unit_price, total_amount, discount, actual_payment, delivery_ts, receive_ts,
       review_score, review_content, source_file, ingested_at
FROM stg_orders_validated WHERE final_rejection_reasons = '';

DROP TABLE IF EXISTS ods_user_behaviors_valid;
CREATE TABLE ods_user_behaviors_valid USING PARQUET COMMENT 'Grain: one valid source behavior event.' AS
SELECT behavior_id, user_id, product_id, behavior_type, behavior_ts, duration_seconds,
       source_file, ingested_at
FROM stg_behaviors_validated WHERE final_rejection_reasons = '';

DROP TABLE IF EXISTS ods_user_features_valid;
CREATE TABLE ods_user_features_valid USING PARQUET COMMENT 'Grain: one valid source user feature snapshot.' AS
SELECT user_id, total_spent, order_count, completed_orders, avg_order_amount,
       browse_count, click_count, favorite_count, cart_count, days_since_last_order,
       order_frequency, repurchase_indicator, purchase_intent, consumption_level,
       member_level_score, source_file, ingested_at
FROM stg_user_features_validated WHERE final_rejection_reasons = '';

DROP TABLE IF EXISTS ods_product_features_valid;
CREATE TABLE ods_product_features_valid USING PARQUET COMMENT 'Grain: one valid source product feature snapshot.' AS
SELECT product_id, total_revenue, total_sales, completed_count, cancel_count,
       cart_count, favorite_count, browse_count, click_count, conversion_rate,
       avg_review_score, popularity_score, source_file, ingested_at
FROM stg_product_features_validated WHERE final_rejection_reasons = '';

DROP TABLE IF EXISTS ods_quarantine;
CREATE TABLE ods_quarantine USING PARQUET COMMENT 'Grain: one invalid source row with all rejection reasons.' AS
SELECT 'users' AS source_table, user_id AS record_key, rejection_reasons, source_file, ingested_at, CURRENT_TIMESTAMP() AS quarantined_at
FROM stg_users_normalized WHERE rejection_reasons <> ''
UNION ALL
SELECT 'products', product_id, rejection_reasons, source_file, ingested_at, CURRENT_TIMESTAMP()
FROM stg_products_normalized WHERE rejection_reasons <> ''
UNION ALL
SELECT 'orders', order_id, final_rejection_reasons, source_file, ingested_at, CURRENT_TIMESTAMP()
FROM stg_orders_validated WHERE final_rejection_reasons <> ''
UNION ALL
SELECT 'user_behaviors', behavior_id, final_rejection_reasons, source_file, ingested_at, CURRENT_TIMESTAMP()
FROM stg_behaviors_validated WHERE final_rejection_reasons <> ''
UNION ALL
SELECT 'user_features', user_id, final_rejection_reasons, source_file, ingested_at, CURRENT_TIMESTAMP()
FROM stg_user_features_validated WHERE final_rejection_reasons <> ''
UNION ALL
SELECT 'product_features', product_id, final_rejection_reasons, source_file, ingested_at, CURRENT_TIMESTAMP()
FROM stg_product_features_validated WHERE final_rejection_reasons <> '';
