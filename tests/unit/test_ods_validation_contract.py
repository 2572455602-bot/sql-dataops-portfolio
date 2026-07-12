from pathlib import Path


ODS_SQL = (Path(__file__).resolve().parents[2] / "sql" / "10_ods.sql").read_text(encoding="utf-8")
QUALITY_SQL = (Path(__file__).resolve().parents[2] / "sql" / "90_quality.sql").read_text(encoding="utf-8")


def test_every_required_typed_field_has_an_explicit_parse_rejection():
    required_parse_rules = [
        # users
        ("age_raw", "INT", "invalid_age_parse"),
        ("registration_date_raw", "TIMESTAMP", "invalid_registration_date"),
        ("account_balance_raw", "DECIMAL(18,2)", "invalid_account_balance_parse"),
        ("credit_score_raw", "INT", "invalid_credit_score_parse"),
        # products
        ("price_raw", "DECIMAL(18,2)", "invalid_price_parse"),
        ("sales_count_raw", "BIGINT", "invalid_sales_count_parse"),
        # orders
        ("quantity_raw", "INT", "invalid_quantity_parse"),
        ("order_date_raw", "TIMESTAMP", "invalid_order_date"),
        ("unit_price_raw", "DECIMAL(18,2)", "invalid_unit_price_parse"),
        ("total_amount_raw", "DECIMAL(18,2)", "invalid_total_amount_parse"),
        ("discount_raw", "DECIMAL(18,2)", "invalid_discount_parse"),
        ("actual_payment_raw", "DECIMAL(18,2)", "invalid_actual_payment_parse"),
        # behaviors
        ("behavior_time_raw", "TIMESTAMP", "invalid_behavior_time"),
        ("duration_seconds_raw", "INT", "invalid_duration_parse"),
        # user feature snapshot
        ("total_spent_raw", "DECIMAL(18,2)", "invalid_total_spent_parse"),
        ("order_count_raw", "DECIMAL(20,6)", "invalid_order_count_parse"),
        ("completed_orders_raw", "DECIMAL(20,6)", "invalid_completed_orders_parse"),
        ("avg_order_amount_raw", "DECIMAL(18,4)", "invalid_avg_order_amount_parse"),
        ("browse_count_raw", "DECIMAL(20,6)", "invalid_browse_count_parse"),
        ("click_count_raw", "DECIMAL(20,6)", "invalid_click_count_parse"),
        ("favorite_count_raw", "DECIMAL(20,6)", "invalid_favorite_count_parse"),
        ("cart_count_raw", "DECIMAL(20,6)", "invalid_cart_count_parse"),
        ("days_since_last_order_raw", "INT", "invalid_days_since_last_order_parse"),
        ("order_frequency_raw", "DOUBLE", "invalid_order_frequency_parse"),
        ("repurchase_indicator_raw", "INT", "invalid_repurchase_indicator_parse"),
        ("purchase_intent_raw", "DOUBLE", "invalid_purchase_intent_parse"),
        ("member_level_score_raw", "INT", "invalid_member_level_score_parse"),
        # product feature snapshot
        ("total_revenue_raw", "DECIMAL(18,2)", "invalid_total_revenue_parse"),
        ("total_sales_raw", "BIGINT", "invalid_total_sales_parse"),
        ("completed_count_raw", "BIGINT", "invalid_completed_count_parse"),
        ("cancel_count_raw", "BIGINT", "invalid_cancel_count_parse"),
        ("conversion_rate_raw", "DOUBLE", "invalid_conversion_rate_parse"),
        ("popularity_score_raw", "DOUBLE", "invalid_popularity_score_parse"),
    ]

    for raw_field, cast_type, reason in required_parse_rules:
        expected = (
            f"CASE WHEN TRY_CAST(TRIM({raw_field}) AS {cast_type}) IS NULL "
            f"THEN '{reason}' END"
        )
        assert expected in ODS_SQL, raw_field

    # These count fields exist in both feature tables and therefore require a
    # parse guard in each table, not merely somewhere in the SQL bundle.
    for shared_field in ("browse_count_raw", "click_count_raw", "favorite_count_raw", "cart_count_raw"):
        assert ODS_SQL.count(f"CASE WHEN TRY_CAST(TRIM({shared_field}) AS DECIMAL(20,6)) IS NULL") == 1


def test_feature_count_contract_accepts_integral_decimals_but_rejects_fractions():
    for raw_field, reason in (
        ("order_count_raw", "invalid_order_count"),
        ("completed_orders_raw", "invalid_completed_orders"),
        ("browse_count_raw", "invalid_browse_count"),
        ("click_count_raw", "invalid_click_count"),
        ("favorite_count_raw", "invalid_favorite_count"),
        ("cart_count_raw", "invalid_cart_count"),
    ):
        decimal_value = f"TRY_CAST(TRIM({raw_field}) AS DECIMAL(20,6))"
        assert f"{decimal_value} <> FLOOR({decimal_value}) THEN '{reason}' END" in ODS_SQL


def test_required_text_fields_are_null_safe_and_nullable_fields_stay_nullable():
    required_text_guards = {
        "user_id_raw": 4,
        "product_id_raw": 4,
        "order_id_raw": 1,
        "behavior_id_raw": 1,
        "gender_raw": 1,
        "province_raw": 1,
        "city_raw": 1,
        "member_level_raw": 1,
        "product_name_raw": 1,
        "category_raw": 1,
        "brand_raw": 1,
        "order_status_raw": 1,
        "payment_method_raw": 1,
        "behavior_type_raw": 1,
        "consumption_level_raw": 1,
    }
    for raw_field, expected_count in required_text_guards.items():
        guard = f"TRIM(COALESCE({raw_field},'')) = ''"
        assert ODS_SQL.count(guard) == expected_count, raw_field

    nullable_parse_rules = [
        ("delivery_date_raw", "TIMESTAMP"),
        ("receive_date_raw", "TIMESTAMP"),
        ("review_score_raw", "INT"),
        ("avg_review_score_raw", "DOUBLE"),
    ]
    for raw_field, cast_type in nullable_parse_rules:
        assert f"TRIM(COALESCE({raw_field},'')) <> ''" in ODS_SQL
        assert f"TRY_CAST(TRIM({raw_field}) AS {cast_type}) IS NULL" in ODS_SQL


def test_non_temporal_quarantine_is_an_independent_critical_gate():
    assert "TRIM(COALESCE(rejection_reasons,'')) <> 'event_before_registration'" in QUALITY_SQL
    assert "UNION ALL SELECT 'non_temporal_quarantine_empty'" in QUALITY_SQL
    assert "CASE WHEN non_temporal_quarantine=0 THEN 'pass' ELSE 'fail' END" in QUALITY_SQL
    assert "CAST(non_temporal_quarantine AS STRING), '0', 'critical'" in QUALITY_SQL
