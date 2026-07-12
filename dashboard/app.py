"""Recruiter-facing Streamlit dashboard for the SQL/DataOps portfolio."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

try:
    from dashboard.data_loader import DashboardData, load_dashboard_data, publication_fingerprint
except ModuleNotFoundError:
    from data_loader import DashboardData, load_dashboard_data, publication_fingerprint


BLUE = "#245EEA"
NAVY = "#12263F"
AMBER = "#B8660B"
GREEN = "#18794E"
RED = "#B42318"

st.set_page_config(
    page_title="SQL DataOps Operations",
    page_icon="D",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner="Loading the latest published aggregates…")
def _load_cached(path: str | None, fingerprint: str) -> DashboardData:
    del fingerprint
    return load_dashboard_data(path)


def _first(frame: pd.DataFrame, field: str, fallback: Any = None) -> Any:
    if frame.empty or field not in frame.columns:
        return fallback
    values = frame[field].dropna()
    return values.iloc[0] if not values.empty else fallback


def _count(value: Any) -> str:
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _sample_amount(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"
    if numeric < 0:
        return "—"
    if numeric >= 1_000_000:
        return f"{numeric / 1_000_000:.2f}M"
    if numeric >= 1_000:
        return f"{numeric / 1_000:.1f}K"
    return f"{numeric:,.2f}"


def _rate(value: Any) -> str:
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return "—"


def _duration(value: Any) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return "—"
    if seconds >= 60:
        return f"{seconds / 60:.1f} min"
    return f"{seconds:.1f}s"


def _quality_counts(bundle: DashboardData, quality: pd.DataFrame) -> tuple[int, int, int, int]:
    manifest_quality = bundle.manifest.get("quality", {})
    if isinstance(manifest_quality, dict):
        total = int(manifest_quality.get("total_checks", 0) or 0)
        passed = int(manifest_quality.get("passed_checks", 0) or 0)
        warnings = int(manifest_quality.get("warning_checks", 0) or 0)
        failed = int(manifest_quality.get("failed_checks", 0) or 0)
        if total:
            return total, passed, warnings, failed
    if quality.empty or "check_status" not in quality.columns:
        return 0, 0, 0, 0
    statuses = quality["check_status"].astype(str).str.lower()
    passed = int((statuses == "pass").sum())
    warnings = int((statuses == "warn").sum())
    failed = int((statuses == "fail").sum())
    return len(quality), passed, warnings, failed


def _date_window(bundle: DashboardData) -> str:
    profile = bundle.manifest.get("data_profile", {})
    if not isinstance(profile, dict):
        return "—"
    start = profile.get("min_event_date")
    end = profile.get("max_event_date")
    return f"{start} → {end}" if start and end else "—"


def _header(bundle: DashboardData, kpis: pd.DataFrame) -> None:
    mode = str(bundle.manifest.get("data_mode") or _first(kpis, "data_mode", "UNKNOWN")).upper()
    source = str(bundle.manifest.get("source_status") or _first(kpis, "source_status", "UNKNOWN")).upper()
    st.markdown(
        """
        <style>
        .block-container {max-width: 1420px; padding-top: 2rem; padding-bottom: 3rem;}
        h1, h2, h3 {color: #101828; letter-spacing: -0.025em;}
        .source-badge {display:inline-flex; border:1px solid #D6A150; background:#FFF7E8;
          color:#7D3F06; border-radius:999px; padding:5px 10px; font-size:.72rem;
          font-weight:800; letter-spacing:.08em; margin-bottom:.75rem;}
        .compact-note {color:#667085; margin-top:-.35rem; margin-bottom:1.25rem;}
        [data-testid="stMetric"] {border:1px solid #E4E7EC; border-radius:14px; padding:14px 16px;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<span class="source-badge">{mode} DATA · SOURCE {source}</span>', unsafe_allow_html=True)
    st.title("SQL DataOps Operations")
    st.markdown(
        '<p class="compact-note">Published snapshot, quality gate, business aggregates, and run evidence.</p>',
        unsafe_allow_html=True,
    )


def _run_health(bundle: DashboardData, quality: pd.DataFrame) -> None:
    st.subheader("Run health")
    profile = bundle.manifest.get("data_profile", {})
    if not isinstance(profile, dict):
        profile = {}
    manifest_quality = bundle.manifest.get("quality", {})
    if not isinstance(manifest_quality, dict):
        manifest_quality = {}
    total, passed, warnings, failed = _quality_counts(bundle, quality)
    published = "yes" if bundle.manifest.get("published") is True else "no"
    quality_status = str(manifest_quality.get("status", "unknown")).upper()
    columns = st.columns(6)
    values = (
        ("Published", published),
        ("Quality gate", quality_status),
        ("Checks", f"{passed}/{total} pass"),
        ("Warnings", str(warnings)),
        ("Quarantined rows", _count(profile.get("quarantine_rows"))),
        ("Runtime", _duration(bundle.manifest.get("duration_seconds"))),
    )
    for column, (label, value) in zip(columns, values):
        column.metric(label, value)
    st.caption(
        f"Run `{bundle.manifest.get('run_id', 'unknown')}` · "
        f"Spark {bundle.manifest.get('spark_version', 'unknown')} · "
        f"Data window {_date_window(bundle)}"
    )
    if failed:
        st.error("This run has failed checks. The current published dashboard should not be replaced.")
    elif warnings:
        st.warning("Warnings are visible and audited; blocking checks passed, so the published ADS snapshot is usable.")
    else:
        st.success("All checks passed for the published ADS snapshot.")


def _kpis(kpis: pd.DataFrame) -> None:
    st.subheader("Business snapshot")
    columns = st.columns(6)
    values = (
        ("Valid orders", "total_orders", _count),
        ("Completed orders", "completed_orders", _count),
        ("Sample amount", "completed_gmv", _sample_amount),
        ("Completed customers", "completed_customers", _count),
        ("Completion rate", "completion_rate", _rate),
        ("Behavior events", "behavior_events", _count),
    )
    for column, (label, field, formatter) in zip(columns, values):
        column.metric(label, formatter(_first(kpis, field)))


def _daily_chart(daily: pd.DataFrame) -> None:
    st.subheader("Sample amount trend")
    if daily.empty or not {"order_date", "completed_gmv", "completed_orders"}.issubset(daily.columns):
        st.info("Daily aggregate is unavailable.")
        return
    plot = daily.dropna(subset=["order_date"]).copy()
    base = alt.Chart(plot).encode(x=alt.X("order_date:T", title=None, axis=alt.Axis(format="%b %d")))
    revenue = base.mark_area(color=BLUE, opacity=0.18, line={"color": BLUE, "strokeWidth": 2}).encode(
        y=alt.Y("completed_gmv:Q", title="Sample amount"),
        tooltip=[
            alt.Tooltip("order_date:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip("completed_gmv:Q", title="Sample amount", format=",.2f"),
            alt.Tooltip("completed_orders:Q", title="Completed orders", format=","),
        ],
    )
    st.altair_chart(revenue.properties(height=300), use_container_width=True)


def _status_chart(status: pd.DataFrame) -> None:
    st.subheader("Order lifecycle")
    if status.empty or not {"source_order_status", "order_count"}.issubset(status.columns):
        st.info("Order-status aggregate is unavailable.")
        return
    plot = status.sort_values("status_order") if "status_order" in status.columns else status
    chart = alt.Chart(plot).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=NAVY).encode(
        x=alt.X("source_order_status:N", title=None, sort=plot["source_order_status"].tolist()),
        y=alt.Y("order_count:Q", title="Orders"),
        tooltip=["source_order_status:N", alt.Tooltip("order_count:Q", format=",")],
    )
    st.altair_chart(chart.properties(height=300), use_container_width=True)


def _category_chart(categories: pd.DataFrame) -> None:
    st.subheader("Sample amount by category")
    if categories.empty or not {"category", "completed_gmv"}.issubset(categories.columns):
        st.info("Category aggregate is unavailable.")
        return
    plot = categories.nlargest(10, "completed_gmv").sort_values("completed_gmv")
    chart = alt.Chart(plot).mark_bar(color=BLUE, cornerRadiusEnd=4).encode(
        y=alt.Y("category:N", title=None, sort=plot["category"].tolist()),
        x=alt.X("completed_gmv:Q", title="Sample amount"),
        tooltip=["category:N", alt.Tooltip("completed_gmv:Q", format=",.2f")],
    )
    st.altair_chart(chart.properties(height=330), use_container_width=True)


def _behavior_chart(hourly: pd.DataFrame) -> None:
    st.subheader("Behavior mix by hour")
    fields = [field for field in ("browse_events", "click_events", "favorite_events", "cart_events") if field in hourly.columns]
    if hourly.empty or "behavior_hour" not in hourly.columns or not fields:
        st.info("Hourly behavior aggregate is unavailable.")
        return
    plot = hourly[["behavior_hour", *fields]].melt("behavior_hour", var_name="behavior", value_name="events")
    chart = alt.Chart(plot).mark_bar().encode(
        x=alt.X("behavior_hour:O", title="Hour"),
        y=alt.Y("events:Q", title="Events", stack=True),
        color=alt.Color("behavior:N", title=None, scale=alt.Scale(range=[BLUE, NAVY, AMBER, GREEN])),
        tooltip=["behavior:N", "behavior_hour:O", alt.Tooltip("events:Q", format=",")],
    )
    st.altair_chart(chart.properties(height=300), use_container_width=True)


def _segment_chart(segments: pd.DataFrame) -> None:
    st.subheader("Customer segments")
    if segments.empty or not {"customer_segment", "user_count"}.issubset(segments.columns):
        st.info("Customer segment aggregate is unavailable.")
        return
    plot = segments.sort_values("segment_order") if "segment_order" in segments.columns else segments
    chart = alt.Chart(plot).mark_bar(color=AMBER, cornerRadiusEnd=4).encode(
        y=alt.Y("customer_segment:N", title=None, sort=plot["customer_segment"].tolist()),
        x=alt.X("user_count:Q", title="Users"),
        tooltip=["customer_segment:N", alt.Tooltip("user_count:Q", format=","), alt.Tooltip("user_share:Q", format=".1%")],
    )
    st.altair_chart(chart.properties(height=260), use_container_width=True)


def _quality(bundle: DashboardData, quality: pd.DataFrame) -> None:
    st.subheader("Data quality")
    if quality.empty:
        st.warning("Quality extract is unavailable.")
        return
    statuses = quality["check_status"].astype(str).str.lower()
    passed = int((statuses == "pass").sum())
    warnings = int((statuses == "warn").sum())
    failed = int((statuses == "fail").sum())
    st.markdown(f"**{passed} passed · {warnings} warnings · {failed} failed**")
    columns = [column for column in ("check_name", "check_status", "observed_value", "severity") if column in quality.columns]
    st.dataframe(quality[columns], hide_index=True, use_container_width=True)
    with st.expander("Run evidence"):
        st.json(
            {
                "run_id": bundle.manifest.get("run_id"),
                "source_status": bundle.manifest.get("source_status"),
                "published": bundle.manifest.get("published"),
                "raw_data_in_public_exports": False,
                "quarantined_rows": bundle.manifest.get("data_profile", {}).get("quarantine_rows"),
            }
        )


def _operating_model() -> None:
    st.subheader("Long-running DataOps model")
    st.markdown(
        "The current portfolio publishes a validated batch snapshot. "
        "For daily operation, the same contract extends to partitioned incremental drops, "
        "watermark tracking, quality-gated publishing, and rollback-safe BI releases."
    )
    st.table(
        pd.DataFrame(
            [
                {
                    "Layer": "Ingest",
                    "Long-running behavior": "Land new files by run date, keep immutable raw history.",
                    "Why it matters": "Replays and source audits stay possible.",
                },
                {
                    "Layer": "Build",
                    "Long-running behavior": "Process only new or backfilled partitions, then reconcile to historical facts.",
                    "Why it matters": "Daily runs stay fast without losing correctness.",
                },
                {
                    "Layer": "Quality gate",
                    "Long-running behavior": "Block schema, enum, null-ID, timestamp, reconciliation, and ADS-output failures.",
                    "Why it matters": "Bad batches cannot replace the last good dashboard.",
                },
                {
                    "Layer": "Publish",
                    "Long-running behavior": "Write candidate outputs first, then atomically publish current only after checks pass.",
                    "Why it matters": "Consumers always see a complete version.",
                },
                {
                    "Layer": "Operate",
                    "Long-running behavior": "Keep manifest history with run ID, row counts, warnings, SQL version, and runtime.",
                    "Why it matters": "Incidents can be explained and reproduced.",
                },
            ]
        )
    )
    st.code(
        "make incremental DATA_DIR=/daily/drop RUN_DATE=2026-07-12\n"
        "# future production extension: partitioned build + same quality gate + atomic publish",
        language="bash",
    )


def main() -> None:
    bundle = _load_cached(None, publication_fingerprint())
    if bundle.errors:
        for error in bundle.errors:
            st.error(error)
    if not bundle.has_business_data:
        st.title("E-commerce SQL + DataOps")
        st.info("No successful aggregate publication is available yet. Run `make demo` or `make full DATA_DIR=…`.")
        return

    kpis = bundle.table("kpis")
    _header(bundle, kpis)
    _run_health(bundle, bundle.table("quality"))
    _kpis(kpis)
    st.divider()
    left, right = st.columns(2)
    with left:
        _daily_chart(bundle.table("daily"))
    with right:
        _status_chart(bundle.table("status"))
    left, right = st.columns(2)
    with left:
        _category_chart(bundle.table("categories"))
    with right:
        _behavior_chart(bundle.table("hourly"))
    _segment_chart(bundle.table("segments"))
    st.divider()
    _quality(bundle, bundle.table("quality"))
    st.divider()
    _operating_model()
    st.caption("Source unverified · Currency unverified · Aggregate outputs only")


main()
