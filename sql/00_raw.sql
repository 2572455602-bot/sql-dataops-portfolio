-- RAW contract views.
-- Grain: one source CSV row, preserved as strings plus ingestion metadata.

CREATE OR REPLACE TEMP VIEW raw_users_contract AS
SELECT
    CAST(user_id AS STRING) AS user_id_raw,
    CAST(age AS STRING) AS age_raw,
    CAST(gender AS STRING) AS gender_raw,
    CAST(province AS STRING) AS province_raw,
    CAST(city AS STRING) AS city_raw,
    CAST(registration_date AS STRING) AS registration_date_raw,
    CAST(member_level AS STRING) AS member_level_raw,
    CAST(account_balance AS STRING) AS account_balance_raw,
    CAST(credit_score AS STRING) AS credit_score_raw,
    CAST(_corrupt_record AS STRING) AS corrupt_record,
    CAST(_source_file AS STRING) AS source_file,
    TRY_CAST(_ingested_at AS TIMESTAMP) AS ingested_at
FROM raw_users_raw;

CREATE OR REPLACE TEMP VIEW raw_products_contract AS
SELECT
    CAST(product_id AS STRING) AS product_id_raw,
    CAST(product_name AS STRING) AS product_name_raw,
    CAST(category AS STRING) AS category_raw,
    CAST(brand AS STRING) AS brand_raw,
    CAST(price AS STRING) AS price_raw,
    CAST(sales_count AS STRING) AS sales_count_raw,
    CAST(_corrupt_record AS STRING) AS corrupt_record,
    CAST(_source_file AS STRING) AS source_file,
    TRY_CAST(_ingested_at AS TIMESTAMP) AS ingested_at
FROM raw_products_raw;

CREATE OR REPLACE TEMP VIEW raw_orders_contract AS
SELECT
    CAST(order_id AS STRING) AS order_id_raw,
    CAST(user_id AS STRING) AS user_id_raw,
    CAST(product_id AS STRING) AS product_id_raw,
    CAST(quantity AS STRING) AS quantity_raw,
    CAST(order_date AS STRING) AS order_date_raw,
    CAST(order_status AS STRING) AS order_status_raw,
    CAST(payment_method AS STRING) AS payment_method_raw,
    CAST(unit_price AS STRING) AS unit_price_raw,
    CAST(total_amount AS STRING) AS total_amount_raw,
    CAST(discount AS STRING) AS discount_raw,
    CAST(actual_payment AS STRING) AS actual_payment_raw,
    CAST(delivery_date AS STRING) AS delivery_date_raw,
    CAST(receive_date AS STRING) AS receive_date_raw,
    CAST(review_score AS STRING) AS review_score_raw,
    CAST(review_content AS STRING) AS review_content_raw,
    CAST(_corrupt_record AS STRING) AS corrupt_record,
    CAST(_source_file AS STRING) AS source_file,
    TRY_CAST(_ingested_at AS TIMESTAMP) AS ingested_at
FROM raw_orders_raw;

CREATE OR REPLACE TEMP VIEW raw_user_behaviors_contract AS
SELECT
    CAST(behavior_id AS STRING) AS behavior_id_raw,
    CAST(user_id AS STRING) AS user_id_raw,
    CAST(product_id AS STRING) AS product_id_raw,
    CAST(behavior_type AS STRING) AS behavior_type_raw,
    CAST(behavior_time AS STRING) AS behavior_time_raw,
    CAST(duration_seconds AS STRING) AS duration_seconds_raw,
    CAST(_corrupt_record AS STRING) AS corrupt_record,
    CAST(_source_file AS STRING) AS source_file,
    TRY_CAST(_ingested_at AS TIMESTAMP) AS ingested_at
FROM raw_user_behaviors_raw;

CREATE OR REPLACE TEMP VIEW raw_user_features_contract AS
SELECT
    CAST(user_id AS STRING) AS user_id_raw,
    CAST(total_spent AS STRING) AS total_spent_raw,
    CAST(order_count AS STRING) AS order_count_raw,
    CAST(completed_orders AS STRING) AS completed_orders_raw,
    CAST(avg_order_amount AS STRING) AS avg_order_amount_raw,
    CAST(browse_count AS STRING) AS browse_count_raw,
    CAST(click_count AS STRING) AS click_count_raw,
    CAST(favorite_count AS STRING) AS favorite_count_raw,
    CAST(cart_count AS STRING) AS cart_count_raw,
    CAST(days_since_last_order AS STRING) AS days_since_last_order_raw,
    CAST(order_frequency AS STRING) AS order_frequency_raw,
    CAST(repurchase_indicator AS STRING) AS repurchase_indicator_raw,
    CAST(purchase_intent AS STRING) AS purchase_intent_raw,
    CAST(consumption_level AS STRING) AS consumption_level_raw,
    CAST(member_level_score AS STRING) AS member_level_score_raw,
    CAST(_corrupt_record AS STRING) AS corrupt_record,
    CAST(_source_file AS STRING) AS source_file,
    TRY_CAST(_ingested_at AS TIMESTAMP) AS ingested_at
FROM raw_user_features_raw;

CREATE OR REPLACE TEMP VIEW raw_product_features_contract AS
SELECT
    CAST(product_id AS STRING) AS product_id_raw,
    CAST(total_revenue AS STRING) AS total_revenue_raw,
    CAST(total_sales AS STRING) AS total_sales_raw,
    CAST(completed_count AS STRING) AS completed_count_raw,
    CAST(cancel_count AS STRING) AS cancel_count_raw,
    CAST(`加购_count` AS STRING) AS cart_count_raw,
    CAST(`收藏_count` AS STRING) AS favorite_count_raw,
    CAST(`浏览_count` AS STRING) AS browse_count_raw,
    CAST(`点击_count` AS STRING) AS click_count_raw,
    CAST(conversion_rate AS STRING) AS conversion_rate_raw,
    CAST(avg_review_score AS STRING) AS avg_review_score_raw,
    CAST(popularity_score AS STRING) AS popularity_score_raw,
    CAST(_corrupt_record AS STRING) AS corrupt_record,
    CAST(_source_file AS STRING) AS source_file,
    TRY_CAST(_ingested_at AS TIMESTAMP) AS ingested_at
FROM raw_product_features_raw;
