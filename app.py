import os
import time
import uuid

import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from databricks.sdk import WorkspaceClient

CATALOG = "phanitha_test_catalog"
SCHEMA = os.environ.get("LAKEBASE_SCHEMA", "tcoc_gold")
GENIE_SPACE_ID = "01f1b2b3e3091d65888a5614977260dd"

PGHOST = os.environ.get("PGHOST") or os.environ.get("LAKEBASE_HOST")
PGDATABASE = os.environ.get("PGDATABASE") or os.environ.get("LAKEBASE_DATABASE", "databricks_postgres")
PGUSER = os.environ.get("PGUSER")
PGPORT = int(os.environ.get("PGPORT", "5432"))
# Only use Lakebase when explicitly opted in — the tcoc tables live in Unity Catalog
USE_LAKEBASE = os.environ.get("USE_LAKEBASE", "false").lower() == "true"


def table_ref(table_name: str) -> str:
    if USE_LAKEBASE:
        return f"{SCHEMA}.{table_name}"
    return f"{CATALOG}.{SCHEMA}.{table_name}"


def data_source_label() -> str:
    if USE_LAKEBASE:
        return f"{PGDATABASE}.{SCHEMA}"
    return f"{CATALOG}.{SCHEMA}"

PRIMARY = "#0B1D3A"
ACCENT  = "#4A90D9"
ACCENT2 = "#1E3A5F"
SURFACE = "#F8F9FB"
TEXT_MUTED = "#1A1A1A"
SUCCESS = "#2E8B57"
WARNING = "#D4A017"
DANGER  = "#C0392B"

PALETTE = ["#4A90D9", "#1E3A5F", "#7BAFD4", "#C0392B", "#D4A017", "#2E8B57", "#8E99A4", "#5B6E85"]

PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, sans-serif", color="#0B1D3A"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(showgrid=False, color="#0B1D3A", tickfont=dict(color="#0B1D3A", size=12), titlefont=dict(color="#0B1D3A", size=13)),
    yaxis=dict(gridcolor="#E0E4E8", gridwidth=1, color="#0B1D3A", tickfont=dict(color="#0B1D3A", size=12), titlefont=dict(color="#0B1D3A", size=13)),
    colorway=PALETTE,
    hoverlabel=dict(bgcolor="white", font_size=13, font_color="#0B1D3A", bordercolor="#4A90D9"),
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
.stApp { background: #F8F9FB; color: #0B1D3A; }
section[data-testid="stSidebar"] { background: #0B1D3A; }
section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] .stMultiSelect label { color: #E2E8F0 !important; font-weight: 500; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em; }
section[data-testid="stSidebar"] hr { border-color: rgba(74,144,217,0.25); }
.hero { background: linear-gradient(135deg, #0B1D3A 0%, #1E3A5F 60%, #4A90D9 100%); border-radius: 12px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; }
.hero h1 { color: white; font-size: 2rem; font-weight: 700; margin: 0 0 0.25rem 0; }
.hero p  { color: #CBD5E1; font-size: 0.95rem; margin: 0; }
.kpi-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.kpi-card { flex: 1 1 140px; background: white; border-radius: 10px; padding: 1.2rem 1.4rem; border-left: 4px solid #4A90D9; box-shadow: 0 1px 4px rgba(11,29,58,0.08); }
.kpi-card.blue   { border-left-color: #1E3A5F; }
.kpi-card.purple { border-left-color: #7BAFD4; }
.kpi-card.red    { border-left-color: #C0392B; }
.kpi-card.amber  { border-left-color: #D4A017; }
.kpi-card .label { font-size: 0.75rem; font-weight: 600; color: #0B1D3A; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem; }
.kpi-card .value { font-size: 1.55rem; font-weight: 700; color: #0B1D3A; line-height: 1.1; }
.section-card { background: white; border-radius: 12px; padding: 1.5rem 1.75rem 1.25rem; margin-top: 1.5rem; margin-bottom: 0.5rem; box-shadow: 0 1px 4px rgba(11,29,58,0.06); }
.section-card h3 { color: #0B1D3A; font-size: 1.1rem; font-weight: 600; margin: 0 0 0.2rem 0; }
.section-card .subtitle { color: #1A1A1A; font-size: 0.82rem; margin-bottom: 0.5rem; }
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
[data-testid="stDataFrame"] th { background: #0B1D3A !important; color: #CBD5E1 !important; }
[data-testid="stDataFrame"] td { background: #F8F9FB !important; color: #0B1D3A !important; }
header[data-testid="stHeader"] { background: #F8F9FB; }
[data-testid="stPlotlyChart"] { margin-top: -0.5rem; }
.footer { text-align: center; color: #1A1A1A; font-size: 0.78rem; padding: 2rem 0 1rem; border-top: 1px solid #E0E4E8; margin-top: 2rem; }
.genie-header { background: linear-gradient(135deg, #0B1D3A 0%, #1E3A5F 60%, #4A90D9 100%); border-radius: 12px; padding: 1.5rem 2rem; margin-bottom: 1rem; }
.genie-header h2 { color: white; font-size: 1.4rem; font-weight: 700; margin: 0 0 0.25rem 0; }
.genie-header p { color: #CBD5E1; font-size: 0.88rem; margin: 0; }
[data-testid="stChatMessage"] { background: white; border-radius: 10px; border: 1px solid #E0E4E8; margin-bottom: 0.5rem; padding: 0.75rem 1rem; color: #0B1D3A !important; }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span, [data-testid="stChatMessage"] li, [data-testid="stChatMessage"] div { color: #0B1D3A !important; }
[data-testid="stChatMessage"] strong { color: #0B1D3A !important; }
[data-testid="stChatMessage"] code { color: #0B1D3A !important; }
[data-testid="stChatInput"] input { color: #0B1D3A !important; }
[data-testid="stChatInput"] textarea { color: #0B1D3A !important; }
[data-testid="stMarkdown"] p { color: #0B1D3A; }
[data-testid="stAlert"] p { color: #0B1D3A !important; }
[data-testid="stCaption"] { color: #3D5A80 !important; }
.genie-sql { background: #0B1D3A; color: #CBD5E1; border-radius: 8px; padding: 1rem; font-size: 0.82rem; overflow-x: auto; }
.genie-sql pre { color: #CBD5E1 !important; }
[data-testid="stBaseButton-secondary"] { background: #0B1D3A !important; color: white !important; border: 1px solid #1E3A5F !important; border-radius: 8px !important; }
[data-testid="stBaseButton-secondary"]:hover { background: #1E3A5F !important; color: white !important; }
[data-testid="stBaseButton-secondary"] p { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ── Data layer ──────────────────────────────────────────────────────

@st.cache_resource
def _client():
    return WorkspaceClient()


def _lakebase_connection():
    w = _client()
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[PGDATABASE],
    )
    return psycopg2.connect(
        host=PGHOST,
        database=PGDATABASE,
        user=PGUSER,
        port=PGPORT,
        password=cred.token,
        sslmode="require",
    )


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
    if USE_LAKEBASE:
        try:
            with _lakebase_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_text)
                    if cur.description is None:
                        return pd.DataFrame()
                    rows = cur.fetchall()
                    cols = [col[0] for col in cur.description]
            return pd.DataFrame(rows, columns=cols)
        except Exception as e:
            st.error(f"Lakebase query failed: {e}")
            return pd.DataFrame()

    w = _client()
    wid = _warehouse_id()
    if not wid:
        st.error("No Lakebase connection or SQL warehouse available. Set DATABRICKS_WAREHOUSE_ID.")
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


# ── Genie helpers ────────────────────────────────────────────────────

def genie_start_conversation(question: str) -> tuple:
    """Start a new Genie conversation. Returns (conversation_id, message_id)."""
    w = _client()
    resp = w.api_client.do(
        "POST",
        f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation",
        body={"content": question},
    )
    return resp["conversation_id"], resp["message_id"]


def genie_follow_up(conversation_id: str, question: str) -> str:
    """Send a follow-up message. Returns the new message_id."""
    w = _client()
    resp = w.api_client.do(
        "POST",
        f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages",
        body={"content": question},
    )
    return resp["id"]


def genie_poll_result(conversation_id: str, message_id: str, timeout: int = 90) -> dict:
    """Poll until the Genie message completes. Returns the full message dict."""
    w = _client()
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = w.api_client.do(
            "GET",
            f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages/{message_id}",
        )
        status = r.get("status", "UNKNOWN")
        if status in ("COMPLETED", "FAILED", "QUERY_RESULT_EXPIRED", "CANCELLED"):
            return r
        time.sleep(2)
    return {"status": "TIMEOUT", "attachments": []}


def genie_parse_response(msg: dict) -> list:
    """Parse a Genie message into display-ready parts.
    Returns a list of dicts: {type: 'text'|'sql'|'table'|'error', content: ...}
    """
    parts = []
    status = msg.get("status", "UNKNOWN")
    if status in ("FAILED", "CANCELLED", "TIMEOUT"):
        error_detail = ""
        # Extract error from attachments or top-level error field
        if "error" in msg:
            error_detail = str(msg["error"])
        for att in msg.get("attachments", []):
            if "query" in att and "error" in att["query"]:
                error_detail = str(att["query"]["error"])
            if "text" in att:
                txt = att["text"].get("content", "")
                if txt.strip():
                    error_detail = txt
        detail_msg = f" — {error_detail}" if error_detail else ""
        parts.append({"type": "error", "content": f"Genie returned status: {status}{detail_msg}"})
        return parts

    for att in msg.get("attachments", []):
        if "text" in att:
            txt = att["text"].get("content", "")
            if txt.strip():
                parts.append({"type": "text", "content": txt})
        if "query" in att:
            q = att["query"]
            sql = q.get("query", "")
            desc = q.get("description", "")
            if sql.strip():
                parts.append({"type": "sql", "content": sql, "description": desc})
            columns = q.get("columns", [])
            data = q.get("data", [])
            if columns and data:
                col_names = [c.get("name", f"col_{i}") for i, c in enumerate(columns)]
                df = pd.DataFrame(data, columns=col_names)
                parts.append({"type": "table", "content": df})

    if not parts:
        parts.append({"type": "text", "content": "Genie returned an empty response."})
    return parts


# ── Sidebar ─────────────────────────────────────────────────

st.sidebar.markdown("### \U0001f3e5 Luminos Health")
st.sidebar.caption("Total Cost of Care Analytics")
st.sidebar.divider()
st.sidebar.markdown("###### FILTERS")


@st.cache_data(ttl=600)
def load_filter_options():
    df = query(f"""
        SELECT DISTINCT line_of_business, plan_type, member_state
        FROM {table_ref('tcoc_pmpm_trends')}
        ORDER BY 1, 2, 3
    """)
    if df.empty:
        st.sidebar.warning("Could not load filter options — check data connection.")
    return df


filter_df = load_filter_options()
lob_opts = sorted(filter_df["line_of_business"].dropna().unique().tolist()) if not filter_df.empty else []
plan_opts = sorted(filter_df["plan_type"].dropna().unique().tolist()) if not filter_df.empty else []
state_opts = sorted(filter_df["member_state"].dropna().unique().tolist()) if not filter_df.empty else []

selected_lob = st.sidebar.multiselect("Line of Business", lob_opts, default=lob_opts)
selected_plan = st.sidebar.multiselect("Plan Type", plan_opts, default=plan_opts)
selected_state = st.sidebar.multiselect("State", state_opts, default=state_opts)

st.sidebar.divider()
app_view = st.sidebar.radio("Navigate", ["\U0001f4ca Dashboard", "\U0001f52e Ask Genie"], label_visibility="collapsed")
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


# ── Genie Chat View ──────────────────────────────────────────────────

if "Genie" in app_view:

    st.markdown("""
    <div class="genie-header">
        <h2>\U0001f52e Ask Genie</h2>
        <p>Ask natural-language questions about your Total Cost of Care data</p>
    </div>
    """, unsafe_allow_html=True)

    # Session state
    if "genie_messages" not in st.session_state:
        st.session_state.genie_messages = []
    if "genie_conversation_id" not in st.session_state:
        st.session_state.genie_conversation_id = None

    # Suggested questions
    suggestions = [
        "What is the average PMPM by line of business?",
        "Which state has the highest total cost?",
        "Show me denial rates by plan type",
        "Top 5 most expensive service categories?",
    ]
    if not st.session_state.genie_messages:
        st.markdown("**Try asking:**")
        scols = st.columns(2, gap="small")
        for idx, s in enumerate(suggestions):
            with scols[idx % 2]:
                if st.button(s, key=f"sug_{idx}", use_container_width=True):
                    st.session_state.genie_pending = s
                    st.rerun()

    # Render conversation history
    for msg in st.session_state.genie_messages:
        avatar = "\U0001f464" if msg["role"] == "user" else "\U0001f52e"
        with st.chat_message(msg["role"], avatar=avatar):
            for part in msg.get("parts", []):
                if part["type"] == "text":
                    st.markdown(part["content"])
                elif part["type"] == "sql":
                    if part.get("description"):
                        st.caption(part["description"])
                    st.code(part["content"], language="sql")
                elif part["type"] == "table":
                    st.dataframe(part["content"], use_container_width=True, hide_index=True)
                elif part["type"] == "error":
                    st.error(part["content"])

    # Handle pending question from suggestion buttons
    pending = st.session_state.pop("genie_pending", None)
    user_input = st.chat_input("Ask about total cost of care...")
    question = pending or user_input

    if question:
        # Show user message
        st.session_state.genie_messages.append({"role": "user", "parts": [{"type": "text", "content": question}]})
        with st.chat_message("user", avatar="\U0001f464"):
            st.markdown(question)

        # Call Genie API
        with st.chat_message("assistant", avatar="\U0001f52e"):
            with st.spinner("Genie is thinking..."):
                try:
                    if st.session_state.genie_conversation_id is None:
                        conv_id, msg_id = genie_start_conversation(question)
                        st.session_state.genie_conversation_id = conv_id
                    else:
                        conv_id = st.session_state.genie_conversation_id
                        msg_id = genie_follow_up(conv_id, question)
                    result = genie_poll_result(conv_id, msg_id)
                    parts = genie_parse_response(result)
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    parts = [{"type": "error", "content": f"Genie API error: {e}\n\n```\n{tb}\n```"}]

            for part in parts:
                if part["type"] == "text":
                    st.markdown(part["content"])
                elif part["type"] == "sql":
                    if part.get("description"):
                        st.caption(part["description"])
                    st.code(part["content"], language="sql")
                elif part["type"] == "table":
                    st.dataframe(part["content"], use_container_width=True, hide_index=True)
                elif part["type"] == "error":
                    st.error(part["content"])

            st.session_state.genie_messages.append({"role": "assistant", "parts": parts})

    # Reset button
    if st.session_state.genie_messages:
        if st.button("\U0001f504 New conversation", key="genie_reset"):
            st.session_state.genie_messages = []
            st.session_state.genie_conversation_id = None
            st.rerun()

    st.stop()


# ── Header ──────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
    <h1>Total Cost of Care</h1>
    <p>Real-time population health analytics across all lines of business</p>
</div>
""", unsafe_allow_html=True)

# ── Executive KPIs ──────────────────────────────────────────────────

kpi_df = query(f"SELECT * FROM {table_ref('tcoc_executive_kpis')}")

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
    FROM {table_ref('tcoc_pmpm_trends')}
    WHERE {wc}
    GROUP BY report_month, line_of_business
    ORDER BY report_month
""")

if not trends_df.empty:
    trends_df["pmpm"] = pd.to_numeric(trends_df["pmpm"], errors="coerce")
    trends_df["report_month"] = pd.to_datetime(trends_df["report_month"], errors="coerce")
    fig = go.Figure()
    for i, lob in enumerate(trends_df["line_of_business"].unique()):
        lob_data = trends_df[trends_df["line_of_business"] == lob].sort_values("report_month")
        color = PALETTE[i % len(PALETTE)]
        fig.add_trace(go.Scatter(
            x=lob_data["report_month"], y=lob_data["pmpm"],
            mode="lines+markers", name=str(lob),
            line=dict(width=3, color=color, shape="spline"),
            marker=dict(size=6, color="white", line=dict(width=2.5, color=color)),
            fill="tozeroy",
            fillcolor=color.replace(")", ", 0.08)") if color.startswith("rgb") else f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.08)",
            hovertemplate="<b>%{x|%b %Y}</b><br>PMPM: $%{y:,.2f}<extra>%{fullData.name}</extra>",
        ))
    _style_fig(fig, 420)
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
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
        FROM {table_ref('tcoc_service_category_costs')}
        WHERE {where_clause(has_member_state=False)}
        GROUP BY procedure_category
        ORDER BY total_paid DESC
    """)
    if not svc_df.empty:
        svc_df["total_paid"] = pd.to_numeric(svc_df["total_paid"], errors="coerce")
        svc_df["claims"] = pd.to_numeric(svc_df["claims"], errors="coerce")
        fig2 = px.treemap(
            svc_df, path=["procedure_category"], values="total_paid",
            color="total_paid",
            color_continuous_scale=[[0, "#E8EDF2"], [0.3, "#7BAFD4"], [0.6, "#4A90D9"], [1, "#0B1D3A"]],
            hover_data={"total_paid": ":$,.0f", "claims": ":,.0f"},
        )
        fig2.update_traces(
            texttemplate="<b>%{label}</b><br>$%{value:,.0f}",
            textfont=dict(size=13, color="white"),
            marker=dict(cornerradius=6),
            hovertemplate="<b>%{label}</b><br>Total Paid: $%{value:,.0f}<br>Claims: %{customdata[0]:,.0f}<extra></extra>",
        )
        _style_fig(fig2, 400)
        fig2.update_layout(coloraxis_showscale=False, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.markdown('<div class="section-card"><h3>PMPM by State</h3><div class="subtitle">Geographic cost variation</div></div>', unsafe_allow_html=True)
    geo_df = query(f"""
        SELECT member_state,
               SUM(total_paid) / NULLIF(SUM(active_members), 0) AS pmpm
        FROM {table_ref('tcoc_geographic_analysis')}
        WHERE {wc}
        GROUP BY member_state
        ORDER BY pmpm DESC
    """)
    if not geo_df.empty:
        geo_df["pmpm"] = pd.to_numeric(geo_df["pmpm"], errors="coerce")
        fig3 = go.Figure(go.Choropleth(
            locations=geo_df["member_state"],
            locationmode="USA-states",
            z=geo_df["pmpm"],
            colorscale=[[0, "#E8EDF2"], [0.3, "#7BAFD4"], [0.6, "#4A90D9"], [1, "#0B1D3A"]],
            colorbar=dict(title="PMPM ($)", thickness=12, len=0.7, tickfont=dict(color="#3D5A80"), titlefont=dict(color="#3D5A80")),
            hovertemplate="<b>%{location}</b><br>PMPM: $%{z:,.2f}<extra></extra>",
            marker_line_color="white", marker_line_width=1.5,
        ))
        _choro_layout = {k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis", "margin")}
        fig3.update_layout(
            geo=dict(
                scope="usa", bgcolor="rgba(0,0,0,0)",
                lakecolor="rgba(0,0,0,0)", landcolor="#E8EDF2",
                showlakes=True, showframe=False,
            ),
            **_choro_layout,
            height=400, margin=dict(l=0, r=0, t=10, b=10),
        )
        st.plotly_chart(fig3, use_container_width=True)


# ── Denial Rate & Network Leakage by LOB ───────────────────────────

st.markdown('<div class="section-card"><h3>Denial Rate & Network Leakage by LOB</h3><div class="subtitle">Claims denied and out-of-network spend as percentage of total</div></div>', unsafe_allow_html=True)

dn_df = query(f"""
    SELECT line_of_business,
           SUM(denied_count) * 100.0 / NULLIF(SUM(claim_count), 0) AS denial_rate,
           SUM(oon_paid) * 100.0 / NULLIF(SUM(total_paid), 0) AS network_leakage
    FROM {table_ref('tcoc_pmpm_trends')}
    WHERE {wc}
    GROUP BY line_of_business
""")

if not dn_df.empty:
    dn_df["denial_rate"] = pd.to_numeric(dn_df["denial_rate"], errors="coerce")
    dn_df["network_leakage"] = pd.to_numeric(dn_df["network_leakage"], errors="coerce")
    d1, d2 = st.columns(2, gap="large")
    with d1:
        categories = ["Denial Rate", "Network Leakage"]
        fig4 = go.Figure()
        for i, row in dn_df.iterrows():
            lob = row["line_of_business"]
            color = PALETTE[int(i) % len(PALETTE)]
            fig4.add_trace(go.Scatterpolar(
                r=[row["denial_rate"], row["network_leakage"], row["denial_rate"]],
                theta=categories + [categories[0]],
                fill="toself", name=str(lob),
                fillcolor=color.replace(")", ", 0.15)") if color.startswith("rgb") else f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.15)",
                line=dict(color=color, width=2.5),
                hovertemplate="<b>%{theta}</b>: %{r:.1f}%<extra>" + str(lob) + "</extra>",
            ))
        _style_fig(fig4, 380)
        fig4.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, gridcolor="#E2E8F0", ticksuffix="%", tickfont=dict(color="#0B1D3A", size=11)),
                angularaxis=dict(gridcolor="#E2E8F0", tickfont=dict(color="#0B1D3A", size=12)),
                bgcolor="rgba(0,0,0,0)",
            ),
            title=dict(text="Risk Profile by LOB", font=dict(size=14, color=PRIMARY)),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
            showlegend=True,
        )
        st.plotly_chart(fig4, use_container_width=True)
    with d2:
        dn_melted = dn_df.melt(id_vars="line_of_business", value_vars=["denial_rate", "network_leakage"],
                                var_name="metric", value_name="pct")
        dn_melted["metric"] = dn_melted["metric"].map({"denial_rate": "Denial Rate", "network_leakage": "Network Leakage"})
        fig5 = px.bar(
            dn_melted, x="line_of_business", y="pct", color="metric",
            barmode="group",
            labels={"line_of_business": "LOB", "pct": "Percentage (%)", "metric": ""},
            color_discrete_map={"Denial Rate": DANGER, "Network Leakage": WARNING},
        )
        fig5.update_traces(marker=dict(cornerradius=6),
                           hovertemplate="<b>%{x}</b><br>%{data.name}: %{y:.1f}%<extra></extra>")
        _style_fig(fig5, 380)
        fig5.update_layout(title=dict(text="Side-by-Side Comparison", font=dict(size=14, color=PRIMARY)),
                           legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
        st.plotly_chart(fig5, use_container_width=True)


# ── Provider Analysis ──────────────────────────────────────────────

st.markdown('<div class="section-card"><h3>Top Providers by Total Paid</h3><div class="subtitle">Top 20 providers ranked by total reimbursement</div></div>', unsafe_allow_html=True)

prov_df = query(f"""
    SELECT provider_id, provider_specialty, network_status,
           SUM(total_paid) AS total_paid,
           SUM(total_claims) AS claims,
           SUM(unique_patients) AS patients
    FROM {table_ref('tcoc_provider_network_analysis')}
    WHERE {where_clause(has_plan_type=False, has_member_state=False)}
    GROUP BY provider_id, provider_specialty, network_status
    ORDER BY total_paid DESC
    LIMIT 20
""")

if not prov_df.empty:
    prov_df["total_paid"] = pd.to_numeric(prov_df["total_paid"], errors="coerce")
    prov_df["claims"] = pd.to_numeric(prov_df["claims"], errors="coerce")
    prov_df["patients"] = pd.to_numeric(prov_df["patients"], errors="coerce")
    p1, p2 = st.columns([3, 2], gap="large")
    with p1:
        fig_prov = px.scatter(
            prov_df, x="claims", y="total_paid", size="patients",
            color="network_status",
            color_discrete_map={"In-Network": "#4A90D9", "Out-of-Network": "#C0392B", "in_network": "#4A90D9", "out_of_network": "#C0392B"},
            hover_name="provider_specialty",
            hover_data={"provider_id": True, "total_paid": ":$,.0f", "claims": ":,.0f", "patients": ":,.0f"},
            labels={"claims": "Total Claims", "total_paid": "Total Paid ($)", "patients": "Patients", "network_status": "Network"},
            size_max=45,
        )
        fig_prov.update_traces(
            marker=dict(opacity=0.8, line=dict(width=1, color="white")),
            hovertemplate="<b>%{hovertext}</b><br>Paid: $%{y:,.0f}<br>Claims: %{x:,.0f}<br>Patients: %{marker.size:,.0f}<extra>%{fullData.name}</extra>",
        )
        _style_fig(fig_prov, 420)
        fig_prov.update_layout(legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
        st.plotly_chart(fig_prov, use_container_width=True)
    with p2:
        st.dataframe(
            prov_df[["provider_specialty", "network_status", "total_paid", "claims"]]
            .style.format({"total_paid": "${:,.0f}", "claims": "{:,.0f}"}),
            use_container_width=True, hide_index=True, height=420,
        )

# ── 6-Month Cost Forecast ──────────────────────────────────────────

st.markdown('<div class="section-card"><h3>\U0001f4c8 6-Month Cost Forecast (Jan\u2013Jun 2026)</h3><div class="subtitle">LightGBM model trained on historical claims \u2014 registered in Unity Catalog</div></div>', unsafe_allow_html=True)

forecast_wc = where_clause()
forecast_df = query(f"""
    SELECT forecast_month, line_of_business, plan_type, member_state,
           predicted_paid, predicted_pmpm, lower_bound, upper_bound, model_version
    FROM {table_ref('tcoc_cost_forecast')}
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
        FROM {table_ref('tcoc_pmpm_trends')}
        WHERE {forecast_wc}
        GROUP BY report_month, line_of_business
        UNION ALL
        SELECT forecast_month AS month, line_of_business,
               AVG(predicted_pmpm) AS pmpm,
               'Forecast' AS series_type
        FROM {table_ref('tcoc_cost_forecast')}
        WHERE {forecast_wc}
        GROUP BY forecast_month, line_of_business
        ORDER BY month
    """)
    if not actual_df.empty:
        actual_df["pmpm"] = pd.to_numeric(actual_df["pmpm"], errors="coerce")
        actual_df["month"] = pd.to_datetime(actual_df["month"], errors="coerce")
        # Build confidence-band forecast chart
        fig_fc = go.Figure()
        # Add confidence bands from forecast data
        fc_band = (
            forecast_df.groupby("forecast_month", as_index=False)
            .agg(lower=pd.NamedAgg("lower_bound", "mean"), upper=pd.NamedAgg("upper_bound", "mean"),
                 pmpm=pd.NamedAgg("predicted_pmpm", "mean"))
            .sort_values("forecast_month")
        )
        fig_fc.add_trace(go.Scatter(
            x=pd.concat([fc_band["forecast_month"], fc_band["forecast_month"][::-1]]),
            y=pd.concat([fc_band["upper"], fc_band["lower"][::-1]]),
            fill="toself", fillcolor="rgba(74,144,217,0.15)",
            line=dict(color="rgba(0,0,0,0)"), showlegend=True, name="Confidence Band",
            hoverinfo="skip",
        ))
        for stype in ["Actual", "Forecast"]:
            sdf = actual_df[actual_df["series_type"] == stype].sort_values("month")
            if sdf.empty:
                continue
            is_forecast = stype == "Forecast"
            fig_fc.add_trace(go.Scatter(
                x=sdf["month"], y=sdf["pmpm"],
                mode="lines+markers", name=stype,
                line=dict(width=3, dash="dot" if is_forecast else "solid",
                          color="#D4A017" if is_forecast else "#4A90D9", shape="spline"),
                marker=dict(size=7 if is_forecast else 5,
                            symbol="diamond" if is_forecast else "circle",
                            color="#D4A017" if is_forecast else "#4A90D9"),
                hovertemplate="<b>%{x|%b %Y}</b><br>PMPM: $%{y:,.2f}<extra>" + stype + "</extra>",
            ))
        _style_fig(fig_fc, 450)
        fig_fc.update_layout(
            title=dict(text="Actual vs Forecast PMPM with Confidence Band", font=dict(size=14, color=PRIMARY)),
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_fc, use_container_width=True)

    # Forecast by LOB donut + state table
    fl, fr = st.columns(2, gap="large")
    with fl:
        lob_fc = forecast_df.groupby("line_of_business", as_index=False)["predicted_paid"].sum()
        fig_lob = go.Figure(go.Pie(
            labels=lob_fc["line_of_business"], values=lob_fc["predicted_paid"],
            hole=0.55, marker=dict(colors=PALETTE[:len(lob_fc)], line=dict(color="white", width=2)),
            textinfo="label+percent", textfont=dict(size=12),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        _style_fig(fig_lob, 400)
        fig_lob.update_layout(
            title=dict(text="Forecasted Cost by LOB", font=dict(size=14, color=PRIMARY)),
            annotations=[dict(text="Forecast", x=0.5, y=0.5, font_size=16, font_color=TEXT_MUTED, showarrow=False)],
            showlegend=False, margin=dict(l=20, r=20, t=50, b=20),
        )
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
    Luminos Health &bull; Total Cost of Care &bull; Data source: <code>{data_source_label()}</code> &bull; Auto-refreshes every 5 min<br/>
    Powered by <strong>Databricks</strong>
</div>
""", unsafe_allow_html=True)
