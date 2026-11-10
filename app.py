import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
import tempfile
import os

if not os.path.exists("store.db"):
    import create_database

from agent import ask_agent, explain_result, describe_table, build_schema_from_db, SCHEMA

st.set_page_config(
    page_title="Conversational Business Intelligence Using Generative AI",
    page_icon="📊",
    layout="wide",
)

TEXT_SIZES = {"Standard": 18, "Large": 22, "Extra large": 26}

if "text_size" not in st.session_state:
    st.session_state.text_size = "Large"

# --- Accessible typography and controls ---
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1440px; }
    section[data-testid="stSidebar"] { width: 18rem !important; }
    section[data-testid="stSidebar"] > div { width: 18rem !important; }
    .stApp { font-size: 22px; line-height: 1.6; }
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stCaptionContainer"],
    div[data-testid="stWidgetLabel"],
    div[data-testid="stMetricLabel"] { font-size: 1em; line-height: 1.5; }
    div[data-testid="stChatInput"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] div[role="combobox"] { font-size: 1em; }
    .stApp div[data-testid="stMarkdownContainer"] p.hero {
        font-size: clamp(1.5rem, 2.6vw, 2.2rem);
        font-weight: 800;
        line-height: 1.25;
        letter-spacing: -.03em;
        margin: 0;
    }
    .stApp div[data-testid="stMarkdownContainer"] p.sub {
        color: #8b92a8;
        margin: .4rem 0 0;
        font-size: 1em;
        line-height: 1.55;
    }
    .eyebrow {
        color: #5b9cff;
        font-size: .8em;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
        margin: 0 0 .45rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: rgba(128, 128, 128, .2);
        border-radius: 1rem;
    }
    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, .08);
        border: 1px solid rgba(128, 128, 128, .16);
        padding: .65rem .85rem;
        border-radius: .75rem;
    }
    div[data-testid="stMetricValue"] { font-size: 1.35em; }
    div[data-testid="stButton"] > button,
    div[data-testid="stButton"] > button[kind="secondary"] {
        min-height: 3.25rem;
        border-radius: .7rem;
        font-size: 1em;
        line-height: 1.35;
        white-space: normal;
        height: auto;
    }
    div[role="radiogroup"] label,
    div[data-testid="stCheckbox"] label { min-height: 2.75rem; }
    @media (max-width: 700px) {
        .block-container { padding: 1rem 1rem 3rem; }
        .stApp div[data-testid="stMarkdownContainer"] p.hero { font-size: 1.5rem; }
    }
</style>
""".replace("22px", f"{TEXT_SIZES[st.session_state.text_size]}px"), unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []
if "pending" not in st.session_state:
    st.session_state.pending = None
if "analysis" not in st.session_state:
    st.session_state.analysis = None


def clean_columns(d):
    d.columns = (
        d.columns.astype(str)
        .str.strip().str.lower()
        .str.replace(r"[^\w\s]", "", regex=True)
        .str.replace(r"\s+", "_", regex=True)
    )
    return d


def safe_table_name(name):
    t = name.strip().lower().replace(" ", "_").replace("-", "_")
    return "".join(c for c in t if c.isalnum() or c == "_") or "sheet"


def list_tables(db_path):
    conn = sqlite3.connect(db_path)
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]
    conn.close()
    return names


def table_details(db_path, table):
    conn = sqlite3.connect(db_path)
    quoted_table = table.replace('"', '""')
    row_count = conn.execute(
        f'SELECT COUNT(*) FROM "{quoted_table}"'
    ).fetchone()[0]
    fields = conn.execute(
        f'PRAGMA table_info("{quoted_table}")'
    ).fetchall()
    conn.close()
    return row_count, fields


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("📁 Data Source")
    st.select_slider(
        "Text size",
        options=list(TEXT_SIZES),
        key="text_size",
        help="Choose a comfortable text size. This setting applies throughout the app.",
    )
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])

    active_db = "store.db"
    active_schema = SCHEMA
    active_source = "Demo store database"

    if uploaded is not None:
        tmp_db = os.path.join(tempfile.gettempdir(), "uploaded.db")
        active_source = uploaded.name

        if uploaded.name.lower().endswith((".xlsx", ".xls")):
            xls = pd.ExcelFile(uploaded)
            conn = sqlite3.connect(tmp_db)
            sheet_info = []
            for name in xls.sheet_names:
                d = clean_columns(pd.read_excel(xls, sheet_name=name))
                table = safe_table_name(name)
                d.to_sql(table, conn, if_exists="replace", index=False)
                sheet_info.append((name, table, d.shape[0], d.shape[1]))
            conn.close()
            active_db = tmp_db
            active_schema = build_schema_from_db(tmp_db)
            st.success(f"Loaded {len(sheet_info)} sheet(s) from **{uploaded.name}**.")
            with st.expander("Sheets / tables"):
                for name, table, rows, cols in sheet_info:
                    st.write(f"**{name}** → `{table}` · {rows:,} rows × {cols} columns")
        else:
            try:
                df = pd.read_csv(uploaded)
            except UnicodeDecodeError:
                uploaded.seek(0)
                df = pd.read_csv(uploaded, encoding="latin-1")
            df = clean_columns(df)
            conn = sqlite3.connect(tmp_db)
            df.to_sql("data", conn, if_exists="replace", index=False)
            conn.close()
            active_db = tmp_db
            active_schema = build_schema_from_db(tmp_db)
            st.success(
                f"Loaded **{uploaded.name}** · {df.shape[0]:,} rows × "
                f"{df.shape[1]} columns."
            )
            with st.expander("Columns"):
                st.write(list(df.columns))
    else:
        st.caption("Using the built-in demo store database. Upload a CSV or Excel file to analyze your own data.")

    tables = list_tables(active_db)
    st.caption(f"**{active_source}** · {len(tables)} table(s)")

    st.divider()
    st.header("🕘 History")
    if st.session_state.history:
        for i, q in enumerate(reversed(st.session_state.history)):
            if st.button(q, key=f"h{i}", width="stretch"):
                st.session_state.pending = q
    else:
        st.caption("Past questions appear here.")


# ---------------- Header ----------------
with st.container(border=True):
    st.markdown('<p class="eyebrow">Your analytics workspace</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero">Conversational Business Intelligence Using Generative AI</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub">Ask questions in plain English. Explore the data, '
        'review the analysis, and get a clear business takeaway.</p>',
        unsafe_allow_html=True,
    )
    

# Compact mode switch (segmented control falls back to radio on older Streamlit)
try:
    mode = st.segmented_control(
        "Mode", ["Ask", "Explore"], default="Ask", label_visibility="collapsed"
    ) or "Ask"
except Exception:
    mode = st.radio("Mode", ["Ask", "Explore"], horizontal=True, label_visibility="collapsed")


# =========================================================
#  EXPLORE MODE
# =========================================================
if mode == "Explore":
    if not tables:
        st.info("Upload a file to explore it.")
    else:
        st.subheader("Explore your data")
        st.caption("Review table size, inspect field definitions, and preview the source data.")
        c1, c2 = st.columns([3, 1])
        chosen = c1.selectbox("Table / sheet", tables)
        go = c2.button("✨ Generate overview", width="stretch")

        row_count, fields = table_details(active_db, chosen)
        metric_cols = st.columns(3)
        metric_cols[0].metric("Rows", f"{row_count:,}")
        metric_cols[1].metric("Columns", len(fields))
        metric_cols[2].metric("Source tables", len(tables))

        st.markdown("#### Fields")
        field_summary = pd.DataFrame(
            [
                {
                    "Column": field[1],
                    "Data type": field[2] or "Not specified",
                    "Required": "Yes" if field[3] or field[5] else "No",
                    "Primary key": "Yes" if field[5] else "No",
                }
                for field in fields
            ]
        )
        st.dataframe(field_summary, width="stretch", hide_index=True)

        st.markdown("#### Data preview")
        conn = sqlite3.connect(active_db)
        quoted_table = chosen.replace('"', '""')
        preview = pd.read_sql(f'SELECT * FROM "{quoted_table}" LIMIT 10', conn)
        conn.close()
        st.caption("Showing the first 10 rows.")
        st.dataframe(preview, width="stretch", height=350, hide_index=True)

        if go:
            with st.spinner("Reading the data…"):
                overview = describe_table(chosen, active_db)
            st.markdown("#### AI-generated overview")
            st.info(overview)

# =========================================================
#  ASK MODE — chat-style input
# =========================================================
else:
    # Suggested questions when nothing asked yet
    if not st.session_state.history:
        st.markdown("### Start with a question")
        st.caption("Choose a starting point or write your own question below.")
        s1, s2, s3 = st.columns(3)
        if s1.button("Revenue trend", key="prompt_monthly", width="stretch",
                     help="Compare total revenue month by month."):
            st.session_state.pending = "What is the total revenue for each month?"
        if s2.button("Revenue drop", key="prompt_drop", width="stretch",
                     help="Find which product category had the biggest revenue drop from May to June 2026."):
            st.session_state.pending = "Which product category had the biggest revenue drop from May to June 2026?"
        if s3.button("By region", key="prompt_region", width="stretch",
                     help="Compare revenue across regions."):
            st.session_state.pending = "How much revenue came from each region?"

    typed = st.chat_input("Ask about revenue, products, customers, or trends…")
    question = typed or st.session_state.pending
    st.session_state.pending = None

    if question:
        if question not in st.session_state.history:
            st.session_state.history.append(question)

        st.session_state.analysis = None
        st.markdown(f"**❓ {question}**")

        with st.spinner("Generating SQL and querying the database…"):
            result, sql = ask_agent(question, schema=active_schema, db_path=active_db)

        if result is None:
            st.error("I couldn't answer that. Try rephrasing, or switch to **Explore** "
                     "mode for a general overview of your data.")
        else:
            with st.spinner("Writing the business insight…"):
                insight = explain_result(question, sql, result)
            st.session_state.analysis = {
                "question": question,
                "result": result,
                "sql": sql,
                "insight": insight,
            }

    analysis = st.session_state.analysis
    if analysis is not None:
        result = analysis["result"]
        st.markdown(f"**❓ {analysis['question']}**")
        st.success("Analysis complete")
        summary = st.columns(3)
        summary[0].metric("Result rows", f"{len(result):,}")
        summary[1].metric("Result columns", len(result.columns))
        summary[2].metric(
            "Numeric measures",
            len(result.select_dtypes(include="number").columns),
        )

        data_tab, chart_tab, sql_tab = st.tabs(["📋 Results", "📊 Visualization", "🧾 SQL"])
        with data_tab:
            st.dataframe(result, width="stretch", height=350, hide_index=True)
            st.download_button(
                "⬇️ Download results as CSV",
                result.to_csv(index=False).encode("utf-8"),
                "analysis.csv", "text/csv",
            )

        with chart_tab:
            numeric_cols = result.select_dtypes(include="number").columns.tolist()
            if len(result) < 2 or len(result.columns) < 2 or not numeric_cols:
                st.info("This result needs at least two rows, two columns, and one numeric column to create a chart.")
            else:
                chart_controls = st.columns(3)
                x_col = chart_controls[0].selectbox(
                    "Category / X axis", result.columns.tolist()
                )
                y_col = chart_controls[1].selectbox(
                    "Measure / Y axis", numeric_cols
                )
                chart_type = chart_controls[2].selectbox(
                    "Chart type", ["Bar", "Line", "Scatter"]
                )

                fig, ax = plt.subplots(figsize=(9, 4.5))
                x_values = result[x_col]
                y_values = result[y_col]
                if chart_type == "Bar":
                    ax.bar(x_values.astype(str), y_values)
                elif chart_type == "Line":
                    ax.plot(x_values.astype(str), y_values, marker="o")
                else:
                    ax.scatter(x_values, y_values)
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                ax.set_title(f"{y_col} by {x_col}")
                if chart_type != "Scatter":
                    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
                ax.grid(axis="y", alpha=.2)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

        with sql_tab:
            st.caption("Generated query used to retrieve these results.")
            st.code(analysis["sql"], language="sql")

        st.subheader("💡 Business insight")
        st.info(analysis["insight"])