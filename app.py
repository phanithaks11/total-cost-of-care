import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from databricks.sdk import WorkspaceClient

CATALOG = "phanitha_test_catalog"
SCHEMA = "tcoc_gold"

PRIMARY = "#0C2340"
ACCENT  = "#00897B"
ACCENT2 = "#1565C0"
SURFACE = "#F7F9FC"
TEXT_MUTED = "#64748B"
SUCCESS = "#16A34A"
WARNING = "#F59E0B"
DANGER  = "#DC2626"

PALETTE = [ACCENT, ACCENT2, "#7C3AED", "#E11D48", WARNING, "#0891B2", "#65A30D", "#C2410C"]

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", color=PRIMARY),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(showgrid=False),
    yaxis=dict(gridcolor="#E2E8F0", gridwidth=1),
    colorway=PALETTE,
    hoverlabel=dict(bgcolor="white", font_size=13, font_color=PRIMARY),
)

st.set_page_config(
    page_title="Luminos Health \u2013 Total Cost of Care",
    page_icon="\U0001f3e5",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ──────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.stApp { background: #F7F9FC; }
section[data-testid="stSidebar"] { background: #0C2340; }
section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
section[data-testid="stSidebar"] .stMultiSelect label { color: #94A3B8 !important; font-weight: 500; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12); }
.hero { background: linear-gradient(135deg, #0C2340 0%, #1565C0 100%); border-radius: 12px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; }
.hero h1 { color: white; font-size: 2rem; font-weight: 700; margin: 0 0 0.25rem 0; }
.hero p  { color: #94A3B8; font-size: 0.95rem; margin: 0; }
.hero .badge { display: inline-block; background: rgba(0,137,123,0.25); color: #5EEAD4; font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.7rem; border-radius: 999px; margin-top: 0.5rem; letter-spacing: 0.03em; }
.kpi-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.kpi-card { flex: 1 1 140px; background: white; border-radius: 10px; padding: 1.2rem 1.4rem; border-left: 4px solid #00897B; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.kpi-card.blue   { border-left-color: #1565C0; }
.kpi-card.purple { border-left-color: #7C3AED; }
.kpi-card.red    { border-left-color: #DC2626; }
.kpi-card.amber  { border-left-color: #F59E0B; }
.kpi-card .label { font-size: 0.75rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem; }
.kpi-card .value { font-size: 1.55rem; font-weight: 700; color: #0C2340; line-height: 1.1; }
.section-card { background: white; border-radius: 12px; padding: 1.5rem 1.75rem 1.25rem; margin-bottom: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.section-card h3 { color: #0C2340; font-size: 1.1rem; font-weight: 600; margin: 0 0 0.2rem 0; }
.section-card .subtitle { color: #64748B; font-size: 0.82rem; margin-bottom: 1rem; }
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.footer { text-align: center; color: #94A3B8; font-size: 0.78rem; padding: 2rem 0 1rem; border-top: 1px solid #E2E8F0; margin-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ── Data layer ──────────────────────────────────────────────────────

@st.cache_resource
def _client():
    return WorkspaceClient()


def _warehouse_id():
    wid = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if wid:
        return wid
    w = _client()
    for wh in w.warehouses.list():
        if wh.state and wh.state.value == "RUNNING":
            return wh.id
    for wh in w.warehouses.list():
        return wh.id
    return None


@st.cache_data(ttl=300)
def query(sql_text: str) -> pd.DataFrame:
    w = _client()
    wid = _warehouse_id()
    if not wid:
        st.error("No SQL warehouse available. Set DATABRICKS_WAREHOUSE_ID.")
        return pd.DataFrame()
    resp = w.statement_execution.execute_statement(
        warehouse_id=wid,
        statement=sql_text,
        wait_timeout="30s",
    )
    if resp.status.state.value == "FAILED":
        st.error(f"Query failed: {resp.status.error.message}")
        return pd.DataFrame()
    cols = [c.name for c in resp.manifest.schema.columns]
    rows = resp.result.data_array if resp.result and resp.result.data_array else []
    return pd.DataFrame(rows, columns=cols)


def _style_fig(fig, height=400):
    """Apply the unified Luminos theme to any Plotly figure."""
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    return fig


# ── Sidebar ─────────────────────────────────────────────────

st.sidebar.markdown("### \U0001f3e5 Luminos Health")
st.sidebar.caption("Total Cost of Care Analytics")
st.sidebar.divider()
st.sidebar.markdown("###### FILTERS")


@st.cache_data(ttl=600)
def load_filter_options():
    return query(f"""
        SELECT DISTINCT line_of_business, plan_type, member_state
        FROM {CATALOG}.{SCHEMA}.tcoc_pmpm_trends
        ORDER BY 1, 2, 3
    """)


filter_df = load_filter_options()
lob_opts = sorted(filter_df["line_of_business"].dropna().unique()) if not filter_df.empty else []
plan_opts = sorted(filter_df["plan_type"].dropna().unique()) if not filter_df.empty else []
state_opts = sorted(filter_df["member_state"].dropna().unique()) if not filter_df.empty else []

selected_lob = st.sidebar.multiselect("Line of Business", lob_opts, default=lob_opts)
selected_plan = st.sidebar.multiselect("Plan Type", plan_opts, default=plan_opts)
selected_state = st.sidebar.multiselect("State", state_opts, default=state_opts)

st.sidebar.divider()
st.sidebar.caption("Powered by Databricks")


def where_clause(has_plan_type=True, has_member_state=True):
    parts = []
    if selected_lob:
        vals = ", ".join(f"'{v}'" for v in selected_lob)
        parts.append(f"line_of_business IN ({vals})")
    if has_plan_type and selected_plan:
        vals = ", ".join(f"'{v}'" for v in selected_plan)
        parts.append(f"plan_type IN ({vals})")
    if has_member_state and selected_state:
        vals = ", ".join(f"'{v}'" for v in selected_state)
        parts.append(f"member_state IN ({vals})")
    return " AND ".join(parts) if parts else "1=1"


# ── Header ──────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
    <h1>Total Cost of Care</h1>
    <p>Real-time population health analytics across all lines of business</p>
    <span class="badge">\u26A1 LIVE &mdash; auto-refreshes every 5 min</span>
</div>
""", unsafe_allow_html=True)

# ── Executive KPIs ──────────────────────────────────────────────────

kpi_df = query(f"SELECT * FROM {CATALOG}.{SCHEMA}.tcoc_executive_kpis")

if not kpi_df.empty:
    r = kpi_df.iloc[0]
    kpi_data = [
        ("Total Members",    f'{int(float(r.get("total_members", 0))):,}',  ""),
        ("Total Paid",       f'${float(r.get("total_paid", 0)):,.0f}',      "blue"),
        ("PMPM",             f'${float(r.get("overall_pmpm", 0)):,.2f}',    ""),
        ("Claims",           f'{int(float(r.get("total_claims", 0))):,}',   "purple"),
        ("Denial Rate",      f'{float(r.get("denial_rate_pct", 0)):.1f}%',  "red"),
        ("Network Leakage",  f'{float(r.get("network_leakage_pct", 0)):.1f}%', "amber"),
    ]
    cards_html = '<div class="kpi-row">' + "".join(
        f'<div class="kpi-card {cls}"><div class="label">{lbl}</div><div class="value">{val}</div></div>'
        for lbl, val, cls in kpi_data
    ) + '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

# ── PMPM Trends ─────────────────────────────────────────────────────

st.markdown('<div class="section-card"><h3>PMPM Trends</h3><div class="subtitle">Monthly per-member-per-month cost by line of business</div></div>', unsafe_allow_html=True)

wc = where_clause()
trends_df = query(f"""
    SELECT report_month, line_of_business,
           SUM(total_paid) / NULLIF(SUM(active_members), 0) AS pmpm,
           SUM(active_members) AS members,
           SUM(claim_count) AS claims
    FROM {CATALOG}.{SCHEMA}.tcoc_pmpm_trends
    WHERE {wc}
    GROUP BY report_month, line_of_business
    ORDER BY report_month
""")

if not trends_df.empty:
    trends_df["pmpm"] = pd.to_numeric(trends_df["pmpm"], errors="coerce")
    trends_df["report_month"] = pd.to_datetime(trends_df["report_month"], errors="coerce")
    fig = px.line(
        trends_df, x="report_month", y="pmpm", color="line_of_business",
        labels={"report_month": "Month", "pmpm": "PMPM ($)", "line_of_business": "LOB"},
    )
    fig.update_traces(line=dict(width=2.5))
    _style_fig(fig, 420)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No trend data for selected filters.")

# ── Two-column: Service Categories + Geography ─────────────────────

col_left, col_right = st.columns(2, gap="large")

with col_left:
    st.markdown('<div class="section-card"><h3>Cost by Service Category</h3><div class="subtitle">Total paid grouped by procedure type</div></div>', unsafe_allow_html=True)
    svc_df = query(f"""
        SELECT procedure_category,
               SUM(total_paid) AS total_paid,
               SUM(claim_count) AS claims
        FROM {CATALOG}.{SCHEMA}.tcoc_service_category_costs
        WHERE {where_clause(has_member_state=False)}
        GROUP BY procedure_category
        ORDER BY total_paid DESC
    """)
    if not svc_df.empty:
        svc_df["total_paid"] = pd.to_numeric(svc_df["total_paid"], errors="coerce")
        fig2 = px.bar(
            svc_df, x="total_paid", y="procedure_category", orientation="h",
            labels={"procedure_category": "", "total_paid": "Total Paid ($)"},
            color_discrete_sequence=[ACCENT],
        )
        fig2.update_traces(marker=dict(cornerradius=4))
        _style_fig(fig2, 400)
        fig2.update_layout(yaxis=dict(categoryorder="total ascending", gridcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.markdown('<div class="section-card"><h3>PMPM by State</h3><div class="subtitle">Geographic cost variation</div></div>', unsafe_allow_html=True)
    geo_df = query(f"""
        SELECT member_state,
               SUM(total_paid) / NULLIF(SUM(active_members), 0) AS pmpm
        FROM {CATALOG}.{SCHEMA}.tcoc_geographic_analysis
        WHERE {wc}
        GROUP BY member_state
        ORDER BY pmpm DESC
    """)
    if not geo_df.empty:
        geo_df["pmpm"] = pd.to_numeric(geo_df["pmpm"], errors="coerce")
        fig3 = px.bar(
            geo_df, x="member_state", y="pmpm",
            labels={"member_state": "State", "pmpm": "PMPM ($)"},
            color="pmpm",
            color_continuous_scale=[[0, "#5EEAD4"], [0.5, ACCENT], [1, DANGER]],
        )
        fig3.update_traces(marker=dict(cornerradius=4))
        _style_fig(fig3, 400)
        st.plotly_chart(fig3, use_container_width=True)


# ── Denial Rate & Network Leakage by LOB ───────────────────────────

st.markdown('<div class="section-card"><h3>Denial Rate & Network Leakage by LOB</h3><div class="subtitle">Claims denied and out-of-network spend as percentage of total</div></div>', unsafe_allow_html=True)

dn_df = query(f"""
    SELECT line_of_business,
           SUM(denied_count) * 100.0 / NULLIF(SUM(claim_count), 0) AS denial_rate,
           SUM(oon_paid) * 100.0 / NULLIF(SUM(total_paid), 0) AS network_leakage
    FROM {CATALOG}.{SCHEMA}.tcoc_pmpm_trends
    WHERE {wc}
    GROUP BY line_of_business
""")

if not dn_df.empty:
    dn_df["denial_rate"] = pd.to_numeric(dn_df["denial_rate"], errors="coerce")
    dn_df["network_leakage"] = pd.to_numeric(dn_df["network_leakage"], errors="coerce")
    d1, d2 = st.columns(2, gap="large")
    with d1:
        fig4 = px.bar(
            dn_df, x="line_of_business", y="denial_rate",
            labels={"line_of_business": "LOB", "denial_rate": "Denial Rate (%)"},
            color_discrete_sequence=[DANGER],
        )
        fig4.update_traces(marker=dict(cornerradius=4))
        _style_fig(fig4, 380)
        fig4.update_layout(title=dict(text="Denial Rate", font=dict(size=14)))
        st.plotly_chart(fig4, use_container_width=True)
    with d2:
        fig5 = px.bar(
            dn_df, x="line_of_business", y="network_leakage",
            labels={"line_of_business": "LOB", "network_leakage": "Network Leakage (%)"},
            color_discrete_sequence=[WARNING],
        )
        fig5.update_traces(marker=dict(cornerradius=4))
        _style_fig(fig5, 380)
        fig5.update_layout(title=dict(text="Network Leakage", font=dict(size=14)))
        st.plotly_chart(fig5, use_container_width=True)


# ── Provider Analysis ──────────────────────────────────────────────

st.markdown('<div class="section-card"><h3>Top Providers by Total Paid</h3><div class="subtitle">Top 20 providers ranked by total reimbursement</div></div>', unsafe_allow_html=True)

prov_df = query(f"""
    SELECT provider_id, provider_specialty, network_status,
           SUM(total_paid) AS total_paid,
           SUM(total_claims) AS claims,
           SUM(unique_patients) AS patients
    FROM {CATALOG}.{SCHEMA}.tcoc_provider_network_analysis
    WHERE {where_clause(has_plan_type=False, has_member_state=False)}
    GROUP BY provider_id, provider_specialty, network_status
    ORDER BY total_paid DESC
    LIMIT 20
""")

if not prov_df.empty:
    prov_df["total_paid"] = pd.to_numeric(prov_df["total_paid"], errors="coerce")
    prov_df["claims"] = pd.to_numeric(prov_df["claims"], errors="coerce")
    prov_df["patients"] = pd.to_numeric(prov_df["patients"], errors="coerce")
    st.dataframe(
        prov_df.style.format({"total_paid": "${:,.0f}", "claims": "{:,.0f}", "patients": "{:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )

# ── 6-Month Cost Forecast ──────────────────────────────────────────

st.markdown('<div class="section-card"><h3>\U0001f4c8 6-Month Cost Forecast (Jan\u2013Jun 2026)</h3><div class="subtitle">LightGBM model trained on historical claims \u2014 registered in Unity Catalog</div></div>', unsafe_allow_html=True)

forecast_wc = where_clause()
forecast_df = query(f"""
    SELECT forecast_month, line_of_business, plan_type, member_state,
           predicted_paid, predicted_pmpm, lower_bound, upper_bound, model_version
    FROM {CATALOG}.{SCHEMA}.tcoc_cost_forecast
    WHERE {forecast_wc}
""")

if not forecast_df.empty:
    for col in ["predicted_paid", "predicted_pmpm", "lower_bound", "upper_bound"]:
        forecast_df[col] = pd.to_numeric(forecast_df[col], errors="coerce")
    forecast_df["forecast_month"] = pd.to_datetime(forecast_df["forecast_month"], errors="coerce")

    total_projected = forecast_df["predicted_paid"].sum()
    avg_pmpm = forecast_df["predicted_pmpm"].mean()
    model_ver = forecast_df["model_version"].iloc[0]
    fc_cards = f"""
    <div class="kpi-row">
        <div class="kpi-card blue"><div class="label">Projected 6-Month Total</div><div class="value">${total_projected:,.0f}</div></div>
        <div class="kpi-card"><div class="label">Avg Forecast PMPM</div><div class="value">${avg_pmpm:,.2f}</div></div>
        <div class="kpi-card purple"><div class="label">Model Version</div><div class="value">{model_ver}</div></div>
    </div>
    """
    st.markdown(fc_cards, unsafe_allow_html=True)

    # Actual vs Forecast line chart
    actual_df = query(f"""
        SELECT report_month AS month, line_of_business,
               SUM(total_paid) / NULLIF(SUM(active_members), 0) AS pmpm,
               'Actual' AS series_type
        FROM {CATALOG}.{SCHEMA}.tcoc_pmpm_trends
        WHERE {forecast_wc}
        GROUP BY report_month, line_of_business
        UNION ALL
        SELECT forecast_month AS month, line_of_business,
               AVG(predicted_pmpm) AS pmpm,
               'Forecast' AS series_type
        FROM {CATALOG}.{SCHEMA}.tcoc_cost_forecast
        WHERE {forecast_wc}
        GROUP BY forecast_month, line_of_business
        ORDER BY month
    """)
    if not actual_df.empty:
        actual_df["pmpm"] = pd.to_numeric(actual_df["pmpm"], errors="coerce")
        actual_df["month"] = pd.to_datetime(actual_df["month"], errors="coerce")
        fig_fc = px.line(
            actual_df, x="month", y="pmpm", color="line_of_business",
            line_dash="series_type",
            labels={"month": "Month", "pmpm": "PMPM ($)", "line_of_business": "LOB", "series_type": "Type"},
        )
        fig_fc.update_traces(line=dict(width=2.5))
        _style_fig(fig_fc, 450)
        fig_fc.update_layout(title=dict(text="Actual vs Forecast PMPM by LOB", font=dict(size=14, color=PRIMARY)))
        st.plotly_chart(fig_fc, use_container_width=True)

    # Forecast by LOB bar + state table
    fl, fr = st.columns(2, gap="large")
    with fl:
        lob_fc = forecast_df.groupby("line_of_business", as_index=False)["predicted_paid"].sum()
        fig_lob = px.bar(
            lob_fc, x="line_of_business", y="predicted_paid",
            labels={"line_of_business": "LOB", "predicted_paid": "Projected Total ($)"},
        )
        fig_lob.update_traces(marker=dict(cornerradius=4))
        _style_fig(fig_lob, 400)
        fig_lob.update_layout(title=dict(text="Forecasted Cost by LOB", font=dict(size=14)), showlegend=False)
        st.plotly_chart(fig_lob, use_container_width=True)
    with fr:
        state_fc = (
            forecast_df.groupby(["member_state", "line_of_business"], as_index=False)
            .agg(total_predicted=pd.NamedAgg("predicted_paid", "sum"),
                 avg_pmpm=pd.NamedAgg("predicted_pmpm", "mean"),
                 min_lower=pd.NamedAgg("lower_bound", "min"),
                 max_upper=pd.NamedAgg("upper_bound", "max"))
            .sort_values("total_predicted", ascending=False)
        )
        st.dataframe(
            state_fc.style.format({
                "total_predicted": "${:,.0f}",
                "avg_pmpm": "${:,.2f}",
                "min_lower": "${:,.0f}",
                "max_upper": "${:,.0f}",
            }),
            use_container_width=True, hide_index=True, height=400,
        )
else:
    st.info("No forecast data available. Run the cost forecast model notebook first.")

st.markdown(f"""
<div class="footer">
    Luminos Health &bull; Total Cost of Care &bull; Data source: <code>{CATALOG}.{SCHEMA}</code> &bull; Auto-refreshes every 5 min<br/>
    Powered by <strong>Databricks</strong>
</div>
""", unsafe_allow_html=True)
