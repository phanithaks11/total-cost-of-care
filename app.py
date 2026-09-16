import os
import streamlit as st
import pandas as pd
import plotly.express as px
from databricks.sdk import WorkspaceClient

CATALOG = "phanitha_test_catalog"
SCHEMA = "tcoc_gold"

st.set_page_config(
    page_title="Luminos Health \u2013 Total Cost of Care",
    page_icon="\U0001f3e5",
    layout="wide",
)

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


# ── Sidebar filters ─────────────────────────────────────────────────

st.sidebar.title("Luminos Health")
st.sidebar.caption("Total Cost of Care")
st.sidebar.divider()


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


def where_clause():
    parts = []
    if selected_lob:
        vals = ", ".join(f"'{v}'" for v in selected_lob)
        parts.append(f"line_of_business IN ({vals})")
    if selected_plan:
        vals = ", ".join(f"'{v}'" for v in selected_plan)
        parts.append(f"plan_type IN ({vals})")
    if selected_state:
        vals = ", ".join(f"'{v}'" for v in selected_state)
        parts.append(f"member_state IN ({vals})")
    return " AND ".join(parts) if parts else "1=1"


# ── Header ──────────────────────────────────────────────────────────

st.title("Total Cost of Care")
st.caption("Real-time analytics powered by Databricks")

# ── Executive KPIs ──────────────────────────────────────────────────

kpi_df = query(f"SELECT * FROM {CATALOG}.{SCHEMA}.tcoc_executive_kpis")

if not kpi_df.empty:
    r = kpi_df.iloc[0]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Members", f"{int(float(r.get('total_members', 0))):,}")
    c2.metric("Total Paid", f"${float(r.get('total_paid', 0)):,.0f}")
    c3.metric("PMPM", f"${float(r.get('overall_pmpm', 0)):,.2f}")
    c4.metric("Claims", f"{int(float(r.get('total_claims', 0))):,}")
    c5.metric("Denial Rate", f"{float(r.get('denial_rate_pct', 0)):.1f}%")
    c6.metric("Network Leakage", f"{float(r.get('network_leakage_pct', 0)):.1f}%")

st.divider()

# ── PMPM Trends ─────────────────────────────────────────────────────

st.subheader("PMPM Trends")

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
        template="plotly_white",
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No trend data for selected filters.")

# ── Two-column: Service Categories + Geography ─────────────────────

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Cost by Service Category")
    svc_df = query(f"""
        SELECT procedure_category,
               SUM(total_paid) AS total_paid,
               SUM(claim_count) AS claims
        FROM {CATALOG}.{SCHEMA}.tcoc_service_category_costs
        WHERE {wc}
        GROUP BY procedure_category
        ORDER BY total_paid DESC
    """)
    if not svc_df.empty:
        svc_df["total_paid"] = pd.to_numeric(svc_df["total_paid"], errors="coerce")
        fig2 = px.bar(
            svc_df, x="procedure_category", y="total_paid",
            labels={"procedure_category": "Category", "total_paid": "Total Paid ($)"},
            template="plotly_white", color="procedure_category",
        )
        fig2.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.subheader("PMPM by State")
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
            template="plotly_white", color="pmpm",
            color_continuous_scale="RdYlGn_r",
        )
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Denial Rate & Network Leakage by LOB ───────────────────────────

st.subheader("Denial Rate & Network Leakage by LOB")

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
    d1, d2 = st.columns(2)
    with d1:
        fig4 = px.bar(
            dn_df, x="line_of_business", y="denial_rate",
            labels={"line_of_business": "LOB", "denial_rate": "Denial Rate (%)"},
            template="plotly_white", color="denial_rate",
            color_continuous_scale="Reds",
        )
        fig4.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)
    with d2:
        fig5 = px.bar(
            dn_df, x="line_of_business", y="network_leakage",
            labels={"line_of_business": "LOB", "network_leakage": "Network Leakage (%)"},
            template="plotly_white", color="network_leakage",
            color_continuous_scale="Oranges",
        )
        fig5.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ── Provider Analysis ──────────────────────────────────────────────

st.subheader("Top Providers by Total Paid")

prov_df = query(f"""
    SELECT provider_id, provider_specialty, network_status,
           SUM(total_paid) AS total_paid,
           SUM(total_claims) AS claims,
           SUM(unique_patients) AS patients
    FROM {CATALOG}.{SCHEMA}.tcoc_provider_network_analysis
    WHERE {wc}
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

st.caption(f"Data source: {CATALOG}.{SCHEMA} | Cached 5 min")
