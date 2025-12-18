#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import io
import math
import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from itertools import count
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots

# =========================================================
# Help Modal (Fragile Months)
# Place this ONCE near the top of your file (after imports)
# =========================================================
@st.dialog("Revenue Fragility — Interpretation Guide")
def show_fragility_help():
    st.markdown("""
This view measures **monthly revenue dependency risk** by showing what share of revenue relies on a **critical product type**, alongside a **Seasonality Index** that indicates whether the month is above or below a normal revenue level.

----
**Insight — What to look for**

- Months with a **high At Risk %** are heavily dependent on one product type.  
- When this dependency coincides with a **below-average month** (Seasonality Index < 1.0), the month is flagged **⚠ Seasonal Risk**, indicating **low resilience if that product underperforms**.


---

**Recommendation — How to act on this**

Prioritize action for **⚠ Seasonal Risk** months:
- Reduce reliance on the critical product through **mix diversification**.
- Prepare **alternate products, inventory buffers, or promotions** ahead of time.
- Repeated flags under *Overall Critical* suggest a **structural dependency**; flags under *Seasonal Critical* suggest a **seasonal planning issue**.

---

**Seasonal Risk Rule**  
A month is flagged when:
- **At Risk share ≥ selected threshold**, and  
- **Seasonality Index < 1.0** (below-average month)
""")

@st.dialog("Price Elasticity — Interpretation Guide")
def show_seasonality_help():
        

        st.markdown("""
This view provides an **executive-level check on pricing effectiveness across seasonal cycles**.

It summarizes performance by **Month × Grade** (after applying the Product Type filter):
- **X-axis:** Month-Year (seasonality timing)
- **Y-axis:** Revenue (CAD)
- **Bubble size:** Average transaction price (Avg Price)
- **Color:** Grade
- **Line:** Total monthly revenue trend (all grades combined)

Each bubble aggregates **all product types included by the current filter** for that grade and month.

----
**Insight — What to look for**

Use this view to quickly identify:
- **Seasonal revenue peaks and slowdowns** (revenue trend line)
- Months where pricing was **more aggressive** (larger bubbles)
- Differences in **price sensitivity by grade**
- **High-confidence price-resistance alerts** (⚠ markers)

A **⚠ Flag** indicates a month where the data suggests customers may have pushed back on pricing:
- Average price rose meaningfully, while both revenue and demand weakened.

---

**Recommendation — How to act on this**

Focus attention on **⚠ flagged months**, especially when bubbles are large and revenue trends are softening.

**High-confidence flag definition (per Grade, compared to a 3-month rolling baseline):**
- **Avg Price ≥ +5%**
- **Revenue ≤ −10%**
- **Volume (transaction count) ≤ −10%**

These alerts are designed as an **early-warning system**:
- Review pricing actions taken in flagged periods before repeating them in future seasonal cycles.
- Consider targeted tactics (bundles, promotions, mix shifts) if the same grade is flagged repeatedly.
- If multiple grades are flagged in the same month, assess whether the driver is **broader seasonal demand softness** rather than pricing alone.
""")

@st.dialog("Seasonal Campaign Opportunities — Interpretation Guide")
def show_opportunity_help():
    st.markdown(
        """
This heatmap isolates **below-average revenue months** (as defined by the **Seasonality Index** threshold) and shows
**which product types still capture demand** during those weaker periods.

- **Columns:** slow months (Month–Year) selected from your criteria  
- **Rows:** product types, **ranked** by **Opportunity Score**  
- **Cell value:** either **Share of Month (%)** or **Revenue (CAD)**, based on your metric selection  
- **Opportunity Score:** combines **consistency** (appears across slow months) and **average share** (importance within those months)

---
**Insight — What to look for**


Use this view to identify product types that are **reliable performers when demand is soft**.

- **Darker cells** indicate stronger contribution in a slow month  
- **Top-ranked rows** are the most dependable campaign candidates  
- If a product stays dark across multiple columns, it is a **repeatable lever** for seasonal stabilization  
- If a product spikes only once, it may be **event-driven** rather than campaignable

---

**Recommendation — How to act on this**


Prioritize campaign effort on the **top-ranked products**, especially those with:
- **High Opportunity Score** (reliable across slow months)  
- **Consistent presence** (appears in many slow months)  
- **Meaningful share** (material contributor when revenue is weak)

Suggested actions:
- Build **bundles** around top-ranked products  
- Run **targeted promotions** in the identified slow months  
- Align **content and messaging** to products resilient in downturn periods  
- Use this as a **campaign short-list**, then validate with inventory and margin constraints

---
**Interpretation note:** This is an **opportunity ranking**, not a forecast. It guides where campaigns are most likely to stabilize revenue during seasonal softness.
"""
    )


# -----------------------------
# Plotly + Streamlit Defaults
# -----------------------------
pio.templates.default = "plotly_white"
px.defaults.template = "plotly_white"

_plot_counter = count()
_widget_counter = count()


def pkey(prefix="plot"):
    return f"{prefix}_{next(_plot_counter)}"


def wkey(prefix="w"):
    return f"{prefix}_{next(_widget_counter)}"


# -----------------------------
# Page Config & Styling
# -----------------------------
st.set_page_config(
    page_title="Global Ammolite Dashboard – All Themes",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root{
      --bg: #FFFFFF;
      --text: #000000;
      --border: #D9D9D9;
      --soft: #F5F5F5;
    }

    /* App background + default text */
    html, body, [class*="css"], .stApp {
      font-size: 0.95rem !important;
      background: var(--bg) !important;
      color: var(--text) !important;
      font-family: SpaceGrotesk, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif !important;
    }

    /* FORCE readable text everywhere (fixes faint/washed-out text) */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp div, .stApp a, .stApp li, .stApp small {
      color: var(--text) !important;
      opacity: 1 !important;
    }

    .block-container {
      padding-top: 0.8rem;
      padding-bottom: 2.0rem;
      max-width: 1550px;
      background: var(--bg) !important;
      color: var(--text) !important;
    }

    div[data-testid="column"] { padding-left: 0.40rem; padding-right: 0.40rem; }

    /* Sidebar: force white background + black text */
    section[data-testid="stSidebar"] {
      background: var(--bg) !important;
      color: var(--text) !important;
      border-right: 1px solid var(--border) !important;
    }
    section[data-testid="stSidebar"] * {
      color: var(--text) !important;
      opacity: 1 !important;
    }

    /* Metric cards (keep your sizing) */
    [data-testid="metric-container"] {
      padding: 0.70rem 0.85rem !important;
      border-radius: 14px !important;
      background: var(--bg) !important;
      border: 1px solid var(--border) !important;
    }
    /* Metric label/value/delta -> BLACK + full opacity (fixes invisible KPIs) */
    [data-testid="metric-container"] [data-testid="stMetricLabel"],
    [data-testid="metric-container"] [data-testid="stMetricLabel"] * ,
    [data-testid="metric-container"] [data-testid="stMetricValue"],
    [data-testid="metric-container"] [data-testid="stMetricValue"] * ,
    [data-testid="metric-container"] [data-testid="stMetricDelta"],
    [data-testid="metric-container"] [data-testid="stMetricDelta"] * {
      color: #000000 !important;
      opacity: 1 !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
      font-size: 1.55rem !important;
      overflow: visible !important;
      text-overflow: clip !important;
      white-space: normal !important;
      line-height: 1.2 !important;
    }

    /* Captions (Filtered view...) */
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] * {
      color: #000000 !important;
      opacity: 1 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
      font-size: 0.95rem;
      color: var(--text) !important;
      opacity: 1 !important;
    }

    /* Headings */
    h1,h2,h3,h4,h5,h6,
    .stMarkdown h1,.stMarkdown h2,.stMarkdown h3,.stMarkdown h4 {
      color: var(--text) !important;
      font-family: SpaceGroteskHeader, SpaceGrotesk, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif !important;
      opacity: 1 !important;
    }

    /* -----------------------------
       ✅ INPUTS: WHITE BACKGROUND + BLACK TEXT (everywhere)
    ------------------------------ */

    /* Input shells */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
      background: #FFFFFF !important;
      color: #000000 !important;
      border: 1px solid var(--border) !important;
      border-radius: 10px !important;
      opacity: 1 !important;
    }

    /* Select internal input + text */
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {
      color: #000000 !important;
      opacity: 1 !important;
    }

    /* Dropdown popovers (opened menu) */
    div[data-baseweb="popover"] *,
    ul[role="listbox"],
    li[role="option"] {
      background: #FFFFFF !important;
      color: #000000 !important;
      opacity: 1 !important;
    }
    li[role="option"]:hover { background: var(--soft) !important; }

    /* Multiselect tags */
    .stMultiSelect span[data-baseweb="tag"] {
      background: var(--soft) !important;
      color: #000000 !important;
      border: 1px solid var(--border) !important;
      opacity: 1 !important;
    }
    .stMultiSelect span[data-baseweb="tag"] svg { fill: #000000 !important; }

    /* Date / Number inputs */
    div[data-testid="stDateInput"] input,
    div[data-testid="stNumberInput"] input {
      background: #FFFFFF !important;
      color: #000000 !important;
      border: 1px solid var(--border) !important;
      border-radius: 10px !important;
      opacity: 1 !important;
    }

    /* Radio / Checkbox / Toggle / Slider text */
    .stRadio *, .stCheckbox *, .stToggle *, .stSlider * {
      color: #000000 !important;
      opacity: 1 !important;
    }

    /* Buttons (including file uploader button) */
    .stButton > button,
    button[data-testid^="stBaseButton"],
    button[kind] {
      background: #FFFFFF !important;
      color: #000000 !important;
      border: 1px solid #000000 !important;
      border-radius: 10px !important;
      opacity: 1 !important;
    }
    .stButton > button:hover,
    button[data-testid^="stBaseButton"]:hover,
    button[kind]:hover { background: var(--soft) !important; }
    .stButton > button * ,
    button[data-testid^="stBaseButton"] * ,
    button[kind] * { color: #000000 !important; opacity: 1 !important; }

    /* File uploader dropzone */
    div[data-testid="stFileUploaderDropzone"] {
      background: #FFFFFF !important;
      border: 1px dashed var(--border) !important;
    }
    div[data-testid="stFileUploaderDropzone"] * {
      color: #000000 !important;
      opacity: 1 !important;
    }

    /* Dataframes background */
    .stDataFrame, .stTable { background: #FFFFFF !important; }

    /* ✅ Highlight/Selection: keep text BLACK */
    ::selection { background: #E6E6E6 !important; color: #000000 !important; }
    ::-moz-selection { background: #E6E6E6 !important; color: #000000 !important; }
    input::selection, textarea::selection { background: #E6E6E6 !important; color: #000000 !important; }

    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Helper: Deduplicate columns
# -----------------------------
def deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = []
    seen = {}
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols
    return df


def safe_col(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns


def to_num(df: pd.DataFrame, col: str):
    if safe_col(df, col):
        df[col] = pd.to_numeric(df[col], errors="coerce")


def style_fig(fig, height=430):
    # ✅ White chart background + black text + FIXED hoverlabel (no ValueError)
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=55, b=40),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="SpaceGrotesk", size=12, color="#000000"),
        legend=dict(
            font=dict(size=11, family="SpaceGrotesk", color="#000000"),
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
        ),
        hoverlabel=dict(
            font=dict(size=11, family="SpaceGrotesk", color="#000000"),
            bgcolor="#FFFFFF",
        ),
        xaxis=dict(
            title_font=dict(size=13, family="SpaceGrotesk", color="#000000"),
            tickfont=dict(size=11, family="SpaceGrotesk", color="#000000"),
            automargin=True,
        ),
        yaxis=dict(
            title_font=dict(size=13, family="SpaceGrotesk", color="#000000"),
            tickfont=dict(size=11, family="SpaceGrotesk", color="#000000"),
            automargin=True,
        ),
    )

    # maps
    try:
        fig.update_geos(bgcolor="#FFFFFF")
    except Exception:
        pass

    # Safe hovertemplate reset (some trace types don't support it)
    def _safe_unset_hovertemplate(tr):
        try:
            if "hovertemplate" in tr.to_plotly_json():
                tr.update(hovertemplate=None)
        except Exception:
            pass

    fig.for_each_trace(_safe_unset_hovertemplate)
    return fig


# -----------------------------
# Data Loading & Preparation
# -----------------------------
@st.cache_data(show_spinner=False)
def load_data(uploaded_file=None):
    # 1) Choose source
    csv_path = None
    if uploaded_file is None:
        possible_paths = [
            "Combined_Sales_2025.csv",
            "Combined_Sales_2025 (2).csv",
            "data/Combined_Sales_2025.csv",
            "/mnt/data/Combined_Sales_2025.csv",
        ]
        for p in possible_paths:
            if Path(p).exists():
                csv_path = p
                break

    # 2) Read CSV (robust encoding)
    def _read_csv(src):
        try:
            return pd.read_csv(src)
        except UnicodeDecodeError:
            try:
                return pd.read_csv(src, encoding="utf-8", encoding_errors="replace")
            except TypeError:
                return pd.read_csv(src, encoding="latin-1")

    if uploaded_file is not None:
        df = _read_csv(uploaded_file)
    else:
        if csv_path is None:
            st.error(
                "❌ CSV file not found.\n\n"
                "Option A: Upload your CSV in the sidebar.\n"
                "Option B: Put **Combined_Sales_2025.csv** in the same folder as this app."
            )
            st.stop()
        df = _read_csv(csv_path)

    # 3) Ensure unique column names
    df = deduplicate_columns(df)

    # 4) Trim object columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    # 5) Parse dates (safe)
    if safe_col(df, "Date"):
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    else:
        st.error("❌ Missing required column: 'Date'")
        st.stop()

    if safe_col(df, "Shipped Date"):
        df["Shipped Date"] = pd.to_datetime(df["Shipped Date"], errors="coerce")
    else:
        df["Shipped Date"] = pd.NaT

    # 6) Numeric conversions (safe)
    for c in ["Price (CAD)", "Discount (CAD)", "Shipping (CAD)", "Taxes Collected (CAD)",
              "length", "width", "weight", "Color Count (#)"]:
        to_num(df, c)

    # Fill core monetary columns if missing
    for c in ["Price (CAD)", "Discount (CAD)", "Shipping (CAD)", "Taxes Collected (CAD)"]:
        if not safe_col(df, c):
            df[c] = 0.0
        df[c] = df[c].fillna(0.0)

    # 7) Derived metrics
    df["Net Sales"] = df["Price (CAD)"] - df["Discount (CAD)"]
    df["Total Collected"] = df["Net Sales"] + df["Shipping (CAD)"] + df["Taxes Collected (CAD)"]
    df["OrderCount"] = 1

    # 8) Ownership
    if safe_col(df, "Consignment? (Y/N)"):
        df["Is Consigned"] = df["Consignment? (Y/N)"].astype(str).str.upper().eq("Y")
    else:
        df["Is Consigned"] = False
    df["Ownership"] = np.where(df["Is Consigned"], "Consigned", "Owned")

    # 9) Timing
    df["Days to Ship"] = (df["Shipped Date"] - df["Date"]).dt.days

    df["Days_to_Ship"] = df["Days to Ship"]
    # 10) Area + price density
    if safe_col(df, "length") and safe_col(df, "width"):
        df["Area (mm²)"] = df["length"] * df["width"]
        df["Price per mm²"] = df["Net Sales"] / df["Area (mm²)"]
        df.loc[~np.isfinite(df["Price per mm²"]), "Price per mm²"] = np.nan
    else:
        df["Area (mm²)"] = np.nan
        df["Price per mm²"] = np.nan

    # 11) Time dimensions
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    df["Month Name"] = df["Date"].dt.strftime("%b")
    df["Month Number"] = df["Date"].dt.month
    df["Quarter"] = df["Date"].dt.to_period("Q").astype(str)
    df["Day Name"] = df["Date"].dt.day_name()
    df["Week"] = df["Date"].dt.to_period("W").dt.start_time

    # 12) Compliance
    if safe_col(df, "Export Permit (PDF link)"):
        df["Has Export Permit"] = (
            df["Export Permit (PDF link)"].astype(str).str.strip().ne("")
            & df["Export Permit (PDF link)"].notna()
        )
    else:
        df["Has Export Permit"] = False

    if safe_col(df, "COA #"):
        df["Has COA"] = df["COA #"].astype(str).str.strip().ne("") & df["COA #"].notna()
    else:
        df["Has COA"] = False

    if safe_col(df, "Country"):
        df["Country"] = df["Country"].fillna("Unknown").astype(str)
    else:
        df["Country"] = "Unknown"

    if safe_col(df, "City"):
        df["City"] = df["City"].fillna("Unknown").astype(str)
    else:
        df["City"] = "Unknown"

    if safe_col(df, "Channel"):
        df["Channel"] = df["Channel"].fillna("Unknown").astype(str)
    else:
        df["Channel"] = "Unknown"

    if safe_col(df, "Customer Type"):
        df["Customer Type"] = df["Customer Type"].fillna("Unknown").astype(str)
    else:
        df["Customer Type"] = "Unknown"

    if safe_col(df, "Customer Name"):
        df["Customer Name"] = df["Customer Name"].fillna("Unknown").astype(str)
    else:
        df["Customer Name"] = "Unknown"

    df["Is Export"] = df["Country"].ne("Canada")

    return df


# -----------------------------
# Sidebar: Data source + Filters
# -----------------------------
st.sidebar.title("Controls")

uploaded = st.sidebar.file_uploader(
    "Upload sales CSV (optional)",
    type=["csv"],
    key="upload_csv",
    help="If you upload here, it overrides searching for Combined_Sales_2025.csv in the folder.",
)

# -----------------------------
# Navigation (render only selected page for speed)
# -----------------------------
_main_pages = [
    "Overview",
    "Price Drivers",
    "Product Mix",
    "Customer Segments",
    "Geography & Channels",
    "Inventory Timing",
    "Ownership",
    "Seasonality",
    "Compliance",
    "Stats",
    "All Data",
]
page = st.sidebar.radio("Navigate", _main_pages, index=0, key="nav_main")
st.sidebar.markdown("---")


df = load_data(uploaded_file=uploaded)

min_date = df["Date"].min()
max_date = df["Date"].max()
if pd.isna(min_date) or pd.isna(max_date):
    st.error("❌ 'Date' column has no valid dates.")
    st.stop()

date_range = st.sidebar.slider(
    "Sale Date range",
    min_value=min_date.date(),
    max_value=max_date.date(),
    value=(min_date.date(), max_date.date()),
    key="date_range",
)


# Core filters
country_options = sorted(df["Country"].dropna().unique())
channel_options = sorted(df["Channel"].dropna().unique())
cust_type_options = sorted(df["Customer Type"].dropna().unique())

sel_countries = st.sidebar.multiselect("Countries", options=country_options, default=[], key="countries")
sel_channels = st.sidebar.multiselect("Channels", options=channel_options, default=[], key="channels")
sel_cust = st.sidebar.multiselect("Customer types", options=cust_type_options, default=[], key="cust_types")

# Advanced filters
with st.sidebar.expander("More filters (optional)", expanded=False):
    prod_opts = sorted(df["Product Type"].dropna().unique()) if safe_col(df, "Product Type") else []
    grade_opts = sorted(df["Grade"].dropna().unique()) if safe_col(df, "Grade") else []
    finish_opts = sorted(df["Finish"].dropna().unique()) if safe_col(df, "Finish") else []

    sel_prod = st.multiselect("Product Type", options=prod_opts, default=[], key="prod_type")
    sel_grade = st.multiselect("Grade", options=grade_opts, default=[], key="grade")
    sel_finish = st.multiselect("Finish", options=finish_opts, default=[], key="finish")

    only_export = st.checkbox("Export only (Country != Canada)", value=False, key="only_export")
    only_consigned = st.checkbox("Consigned only", value=False, key="only_consigned")

    name_search = st.text_input("Customer name contains", value="", key="cust_search")

    max_rows = st.slider("Max rows to show in tables", 100, 3000, 500, step=100, key="max_rows")

metric_map = {
    "Net Sales (CAD)": "Net Sales",
    "Total Collected (CAD)": "Total Collected",
    "Order Count": "OrderCount",
}
metric_label = st.sidebar.selectbox("Main metric for charts", options=list(metric_map.keys()), index=0, key="metric")
metric_col = metric_map[metric_label]

compare_prev = st.sidebar.toggle("Show deltas vs previous period", value=True, key="compare_prev")


def apply_filters(data: pd.DataFrame, start, end) -> pd.DataFrame:
    mask = pd.Series(True, index=data.index)
    mask &= data["Date"].between(pd.to_datetime(start), pd.to_datetime(end))

    if sel_countries:
        mask &= data["Country"].isin(sel_countries)
    if sel_channels:
        mask &= data["Channel"].isin(sel_channels)
    if sel_cust:
        mask &= data["Customer Type"].isin(sel_cust)

    if safe_col(data, "Product Type") and sel_prod:
        mask &= data["Product Type"].isin(sel_prod)
    if safe_col(data, "Grade") and sel_grade:
        mask &= data["Grade"].isin(sel_grade)
    if safe_col(data, "Finish") and sel_finish:
        mask &= data["Finish"].isin(sel_finish)

    if only_export:
        mask &= data["Is Export"]
    if only_consigned:
        mask &= data["Is Consigned"]

    if name_search.strip():
        mask &= data["Customer Name"].str.contains(name_search.strip(), case=False, na=False)

    return data[mask].copy()


# Resolve date range
if isinstance(date_range, tuple) and len(date_range) == 2:
    cur_start, cur_end = date_range
else:
    cur_start, cur_end = min_date.date(), max_date.date()

f = apply_filters(df, cur_start, cur_end)

if f.empty:
    st.warning("No rows match the current filters. Try widening your filters on the left.")
    st.stop()

# Previous-period compare (same duration immediately before)
cur_days = (pd.to_datetime(cur_end) - pd.to_datetime(cur_start)).days + 1
prev_end = (pd.to_datetime(cur_start) - pd.Timedelta(days=1)).date()
prev_start = (pd.to_datetime(cur_start) - pd.Timedelta(days=cur_days)).date()
prev = apply_filters(df, prev_start, prev_end) if compare_prev else pd.DataFrame()


def fmt_money(x):
    return f"${x:,.0f}"


def fmt_int(x):
    return f"{int(x):,}"


# -----------------------------
# Title & KPI Row (with deltas)
# -----------------------------
st.title("💎 Global Ammolite Sales Dashboard – Advanced")

cur_total_metric = f[metric_col].sum()
cur_total_net = f["Net Sales"].sum()
cur_orders = len(f)
cur_unique = f["Customer Name"].nunique()
cur_cons_share = float(f["Is Consigned"].mean()) if cur_orders else 0.0
cur_avg_ship = float(f["Days to Ship"].dropna().mean()) if f["Days to Ship"].notna().any() else np.nan

# prev KPI
if compare_prev and not prev.empty:
    prev_total_metric = prev[metric_col].sum()
    prev_total_net = prev["Net Sales"].sum()
    prev_orders = len(prev)
    prev_unique = prev["Customer Name"].nunique()
    prev_cons_share = float(prev["Is Consigned"].mean()) if prev_orders else 0.0
    prev_avg_ship = float(prev["Days to Ship"].dropna().mean()) if prev["Days to Ship"].notna().any() else np.nan
else:
    prev_total_metric = prev_total_net = prev_orders = prev_unique = np.nan
    prev_cons_share = prev_avg_ship = np.nan

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric(
        "Total Net Sales",
        fmt_money(cur_total_net),
        delta=(None if not np.isfinite(prev_total_net) else fmt_money(cur_total_net - prev_total_net)),
    )

with k2:
    st.metric(
        "Total Orders",
        fmt_int(cur_orders),
        delta=(None if not np.isfinite(prev_orders) else f"{int(cur_orders - prev_orders):,}"),
    )

with k3:
    st.metric(
        "Unique Customers",
        fmt_int(cur_unique),
        delta=(None if not np.isfinite(prev_unique) else f"{int(cur_unique - prev_unique):,}"),
    )

with k4:
    st.metric(
        "Consigned Share",
        f"{cur_cons_share*100:,.1f}%",
        delta=(None if not np.isfinite(prev_cons_share) else f"{(cur_cons_share - prev_cons_share)*100:,.1f}%"),
    )

with k5:
    if np.isfinite(cur_avg_ship):
        st.metric(
            "Avg Days to Ship",
            f"{cur_avg_ship:,.1f}",
            delta=(None if not np.isfinite(prev_avg_ship) else f"{(cur_avg_ship - prev_avg_ship):,.1f}"),
        )
    else:
        st.metric("Avg Days to Ship", "—")

st.caption(
    f"Filtered view: **{cur_start} → {cur_end}**"
    + (f" (compared to **{prev_start} → {prev_end}**)" if compare_prev else "")
)
st.markdown("---")

# ----------------------------------------------------
# TAB: Overview (more advanced)
# -----------------------------
if page == 'Overview':
    st.subheader("Executive Overview")

    c1, c2 = st.columns([1.6, 1])

    # Trend line with granularity
    with c1:
        gran = st.radio("Trend granularity", ["Daily", "Weekly", "Monthly"], horizontal=True, key="ov_gran")
        if gran == "Daily":
            ts = f.groupby("Date", as_index=False)[metric_col].sum().sort_values("Date")
            xcol = "Date"
        elif gran == "Weekly":
            ts = f.groupby("Week", as_index=False)[metric_col].sum().sort_values("Week")
            xcol = "Week"
        else:
            ts = f.groupby("Month", as_index=False)[metric_col].sum().sort_values("Month")
            xcol = "Month"

        if not ts.empty:
            ts["Rolling"] = ts[metric_col].rolling(3, min_periods=1).mean()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts[xcol], y=ts[metric_col], mode="lines+markers", name=metric_label))
            fig.add_trace(go.Scatter(x=ts[xcol], y=ts["Rolling"], mode="lines", name="3-period avg"))
            fig.update_layout(title=f"{metric_label} Trend", xaxis_title="", yaxis_title=metric_label)
            fig = style_fig(fig, height=420)
            st.plotly_chart(fig, use_container_width=True, key=pkey("ov_trend"))

    # Pareto: Top countries share
    with c2:
        by_country = f.groupby("Country", as_index=False)[metric_col].sum().sort_values(metric_col, ascending=False)
        if not by_country.empty:
            topn = st.slider("Pareto top N", 5, 25, 10, key="ov_pareto_n")
            pareto = by_country.head(topn).copy()
            total = by_country[metric_col].sum()
            pareto["Share"] = pareto[metric_col] / total if total else 0
            pareto["CumShare"] = pareto["Share"].cumsum()

            fig = go.Figure()
            fig.add_trace(go.Bar(x=pareto["Country"], y=pareto[metric_col], name=metric_label))
            fig.add_trace(
                go.Scatter(
                    x=pareto["Country"],
                    y=pareto["CumShare"],
                    name="Cumulative share",
                    yaxis="y2",
                    mode="lines+markers",
                )
            )
            fig.update_layout(
                title=f"Pareto – Top {topn} Countries",
                xaxis_title="",
                yaxis_title=metric_label,
                yaxis2=dict(title="Cumulative share", overlaying="y", side="right", tickformat=".0%"),
            )
            fig = style_fig(fig, height=420)
            st.plotly_chart(fig, use_container_width=True, key=pkey("ov_pareto"))

    st.markdown("#### Snapshot: Top Performers")
    c3, c4, c5 = st.columns(3)

    with c3:
        by_channel = f.groupby("Channel", as_index=False)[metric_col].sum().sort_values(metric_col, ascending=False)
        fig = px.bar(by_channel, x="Channel", y=metric_col, text_auto=".2s", title=f"{metric_label} by Channel")
        fig.update_layout(xaxis_title="", yaxis_title=metric_label)
        fig = style_fig(fig, height=380)
        st.plotly_chart(fig, use_container_width=True, key=pkey("ov_channel"))

    with c4:
        if safe_col(f, "Product Type"):
            by_prod = (
                f.groupby("Product Type", as_index=False)[metric_col]
                .sum()
                .sort_values(metric_col, ascending=False)
                .head(12)
            )
            fig = px.bar(
                by_prod,
                x=metric_col,
                y="Product Type",
                orientation="h",
                text_auto=".2s",
                title=f"Top Product Types by {metric_label}",
            )
            fig.update_layout(xaxis_title=metric_label, yaxis_title="")
            fig = style_fig(fig, height=380)
            st.plotly_chart(fig, use_container_width=True, key=pkey("ov_prod"))
        else:
            st.info("No 'Product Type' column found.")

    with c5:
        seg = f.groupby("Customer Type", as_index=False)[metric_col].sum().sort_values(metric_col, ascending=False)
        fig = px.pie(seg, names="Customer Type", values=metric_col, hole=0.35, title=f"{metric_label} Share by Customer Type")
        fig = style_fig(fig, height=380)
        st.plotly_chart(fig, use_container_width=True, key=pkey("ov_seg"))

    # Auto insights
    top_country = by_country["Country"].iloc[0] if not by_country.empty else "N/A"
    top_channel = by_channel["Channel"].iloc[0] if not by_channel.empty else "N/A"
    share_top = float(by_country[metric_col].iloc[0] / by_country[metric_col].sum()) if by_country[metric_col].sum() > 0 else np.nan

    st.markdown("### Key Takeaways")
    bullets = []
    if np.isfinite(share_top):
        bullets.append(f"- **{top_country}** is #1, contributing **{share_top*100:.1f}%** of {metric_label.lower()} in this view.")
    bullets.append(f"- **{top_channel}** is the leading channel for the selected filters.")
    if np.isfinite(cur_avg_ship):
        bullets.append(f"- Average time to ship is **{cur_avg_ship:.1f} days** (use *Inventory Timing* to see channel differences).")
    bullets.append("- Use *Price Drivers* to see which attributes push price up/down, and *Compliance* to spot risk gaps.")
    st.markdown("\n".join(bullets))
# -----------------------------
# TAB: Price Drivers / Visualization (5 tabs + 9 visuals)
# -----------------------------
if page == 'Price Drivers':
    st.subheader("Price Drivers / Visualization")
    p_df = f.copy()

    # Revenue (total sales value): prefer Net Sales, else Price
    if safe_col(p_df, "Net Sales"):
        revenue_col = "Net Sales"
    elif safe_col(p_df, "Price (CAD)"):
        revenue_col = "Price (CAD)"
    else:
        revenue_col = metric_col  # fallback

    # Unit price (average price): prefer Price (CAD), else revenue_col
    price_col = "Price (CAD)" if safe_col(p_df, "Price (CAD)") else revenue_col

    # Make Year + Month robust for grouping
    if safe_col(p_df, "Year"):
        p_df["_YearNum"] = pd.to_numeric(p_df["Year"], errors="coerce")
    else:
        p_df["_YearNum"] = np.nan

    if safe_col(p_df, "Month"):
        if pd.api.types.is_datetime64_any_dtype(p_df["Month"]):
            p_df["_MonthNum"] = p_df["Month"].dt.month
        else:
            p_df["_MonthNum"] = pd.to_numeric(p_df["Month"], errors="coerce")
    else:
        p_df["_MonthNum"] = np.nan

    # Most recent year in filtered view
    year_pick = (
        int(p_df["_YearNum"].dropna().max())
        if safe_col(p_df, "_YearNum") and p_df["_YearNum"].notna().any()
        else None
    )
    p_year = p_df[p_df["_YearNum"] == year_pick].copy() if year_pick is not None else p_df.copy()

    month_ticks = list(range(1, 13))
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # 5 Tabs
    t1, t2, t3, t4, t5 = st.tabs(
        [
            "Average Price by Product Type & Grade",
            "Sales Performance by Dominant Color",
            "Monthly Sales Value vs Average Price Trend",
            "Monthly Total Sales Value Trend (Revenue)",
            "Next Fiscal Year Seasonal Forecast (30% Growth)",
        ]
    )

    # -----------------------------
    # TAB 1 (1 visual)
    # Average Price by Product Type & Grade
    # -----------------------------
    with t1:
        if safe_col(p_df, "Product Type") and safe_col(p_df, "Grade") and safe_col(p_df, price_col):
            tmp = p_df.dropna(subset=["Product Type", "Grade", price_col]).copy()

            avg_ptg = (
                tmp.groupby(["Product Type", "Grade"], as_index=False)
                .agg(
                    Avg_Price=(price_col, "mean"),
                    Num_Sales=(price_col, "count"),
                )
            )

            fig = px.bar(
                avg_ptg,
                x="Product Type",
                y="Avg_Price",
                color="Grade",
                barmode="group",
                title="Average Price by Product Type & Grade",
                hover_data={"Num_Sales": True, "Avg_Price": ":,.0f"},
            )
            
            fig = style_fig(fig, height=520)
            fig.update_layout(
                xaxis_title="Product Type", 
                yaxis_title="Avg Price (CAD)",
                legend_title_text ="Product Grade",
                legend = dict( orientation ="h",yanchor="bottom",y=1.05,xanchor="right",x=0.5
                ),
                margin=dict(t=150)
                
            )
            fig.update_yaxes(tickprefix="$", separatethousands=True)
            fig.update_xaxes(tickangle=-25)
            st.plotly_chart(fig, use_container_width=True, key=pkey("pd_viz_tab1"))

            with st.expander("Insights - Average Price by Product Type & Grade", expanded=False):
                st.markdown(
                    """
**Insights:** Shows how discounting relates to net sale value and highlights if large discounts are driving larger baskets.

**Why it helps:** Helps manage promotions without unintentionally eroding margins.

**Recommendations:**  
- If discounts don’t meaningfully lift net sale value, reduce discount depth or tighten eligibility.  
- Create tiered offers (e.g., discounts only above certain cart values) to protect profitability.
"""
                )

            st.divider()
        else:
            st.info("Missing required columns for this chart (need Product Type, Grade, and a price column).")
    # -----------------------------
    # TAB 2 (2 visuals)
    # Sales Performance by Dominant Color
    # -----------------------------
    with t2:
        st.markdown("### Sales Performance by Dominant Color")

        if safe_col(p_df, "Dominant Color") and safe_col(p_df, revenue_col) and safe_col(p_df, price_col):
            tmp = p_df.dropna(subset=["Dominant Color"]).copy()

            dom = (
                tmp.groupby("Dominant Color", as_index=False)
                .agg(
                    Total_Revenue=(revenue_col, "sum"),
                    Avg_Price=(price_col, "mean"),
                )
            )

            dom_rev = dom.sort_values("Total_Revenue", ascending=False)
            dom_avg = dom.sort_values("Avg_Price", ascending=False)

            c1, c2 = st.columns(2)

            with c1:
                fig1 = px.bar(
                    dom_rev,
                    x="Dominant Color",
                    y="Total_Revenue",
                    color="Dominant Color",
                    title="Total Revenue by Dominant Color",
                )
                fig1.update_layout(showlegend= False, xaxis_title="Dominant Color", yaxis_title="Total Sales Value (CAD)",margin=dict(t=80))
                fig1.update_yaxes(tickprefix="$", separatethousands=True)
                fig1.update_xaxes(tickangle=-60)
                fig1 = style_fig(fig1, height=470)
                st.plotly_chart(fig1, use_container_width=True, key=pkey("pd_viz_tab2_rev"))

            with c2:
                fig2 = px.bar(
                    dom_avg,
                    x="Dominant Color",
                    y="Avg_Price",
                    color="Dominant Color",
                    title="Average Price by Dominant Color",
                )
                fig2.update_layout(showlegend= False, xaxis_title="Dominant Color", yaxis_title="Average Price (CAD)",margin=dict(t=80))
                fig2.update_yaxes(tickprefix="$", separatethousands=True)
                fig2.update_xaxes(tickangle=-60)
                fig2 = style_fig(fig2, height=470)
                st.plotly_chart(fig2, use_container_width=True, key=pkey("pd_viz_tab2_avg"))

            with st.expander("Insights - Sales Performance by Dominant Color", expanded=False):
                st.markdown(
                    """
**Insights:** Two Graphs shown the relationship between High Volume-Lower Price (Mass Market Leader), Low Volume-High Price (Luxury)and High Value Performer(Sweet Spot) if they both high performing. This Focal point of the Total Market Performances.

**Recommendations:** - Market Leader: Test a Small price increase to boost profit on high volume 
- Luxury: Maintain high price and controlled and explore selective expansion
- Sweet Spot : Invest more and replicate its successful strategy across the product line
- Underperformer: Liquidate stock and cut resources.
"""
                )

            st.divider()
        else:
            st.info("Missing 'Dominant Color' or required price/revenue columns for this tab.")

    # -----------------------------
    # TAB 3 (2 visuals)
    # Monthly Sales Value Vs Average price trend
    # -----------------------------
    with t3:
        st.markdown("### Monthly Average Price and Total Revenue by Color Count")

        if year_pick is None or not safe_col(p_year, "_MonthNum") or p_year["_MonthNum"].notna().sum() == 0:
            st.info("Missing Month/Year info to build monthly trends.")
        else:
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("#### Monthly Average Price (CAD) Trend")
                if safe_col(p_year, "Color Count (#)") and safe_col(p_year, price_col):
                    cc = p_year.dropna(subset=["_MonthNum", "Color Count (#)", price_col]).copy()
                    cc["Color Count (#)"] = pd.to_numeric(cc["Color Count (#)"], errors="coerce").round(0).astype("Int64").astype(str)
                    g2 = cc.groupby(["_MonthNum", "Color Count (#)"], as_index=False).agg(Avg_Price=(price_col, "mean")).sort_values("_MonthNum")
                    fig2 = px.line(g2, x="_MonthNum", y="Avg_Price", color="Color Count (#)", markers=True)
                    fig2 = style_fig(fig2, height=500)
                    fig2.update_layout(
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
                        margin=dict(t=50, b=100, l=10, r=10),
                        xaxis_title="Month",
                        yaxis_title="Avg Price (CAD)"
                    )
                    fig2.update_xaxes(tickmode="array", tickvals=month_ticks, ticktext=month_labels)
                    st.plotly_chart(fig2, use_container_width=True, key="tab3_p_final_no_comm")

            with c2:
                st.markdown("#### Monthly Total Sales Value (CAD) Trend")
                if safe_col(p_year, "Color Count (#)") and safe_col(p_year, revenue_col):
                    cc_rev = p_year.dropna(subset=["_MonthNum", "Color Count (#)", revenue_col]).copy()
                    cc_rev["Color Count (#)"] = pd.to_numeric(cc_rev["Color Count (#)"], errors="coerce")
                    cc_rev = cc_rev[cc_rev["Color Count (#)"].between(1, 7)]
                    cr = cc_rev.groupby(["_MonthNum", "Color Count (#)"], as_index=False).agg(Total_Sales=(revenue_col, "sum")).sort_values("_MonthNum")
                    cr["Color Count (#)"] = cr["Color Count (#)"].astype(int).astype(str)

                    fig_rev = px.line(cr, x="_MonthNum", y="Total_Sales", color="Color Count (#)", markers=True)
                    fig_rev = style_fig(fig_rev, height=500)
                    fig_rev.update_layout(
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
                        margin=dict(t=50, b=100, l=10, r=10),
                        xaxis_title="Month",
                        yaxis_title="Total Sales (CAD)"
                    )
                    fig_rev.update_xaxes(tickmode="array", tickvals=month_ticks, ticktext=month_labels)
                    st.plotly_chart(fig_rev, use_container_width=True, key="tab3_s_final_no_comm")

            with st.expander("Insights - Monthly Trends", expanded=False):
                st.markdown("""
                ### Insights & Recommendations
                **Price Power:** Products with higher color counts command higher average prices.
                **Action:** Emphasize color richness in marketing for high-margin growth.
                """)
                st.divider()
    # -----------------------------
    # TAB 4 (3 visuals)
    # Monthly Total Sales Value Trend (Revenue)
    # -----------------------------
    with t4:
        st.markdown("### Monthly Total Sales Value Trend")

        if safe_col(p_year, "_MonthNum") and safe_col(p_year, revenue_col):
            overall = (
                p_year.dropna(subset=["_MonthNum", revenue_col])
                .groupby("_MonthNum", as_index=False)
                .agg(Total_Sales=(revenue_col, "sum"))
                .sort_values("_MonthNum")
            )
            
            fig3 = px.line(
                overall,
                x="_MonthNum",
                y="Total_Sales",
                markers=True,
                title="Overall Total Sales Value Trend"
            )
            
            fig3.update_yaxes(tickprefix="$", separatethousands=True)
            fig3.update_xaxes(tickmode="array", tickvals=month_ticks, ticktext=month_labels)
            
            # Apply style first
            fig3 = style_fig(fig3, height=520)
            
            # Final layout overrides
            fig3.update_layout(
                xaxis_title=f"Month ({year_pick})",
                yaxis_title="Total Sales Value (CAD)",
                margin=dict(t=50, b=50, l=10, r=10)
            )
            
            st.plotly_chart(fig3, use_container_width=True, key="tab4_overall_trend_final")
        else:
            st.info("Need a revenue column to plot the overall trend.")

        with st.expander("Insights - Monthly Revenue Trends", expanded=False):
            st.markdown(
                """
### Overall Total Sales Value Trend
**Insights:**
- Provides a macro view of total revenue performance over time.
- Reveals seasonality, growth cycles, and potential slowdowns.

**Recommendations:**
- Leverage peak periods for premium pricing and stock optimization.
- Use low-demand periods for clearance strategies or supplier renegotiation.
"""
            )

        st.divider()
    # -----------------------------
    # TAB 5 (1 visual, 2-panel layout)
    # Next Fiscal Year Seasonal Forecast Model (30% Growth)
    # -----------------------------
    with t5:
        st.markdown("### Next Fiscal Year Seasonal Forecast Model (30% Growth)")
        st.caption("Assumes the next year ranges between repeating last year’s seasonality (lower bound) and +30% growth (upper bound).")

        req_ok = (
            safe_col(p_df, "Product Type")
            and safe_col(p_df, "Grade")
            and safe_col(p_df, price_col)
            and safe_col(p_df, "_MonthNum")
            and safe_col(p_df, "_YearNum")
        )

        if req_ok:
            left, right = st.columns(2)

            prod_opts = sorted([x for x in p_df["Product Type"].dropna().unique().tolist() if str(x).strip() != ""])
            grade_opts = sorted([x for x in p_df["Grade"].dropna().unique().tolist() if str(x).strip() != ""])

            sel_prod = st.selectbox("Select Product Type:", options=prod_opts, key="pd_fc_prod")
            sel_grade = st.selectbox("Select Grade:", options=grade_opts, key="pd_fc_grade")

            sub = p_df[(p_df["Product Type"] == sel_prod) & (p_df["Grade"] == sel_grade)].copy()

            if sub.empty:
                st.info("No rows match that Product Type + Grade under current filters.")
            else:
                base_year = int(sub["_YearNum"].dropna().max())
                forecast_year = base_year + 1

                # Actual series (base year) on month numbers
                actual = (
                    sub[sub["_YearNum"] == base_year]
                    .dropna(subset=["_MonthNum", price_col])
                    .groupby("_MonthNum", as_index=False)
                    .agg(Avg_Price=(price_col, "mean"))
                    .sort_values("_MonthNum")
                )

                # Ensure 12-month frame
                actual_full = pd.DataFrame({"_MonthNum": month_ticks}).merge(actual, on="_MonthNum", how="left")

                # Forecast: repeat seasonality (lower) + 30% growth (upper)
                fc = actual_full.copy()
                fc["Lower Bound"] = fc["Avg_Price"]
                fc["Upper Bound"] = fc["Avg_Price"] * 1.30

                with left:
                    fig_a = px.line(
                        actual_full,
                        x="_MonthNum",
                        y="Avg_Price",
                        markers=True,
                        title=f"Actual Monthly Average Price ({base_year})<br>{sel_prod} ({sel_grade})",
                    )
                    fig_a.update_layout(xaxis_title="Month", yaxis_title="Average Price (CAD)")
                    fig_a.update_yaxes(tickprefix="$", separatethousands=True)
                    fig_a.update_xaxes(tickmode="array", tickvals=month_ticks, ticktext=month_labels)
                    fig_a = style_fig(fig_a, height=520)
                    st.plotly_chart(fig_a, use_container_width=True, key=pkey("pd_fc_actual"))

                with right:
                    fig_f = go.Figure()
                    fig_f.add_trace(
                        go.Scatter(
                            x=fc["_MonthNum"],
                            y=fc["Lower Bound"],
                            mode="lines+markers",
                            name=f"{forecast_year} Forecast: Lower Bound",
                        )
                    )
                    fig_f.add_trace(
                        go.Scatter(
                            x=fc["_MonthNum"],
                            y=fc["Upper Bound"],
                            mode="lines+markers",
                            name=f"{forecast_year} Forecast: Upper Bound",
                        )
                    )
                    fig_f.update_layout(
                        title=f"Forecast Monthly Average Price ({forecast_year})",
                        xaxis_title="Month",
                        yaxis_title="Average Price (CAD)",
                    )
                    fig_f.update_yaxes(tickprefix="$", separatethousands=True)
                    fig_f.update_xaxes(tickmode="array", tickvals=month_ticks, ticktext=month_labels)
                    fig_f = style_fig(fig_f, height=520)
                    st.plotly_chart(fig_f, use_container_width=True, key=pkey("pd_fc_forecast"))

            with st.expander("Insights - Next Fiscal Year Forecast", expanded=False):
                st.markdown(
                    """
- The forecast shows expected seasonal peaks and dips across the next fiscal year, highlighting when demand is likely to rise or soften.
- The uncertainty band (lower vs upper bound) widens in some months, indicating higher volatility and less predictable sales periods.
- Months with consistently higher forecast values suggest stronger seasonal demand that can be planned for ahead of time.

**Recommendations:**
- Align inventory and procurement ahead of forecasted peak months to reduce stockouts and missed revenue.
- Use the lower-bound scenario for budgeting and cash-flow planning, and treat the upper bound as an upside target for stretch planning.
- Increase marketing/promo activity in months where the forecast dips to stabilize sales and improve capacity utilization.
- Track forecast error monthly and retrain/update the model regularly as new sales data arrives to keep seasonality patterns accurate.
"""
                )

            st.divider()
        else:
            st.info("Missing required columns for forecasting (need Product Type, Grade, Month, Year, and a price column).")
    #### -----------------------------
    # TAB 5 (2 visual, 2-panel layout)
    # Next Fiscal Year Total Sales Revenue Forecast (30% Growth)
    # -----------------------------
        with t5:
            st.markdown("### Next Fiscal Year Total Revenue Forecast (30% Growth)")
            
            req_ok = (
                safe_col(p_df, "Product Type")
                and safe_col(p_df, "Grade")
                and safe_col(p_df, revenue_col)
                and safe_col(p_df, "_MonthNum")
                and safe_col(p_df, "_YearNum")
            )
    
            if req_ok:
                prod_opts = sorted([x for x in p_df["Product Type"].dropna().unique().tolist() if str(x).strip() != ""])
                grade_opts = sorted([x for x in p_df["Grade"].dropna().unique().tolist() if str(x).strip() != ""])
    
                c_sel1, c_sel2 = st.columns(2)
                with c_sel1:
                    sel_prod = st.selectbox("Select Product Type:", options=prod_opts, key="rev_fc_prod_final")
                with c_sel2:
                    sel_grade = st.selectbox("Select Grade:", options=grade_opts, key="rev_fc_grade_final")
    
                sub = p_df[(p_df["Product Type"] == sel_prod) & (p_df["Grade"] == sel_grade)].copy()
    
                if sub.empty:
                    st.info("No rows match that Product Type + Grade.")
                else:
                    base_year = int(sub["_YearNum"].dropna().max())
                    forecast_year = base_year + 1
    
                    
                    actual_rev = (
                        sub[sub["_YearNum"] == base_year]
                        .dropna(subset=["_MonthNum", revenue_col])
                        .groupby("_MonthNum", as_index=False)
                        .agg(Total_Rev=(revenue_col, "sum")) 
                        .sort_values("_MonthNum")
                    )
    
                    actual_full = pd.DataFrame({"_MonthNum": month_ticks}).merge(actual_rev, on="_MonthNum", how="left")
    
                   
                    fc_rev = actual_full.copy()
                    fc_rev["Lower Bound"] = fc_rev["Total_Rev"]
                    fc_rev["Upper Bound"] = fc_rev["Total_Rev"] * 1.30
    
                    left, right = st.columns(2)
    
                    with left:
                        fig_a = px.line(
                            actual_full,
                            x="_MonthNum",
                            y="Total_Rev",
                            markers=True,
                            title=f"Actual Total Revenue Sum ({base_year})"
                        )
                        fig_a = style_fig(fig_a, height=520)
                        fig_a.update_layout(
                            xaxis_title="Month", 
                            yaxis_title="Total Revenue (Sum CAD)",
                            margin=dict(t=80, b=50)
                        )
                        fig_a.update_yaxes(tickprefix="$", separatethousands=True)
                        fig_a.update_xaxes(tickmode="array", tickvals=month_ticks, ticktext=month_labels)
                        st.plotly_chart(fig_a, use_container_width=True, key="rev_sum_actual_viz")
    
                    with right:
                        fig_f = go.Figure()
                        fig_f.add_trace(go.Scatter(
                            x=fc_rev["_MonthNum"], y=fc_rev["Lower Bound"],
                            mode="lines+markers", name="Base Revenue (Last Year Sum)",
                            line=dict(dash='dash')
                        ))
                        fig_f.add_trace(go.Scatter(
                            x=fc_rev["_MonthNum"], y=fc_rev["Upper Bound"],
                            mode="lines+markers", name="Growth Target (+30% Sum)"
                        ))
                        fig_f = style_fig(fig_f, height=520)
                        fig_f.update_layout(
                            title=f"Total Revenue Forecast ({forecast_year})",
                            xaxis_title="Month",
                            yaxis_title="Total Revenue (Sum CAD)",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                            margin=dict(t=80, b=50)
                        )
                        fig_f.update_yaxes(tickprefix="$", separatethousands=True)
                        fig_f.update_xaxes(tickmode="array", tickvals=month_ticks, ticktext=month_labels)
                        st.plotly_chart(fig_f, use_container_width=True, key="rev_sum_forecast_viz")
    
                st.divider()

# ======================
# TAB: PRODUCT MIX ✅ (ONLY shows inside Product Mix tab)
# ======================
if page == 'Product Mix':
    st.header("🧩 Product Mix")

    # ✅ FIX: Directly use the filtered dataframe 'f' from master dashboard
    # This ensures sidebar filters work properly
    pm_df = f.copy()

    # ---- Safety: required columns + numeric cleanup ----
    for col in ["Price (CAD)", "Discount (CAD)"]:
        if col in pm_df.columns:
            pm_df[col] = pd.to_numeric(pm_df[col], errors="coerce").fillna(0)
        else:
            pm_df[col] = 0

    if "Sale ID" not in pm_df.columns:
        pm_df["Sale ID"] = np.arange(len(pm_df)) + 1

    for col in ["Product Type", "Grade", "Species"]:
        if col not in pm_df.columns:
            pm_df[col] = "Unknown"
        pm_df[col] = pm_df[col].fillna("Unknown")

    # Optional fallback CSS
    st.markdown(
        """
        <style>
        .insight-box{
            padding: 14px 16px;
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 12px;
            background: rgba(0,0,0,0.02);
            margin: 8px 0 14px 0;
        }
        .recommendation-box{
            padding: 14px 16px;
            border: 1px solid rgba(0,0,0,0.10);
            border-radius: 12px;
            background: rgba(255, 193, 7, 0.10);
            margin: 8px 0 14px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Create sub-tabs for Product Mix section (NO ICONS as requested)
    pm_tabs = st.tabs([
        "Overview",
        "Interactive Treemap",
        "Revenue Analysis",
        "Pricing Analysis",
        "Efficiency Metrics",
        "Strategic Insights"
    ])

    # =====================================================
    # TAB 1: OVERVIEW (NO CHARTS - removed as requested)
    # =====================================================
    with pm_tabs[0]:
        st.subheader("Executive Summary")

        col1, col2, col3, col4 = st.columns(4)

        total_rev = pm_df["Price (CAD)"].sum()
        total_sales = len(pm_df)
        avg_txn = pm_df["Price (CAD)"].mean() if total_sales else 0
        mean_price = pm_df["Price (CAD)"].mean() if total_sales else 0
        mean_disc = pm_df["Discount (CAD)"].mean() if total_sales else 0
        avg_disc = (mean_disc / mean_price * 100) if mean_price else 0

        with col1:
            st.metric("Total Revenue", f"${total_rev:,.0f}", "CAD")
        with col2:
            st.metric("Total Sales", f"{total_sales:,}", "transactions")
        with col3:
            st.metric("Avg Transaction", f"${avg_txn:,.2f}")
        with col4:
            st.metric("Avg Discount", f"{avg_disc:.2f}%", "Strong pricing")

        st.markdown("---")

        # DYNAMIC KEY FINDINGS
        st.subheader("Key Findings")
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        
        # Determine pricing assessment (DYNAMIC)
        if avg_disc < 1:
            pricing_assessment = "exceptionally low"
            pricing_quality = "exceptional"
        elif avg_disc < 2:
            pricing_assessment = "very low"
            pricing_quality = "strong"
        elif avg_disc < 3:
            pricing_assessment = "low"
            pricing_quality = "good"
        else:
            pricing_assessment = "moderate"
            pricing_quality = "developing"
        
        # Determine market tier (DYNAMIC)
        if avg_txn > 5000:
            market_tier = "ultra-premium"
        elif avg_txn > 2000:
            market_tier = "premium"
        elif avg_txn > 1000:
            market_tier = "mid-tier premium"
        else:
            market_tier = "accessible"
        
        st.markdown(
            f"""
            Total revenue of **${total_rev:,.0f} CAD** across **{total_sales:,} transactions**
            with an average of **${avg_txn:,.2f}** per sale. The {pricing_assessment} discount rate of 
            **{avg_disc:.2f}%** (vs. 5-15% industry average) demonstrates {pricing_quality} brand value and 
            pricing power, positioning the business in the **{market_tier} market segment**.
            """,
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Top/Bottom product stats
        product_stats = (
            pm_df.groupby("Product Type", as_index=False)
            .agg(**{"Total Revenue": ("Price (CAD)", "sum"), "Sales Volume": ("Sale ID", "count")})
            .sort_values("Total Revenue", ascending=False)
        )

        st.markdown("---")
        colL, colR = st.columns(2)

        with colL:
            st.markdown("### Top 3 Revenue Generators")
            top3_revenue = product_stats.head(3)
            for _, row in top3_revenue.iterrows():
                pct = (row["Total Revenue"] / total_rev * 100) if total_rev else 0
                st.metric(row["Product Type"], f"${row['Total Revenue']:,.0f}", f"{pct:.1f}% of total")

            st.markdown("### Top 3 Volume Leaders")
            top3_volume = product_stats.sort_values("Sales Volume", ascending=False).head(3)
            for _, row in top3_volume.iterrows():
                pct = (row["Sales Volume"] / total_sales * 100) if total_sales else 0
                st.metric(row["Product Type"], f"{int(row['Sales Volume']):,} sales", f"{pct:.1f}% of volume")

        with colR:
            st.markdown("### Bottom 3 Revenue Generators")
            bottom3_revenue = product_stats.tail(3).sort_values("Total Revenue", ascending=True)
            for _, row in bottom3_revenue.iterrows():
                pct = (row["Total Revenue"] / total_rev * 100) if total_rev else 0
                st.metric(row["Product Type"], f"${row['Total Revenue']:,.0f}", f"{pct:.1f}% of total")

            st.markdown("### Bottom 3 Volume Leaders")
            bottom3_volume = product_stats.sort_values("Sales Volume", ascending=True).head(3)
            for _, row in bottom3_volume.iterrows():
                pct = (row["Sales Volume"] / total_sales * 100) if total_sales else 0
                st.metric(row["Product Type"], f"{int(row['Sales Volume']):,} sales", f"{pct:.1f}% of volume")

        # DYNAMIC BUSINESS TAKEAWAYS
        st.markdown("---")
        st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
        st.markdown("**Business Takeaways:**\n\n")
        
        if len(product_stats) > 0:
            top_product = product_stats.iloc[0]["Product Type"]
            top_product_pct = (product_stats.iloc[0]["Total Revenue"] / total_rev * 100) if total_rev else 0
            bottom_product = product_stats.iloc[-1]["Product Type"]
            bottom_product_pct = (product_stats.iloc[-1]["Total Revenue"] / total_rev * 100) if total_rev else 0
            
            takeaways = []
            
            # Pricing takeaway (DYNAMIC)
            if avg_disc < 2:
                takeaways.append(f"The {pricing_assessment} discount rate of {avg_disc:.2f}% combined with ${avg_txn:,.0f} average transaction validates premium positioning. Current pricing strategy is highly effective - customers perceive significant value and pay full price willingly.")
            else:
                takeaways.append(f"The discount rate of {avg_disc:.2f}% combined with ${avg_txn:,.0f} average transaction indicates opportunity to strengthen pricing discipline and move toward premium positioning.")
            
            # Concentration takeaway (DYNAMIC)
            if top_product_pct > 50:
                takeaways.append(f"Critical concentration in {top_product} ({top_product_pct:.1f}% of revenue) presents significant portfolio dependency risk requiring immediate diversification strategy.")
            elif top_product_pct > 40:
                takeaways.append(f"High concentration in {top_product} ({top_product_pct:.1f}% of revenue) presents both opportunity (proven market success) and risk (portfolio dependency) requiring strategic balance.")
            elif top_product_pct > 30:
                takeaways.append(f"Moderate concentration in {top_product} ({top_product_pct:.1f}% of revenue) shows clear market leader while maintaining reasonable portfolio diversification.")
            else:
                takeaways.append(f"Well-balanced portfolio with {top_product} leading at {top_product_pct:.1f}% of revenue, indicating healthy diversification across product categories.")
            
            # Bottom performer takeaway (DYNAMIC)
            if bottom_product_pct < 2:
                takeaways.append(f"Bottom performers like {bottom_product} ({bottom_product_pct:.1f}% of revenue) require strategic evaluation for continuation or elimination based on strategic importance and margin contribution.")
            else:
                takeaways.append(f"Lower performers including {bottom_product} ({bottom_product_pct:.1f}% of revenue) contribute meaningful revenue and may serve strategic roles in customer acquisition or portfolio completeness.")
            
            st.markdown("\n\n".join(takeaways), unsafe_allow_html=True)
        else:
            st.markdown("No product data available in current filter selection.")
        
        st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================
    # TAB 2: INTERACTIVE TREEMAP (ORIGINAL COLORS RESTORED)
    # =====================================================
    with pm_tabs[1]:
        st.subheader("Interactive Product Hierarchy")

        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown(
            """
            This interactive treemap shows revenue flow **Product Type → Grade → Species**.
            Rectangle size = revenue. Click to zoom.
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ✅ RESTORED ORIGINAL COLOR SCHEME: RdYlBu_r
        fig_treemap = px.treemap(
            pm_df,
            path=["Product Type", "Grade", "Species"],
            values="Price (CAD)",
            title="Product Mix Revenue Hierarchy (Click to Zoom)",
            color="Price (CAD)",
            color_continuous_scale='RdYlBu_r',  # ✅ ORIGINAL COLOR
        )
        fig_treemap.update_layout(height=700, font=dict(size=14))
        fig_treemap.update_traces(
            textfont_size=12,
            marker=dict(line=dict(width=2, color="white"))
        )
        st.plotly_chart(fig_treemap, use_container_width=True, key=pkey("pm_tree"))

        st.markdown("---")
        if st.checkbox("View Complete Data Table", key=wkey("pm_treemap_data")):
            hierarchy_data = (
                pm_df.groupby(["Product Type", "Grade", "Species"])
                .agg(
                    **{
                        "Total Revenue": ("Price (CAD)", "sum"),
                        "Sales Count": ("Price (CAD)", "count"),
                        "Avg Price": ("Price (CAD)", "mean"),
                    }
                )
                .round(2)
                .sort_values("Total Revenue", ascending=False)
            )
            st.dataframe(hierarchy_data, use_container_width=True)

    # =====================================================
    # TAB 3: REVENUE ANALYSIS (REMOVED Individual Product Breakdowns)
    # =====================================================
    with pm_tabs[2]:
        st.subheader("Revenue Deep Dive")
        
        st.markdown("### Total Revenue by Grade")

        grade_revenue = (
            pm_df.groupby("Grade", as_index=False)
            .agg(Revenue=("Price (CAD)", "sum"), Sales=("Sale ID", "count"))
        )
        total_grade_rev = grade_revenue["Revenue"].sum()
        grade_revenue["Percentage"] = ((grade_revenue["Revenue"] / total_grade_rev) * 100).round(1) if total_grade_rev else 0
        grade_revenue = grade_revenue.sort_values("Revenue", ascending=False)

        # ✅ ORIGINAL COLORS: Viridis
        fig_grade = px.bar(
            grade_revenue,
            x="Grade",
            y="Revenue",
            title="Total Revenue by Grade",
            text="Percentage",
            color="Revenue",
            color_continuous_scale='Viridis',  # ✅ ORIGINAL COLOR
        )
        fig_grade.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_grade.update_layout(height=500, xaxis_title="Grade", yaxis_title="Revenue (CAD)", showlegend=False)
        st.plotly_chart(fig_grade, use_container_width=True, key=pkey("pm_grade"))

        # DYNAMIC INSIGHT
        if not grade_revenue.empty:
            top = grade_revenue.iloc[0]
            st.markdown('<div class="insight-box">', unsafe_allow_html=True)
            st.markdown(
                f"""
                Grade {top['Grade']} generates **${top['Revenue']:,.0f}** ({top['Percentage']:.1f}% of total), 
                leading revenue contribution. This grade represents the optimal balance of quality, pricing, and market demand, 
                making it the strategic sweet spot for product development and inventory focus.
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================
    # TAB 4: PRICING ANALYSIS (REMOVED Price Distribution by Grade)
    # =====================================================
    with pm_tabs[3]:
        st.subheader("Pricing Structure Analysis")
        
        st.markdown("### Price Distribution by Product Type")

        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown(
            """
            Violin plots show the full price distribution for each product type.
            Wider areas = more transactions at that price.
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        fig_violin = go.Figure()
        for pt in sorted(pm_df["Product Type"].dropna().unique()):
            data = pm_df.loc[pm_df["Product Type"] == pt, "Price (CAD)"]
            if len(data) > 0:
                fig_violin.add_trace(go.Violin(
                    y=data,
                    name=str(pt),
                    box_visible=True,
                    meanline_visible=True,
                    opacity=0.6,
                ))
        fig_violin.update_layout(
            title="Price Distribution Across Product Types (Violin Plot)",
            yaxis_title="Price (CAD)",
            xaxis_title="Product Type",
            height=600,
            showlegend=False,
            violinmode="group",
        )
        st.plotly_chart(fig_violin, use_container_width=True, key=pkey("pm_violin_type"))

        st.markdown("---")
        if st.checkbox("View Detailed Price Statistics Table", key=wkey("pm_price_stats")):
            price_stats = (
                pm_df.groupby(["Product Type", "Grade"])["Price (CAD)"]
                .agg(["count", "mean", "median", "std", "min", "max"])
                .round(2)
                .rename(columns={"count": "Sales", "mean": "Mean", "median": "Median", "std": "Std Dev", "min": "Min", "max": "Max"})
                .sort_values("Mean", ascending=False)
            )
            st.dataframe(price_stats, use_container_width=True)

    # =====================================================
    # TAB 5: EFFICIENCY METRICS (ORIGINAL COLORS)
    # =====================================================
    with pm_tabs[4]:
        st.subheader("Sales Efficiency Analysis")
        
        st.markdown("### Sales Efficiency: Volume vs Revenue")

        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown(
            """
            Efficiency = revenue per sale. Bubble chart compares volume vs revenue,
            bubble size = total revenue contribution.
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        efficiency = (
            pm_df.groupby("Product Type")
            .agg(**{"Sales": ("Sale ID", "count"), "Total Revenue": ("Price (CAD)", "sum"), "Avg Price": ("Price (CAD)", "mean")})
            .reset_index()
        )
        efficiency["Efficiency"] = efficiency["Total Revenue"] / efficiency["Sales"].replace(0, np.nan)
        efficiency["Efficiency"] = efficiency["Efficiency"].fillna(0)
        efficiency["Revenue %"] = ((efficiency["Total Revenue"] / efficiency["Total Revenue"].sum()) * 100).round(1) if efficiency["Total Revenue"].sum() else 0

        # ✅ ORIGINAL COLORS: RdYlGn
        fig_eff = px.scatter(
            efficiency,
            x="Sales",
            y="Total Revenue",
            size="Total Revenue",
            color="Efficiency",
            hover_name="Product Type",
            title="Product Efficiency Matrix: Sales Volume vs Total Revenue",
            labels={"Sales": "Number of Sales", "Total Revenue": "Total Revenue (CAD)", "Efficiency": "Revenue per Sale"},
            color_continuous_scale='RdYlGn',  # ✅ ORIGINAL COLOR
            size_max=80,
        )
        fig_eff.update_layout(height=600, xaxis_title="Sales Volume", yaxis_title="Total Revenue (CAD)")

        if not efficiency.empty:
            med_sales = efficiency["Sales"].median()
            med_rev = efficiency["Total Revenue"].median()
            fig_eff.add_hline(y=med_rev, line_dash="dash", line_color="gray", opacity=0.5)
            fig_eff.add_vline(x=med_sales, line_dash="dash", line_color="gray", opacity=0.5)

        st.plotly_chart(fig_eff, use_container_width=True, key=pkey("pm_eff_scatter"))

        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown(
            """
            **Quadrant Interpretation:**
            
            - **Top Right (Stars):** High volume + High revenue - Proven winners, scale aggressively
            - **Top Left (Premium):** Low volume + High revenue - Efficient, high-margin products
            - **Bottom Right (Volume Play):** High volume + Low revenue - Evaluate strategic value
            - **Bottom Left (Underperformers):** Low volume + Low revenue - Consider elimination
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Efficiency Rankings")

        eff_sorted = efficiency.sort_values("Efficiency", ascending=False)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Top 5 Most Efficient (Revenue per Sale)")
            for _, row in eff_sorted.head(5).iterrows():
                st.metric(row["Product Type"], f"${row['Efficiency']:,.2f}/sale", f"{row['Revenue %']:.1f}% of revenue")

        with c2:
            st.markdown("### Bottom 5 Least Efficient")
            for _, row in eff_sorted.tail(5).iterrows():
                st.metric(row["Product Type"], f"${row['Efficiency']:,.2f}/sale", f"{row['Revenue %']:.1f}% of revenue")

        st.markdown("---")
        if st.checkbox("View Efficiency Data Table", key=wkey("pm_eff_table")):
            show = eff_sorted[["Product Type", "Sales", "Total Revenue", "Efficiency", "Revenue %"]].copy()
            st.dataframe(show, use_container_width=True)

    # =====================================================
    # TAB 6: STRATEGIC INSIGHTS (DYNAMIC)
    # =====================================================
    with pm_tabs[5]:
        st.subheader("Strategic Recommendations")
        
        # Calculate metrics from FILTERED data
        total_revenue = pm_df["Price (CAD)"].sum()
        total_sales = len(pm_df)
        avg_transaction = pm_df["Price (CAD)"].mean()
        avg_disc = (pm_df["Discount (CAD)"].mean() / pm_df["Price (CAD)"].mean() * 100) if pm_df["Price (CAD)"].mean() > 0 else 0
        
        # Find dominant product
        product_revenue = pm_df.groupby("Product Type")["Price (CAD)"].sum().sort_values(ascending=False)
        top_product = product_revenue.index[0] if len(product_revenue) > 0 else "N/A"
        top_product_pct = (product_revenue.iloc[0] / total_revenue * 100) if len(product_revenue) > 0 and total_revenue > 0 else 0
        top3_pct = (product_revenue.head(3).sum() / total_revenue * 100) if len(product_revenue) >= 3 and total_revenue > 0 else 0
        
        # Find dominant grade
        if "Grade" in pm_df.columns:
            grade_revenue = pm_df.groupby("Grade")["Price (CAD)"].sum().sort_values(ascending=False)
            top_grade = grade_revenue.index[0] if len(grade_revenue) > 0 else "N/A"
            top_grade_pct = (grade_revenue.iloc[0] / total_revenue * 100) if len(grade_revenue) > 0 and total_revenue > 0 else 0
        else:
            top_grade = "N/A"
            top_grade_pct = 0
        
        # Calculate efficiency
        efficiency_calc = pm_df.groupby("Product Type").agg({
            "Sale ID": "count",
            "Price (CAD)": ["sum", "mean"]
        })
        efficiency_calc.columns = ["Sales", "Total Revenue", "Avg Price"]
        efficiency_calc["Efficiency"] = efficiency_calc["Total Revenue"] / efficiency_calc["Sales"]
        efficiency_calc = efficiency_calc.sort_values("Efficiency", ascending=False)
        
        most_efficient = efficiency_calc.index[0] if len(efficiency_calc) > 0 else "N/A"
        most_efficient_value = efficiency_calc.iloc[0]["Efficiency"] if len(efficiency_calc) > 0 else 0
        least_efficient = efficiency_calc.index[-1] if len(efficiency_calc) > 0 else "N/A"
        least_efficient_value = efficiency_calc.iloc[-1]["Efficiency"] if len(efficiency_calc) > 0 else 0
        efficiency_gap = (most_efficient_value / least_efficient_value) if least_efficient_value > 0 else 0

        with st.expander("Immediate Actions (0-3 Months)", expanded=False):
            st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
            
            # Priority 1: Pricing (DYNAMIC)
            if avg_disc < 2:
                st.markdown(f"""
                **Priority 1: Protect Pricing Power**
                - Current discount rate of {avg_disc:.2f}% is exceptional - maintain this discipline
                - Document value propositions that justify premium pricing
                - Train sales team on value-based selling vs. discount negotiations
                - **Expected Impact:** Preserve margin advantage over competitors
                """)
            else:
                st.markdown(f"""
                **Priority 1: Improve Pricing Discipline**
                - Current discount rate of {avg_disc:.2f}% is higher than optimal
                - Reduce discounting by implementing value-based pricing strategies
                - Train sales team to resist discount requests
                - **Target:** Reduce to <2% within 90 days
                - **Expected Impact:** Immediate margin improvement of {avg_disc - 1.5:.1f} percentage points
                """)
            
            # Priority 2: Supply Chain (DYNAMIC)
            if top_product_pct > 40:
                st.markdown(f"""
                **Priority 2: Secure Supply Chain**
                - {top_product} represents {top_product_pct:.1f}% of revenue - high dependency risk
                - Establish backup suppliers for {top_product} immediately
                - Increase safety stock for high-efficiency products
                - Negotiate volume commitments with key suppliers
                - **Expected Impact:** Reduce stockout risk by 50-60%
                """)
            else:
                st.markdown(f"""
                **Priority 2: Optimize Supply Chain**
                - Portfolio is well-diversified (top product: {top_product_pct:.1f}%)
                - Focus on optimizing fulfillment efficiency
                - Negotiate better terms with suppliers based on volume
                - **Expected Impact:** 5-10% cost reduction in procurement
                """)
            
            # Priority 3: Quick Wins (DYNAMIC)
            st.markdown(f"""
            **Priority 3: Quick Wins**
            - Bundle high-efficiency ({most_efficient}) with lower performers to move inventory
            - Test 10-15% price increases on top products (they have pricing power)
            - Focus sales effort on {most_efficient} (${most_efficient_value:,.0f}/sale vs ${least_efficient_value:,.0f}/sale for {least_efficient})
            - **Expected Impact:** 8-12% revenue increase with same sales effort
            """)
            
            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Short-Term Strategy (3-6 Months)", expanded=False):
            st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
            
            # Initiative 1: Portfolio Rebalancing (DYNAMIC)
            if top_product_pct > 50:
                target_pct = 40
            elif top_product_pct > 40:
                target_pct = 35
            else:
                target_pct = max(30, top_product_pct - 5)
            
            st.markdown(f"""
            **Initiative 1: Portfolio Rebalancing**
            - **Current State:** {top_product} at {top_product_pct:.1f}%, top 3 at {top3_pct:.1f}%
            - **Target:** Reduce {top_product} to <{target_pct}% within 6 months
            - **How:** Don't reduce {top_product} sales - grow other categories around it
            - Invest in 2-3 underutilized categories with growth potential
            - Develop new SKUs in proven {top_grade} grade (top revenue generator)
            - **Expected Impact:** 15-20% revenue growth from diversification
            """)
            
            # Initiative 2: Sales Force Realignment (DYNAMIC)
            st.markdown(f"""
            **Initiative 2: Sales Force Realignment**
            - **Problem:** {efficiency_gap:.0f}x efficiency gap between {most_efficient} (${most_efficient_value:,.0f}/sale) and {least_efficient} (${least_efficient_value:,.0f}/sale)
            - **Solution:** Compensate based on profit contribution, not volume
            - Create incentives for high-efficiency product sales
            - Reduce effort on low-efficiency products (automate/eliminate)
            - **Expected Impact:** 25% improvement in team productivity
            """)
            
            # Initiative 3: Customer Segmentation
            customer_count = pm_df["Customer Name"].nunique() if "Customer Name" in pm_df.columns else total_sales
            st.markdown(f"""
            **Initiative 3: Customer Segmentation**
            - Analyze {customer_count:,} customers to identify Premium vs. Value vs. Mixed buyers
            - Develop targeted strategies for each segment
            - Create VIP program for top 20% of customers
            - **Expected Impact:** 20-30% increase in customer lifetime value
            """)
            
            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Long-Term Vision (6-12 Months)", expanded=False):
            st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
            
            # Theme 1: Diversification (DYNAMIC)
            st.markdown(f"""
            **Theme 1: Sustainable Diversification**
            - **Target Portfolio Mix (12 months):**
              * Primary category ({top_product}): 35-40% (from current {top_product_pct:.1f}%)
              * Secondary categories: 40-45% distributed across 3-4 products
              * Emerging/experimental: 15-20% new product development
            
            - **Development Roadmap:**
              * Months 1-3: Research and identify growth categories
              * Months 4-6: Pilot products in selected categories
              * Months 7-9: Scale successful pilots
              * Months 10-12: Portfolio rebalancing complete
            
            - **Investment:** 15-20% of current marketing budget redirected
            - **Expected Outcome:** More resilient revenue base, no single product >40%
            """)
            
            # Theme 2: Premium Brand Evolution (DYNAMIC)
            if top_grade != "N/A":
                st.markdown(f"""
                **Theme 2: Premium Brand Evolution**
                - **Three-tier architecture:**
                  * Flagship: Top grade products, ultra-premium positioning
                  * Core: {top_grade} grade (proven sweet spot at {top_grade_pct:.1f}% of revenue)
                  * Access: Entry-level premium to attract new customers
                
                - **Pricing Strategy:**
                  * Maintain current {avg_disc:.2f}% discount discipline
                  * Implement dynamic pricing for scarcity items
                  * Value-based pricing across all tiers
                
                - **Expected Outcome:** 40% increase in customer lifetime value
                """)
            else:
                st.markdown(f"""
                **Theme 2: Premium Brand Evolution**
                - Develop clear product tiers based on price points
                - Maintain current {avg_disc:.2f}% discount discipline
                - Implement value-based pricing strategies
                - **Expected Outcome:** 30-40% increase in customer lifetime value
                """)
            
            # Theme 3: Operational Excellence (DYNAMIC)
            tech_investment = int(total_revenue * 0.01)
            tech_investment_rounded = round(tech_investment / 10000) * 10000
            
            st.markdown(f"""
            **Theme 3: Operational Excellence**
            - **Technology Investments:**
              * CRM system to track customer preferences (~${tech_investment_rounded/3:,.0f})
              * Inventory management optimized by product efficiency (~${tech_investment_rounded/3:,.0f})
              * Business intelligence dashboard for real-time decisions (~${tech_investment_rounded/3:,.0f})
            
            - **Process Improvements:**
              * Tier-based fulfillment (white-glove for {most_efficient}, automated for {least_efficient})
              * Focus resources on high-efficiency products
              * Streamline operations for volume products
            
            - **Investment:** ~${tech_investment_rounded:,.0f} in technology
            - **Expected Outcome:** 25-30% operational efficiency improvement
            """)
            
            st.markdown("</div>", unsafe_allow_html=True)

        # DYNAMIC EXECUTIVE SUMMARY
        st.markdown("---")
        st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
        
        # Calculate projections (DYNAMIC)
        projected_growth_low = total_revenue * 1.25
        projected_growth_high = total_revenue * 1.30
        total_investment = tech_investment_rounded + (total_revenue * 0.02)
        total_investment_rounded = round(total_investment / 10000) * 10000
        
        # Dynamic concentration message
        if top_product_pct > 50:
            concentration_msg = f"CRITICAL concentration ({top_product_pct:.1f}% in {top_product}) presents significant risk"
        elif top_product_pct > 40:
            concentration_msg = f"High concentration ({top_product_pct:.1f}% in {top_product}) presents both opportunity and risk"
        else:
            concentration_msg = f"Balanced portfolio with largest category at {top_product_pct:.1f}%"
        
        st.markdown(
            f"""
            ### Executive Summary
            
            **Current State:** ${total_revenue:,.0f} revenue from {total_sales:,} transactions with {avg_disc:.2f}% avg discount. 
            {concentration_msg}.
            
            **Key Strengths:**
            1. {"Exceptional" if avg_disc < 2 else "Good"} pricing discipline ({avg_disc:.2f}% discount rate)
            2. Strong performers: {top_product} leads with {top_product_pct:.1f}% of revenue
            3. Proven efficiency: {most_efficient} at ${most_efficient_value:,.0f} per sale
            4. Average transaction of ${avg_transaction:,.2f} indicates {"premium" if avg_transaction > 1000 else "mid-tier"} market positioning
            
            **Critical Risks:**
            1. {"Portfolio concentration risk" if top_product_pct > 40 else "Minimal concentration risk"}
            2. {efficiency_gap:.0f}x efficiency gap between best and worst performers
            3. {"Pricing pressure" if avg_disc > 3 else "Potential for margin erosion if discounting increases"}
            4. {"Supply chain dependency on " + top_product if top_product_pct > 40 else "Resource allocation inefficiency"}
            
            **Strategic Priorities:**
            1. **Immediate:** {"Protect" if avg_disc < 2 else "Improve"} pricing power and secure supply chain
            2. **Short-term:** {"Rebalance portfolio and" if top_product_pct > 40 else "Optimize"} align sales incentives  
            3. **Long-term:** Sustainable diversification and operational excellence
            
            **Expected Outcomes (12 Months):**
            - Revenue growth: 25-30% (${total_revenue:,.0f} → ${projected_growth_low:,.0f}-${projected_growth_high:,.0f})
            - Margin improvement: {"Maintain current excellence" if avg_disc < 2 else f"Improve by {avg_disc - 1.5:.1f}pp"}
            - Concentration: {"Reduce to <40%" if top_product_pct > 40 else "Maintain current balance"}
            - Operational efficiency: +30%
            
            **Investment Required:** ${total_investment_rounded:,.0f} | **Expected ROI:** 300-400% over 2 years
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------

    # =====================================================
    # TAB 4: PRICING ANALYSIS
    # =====================================================
    with pm_tabs[3]:
        st.subheader("💰 Pricing Structure Analysis")

        st.subheader("🎻 Price Distribution by Product Type (Violin Plot)")
        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown(
            """
            Violin plots show the full price distribution for each product type.
            Wider areas = more transactions at that price.
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        fig_violin = go.Figure()
        for pt in pm_df["Product Type"].dropna().unique():
            data = pm_df.loc[pm_df["Product Type"] == pt, "Price (CAD)"]
            fig_violin.add_trace(go.Violin(
                y=data,
                name=str(pt),
                box_visible=True,
                meanline_visible=True,
                opacity=0.6,
            ))
        fig_violin.update_layout(
            title="Price Distribution Across Product Types",
            yaxis_title="Price (CAD)",
            xaxis_title="Product Type",
            height=600,
            showlegend=False,
            violinmode="group",
        )
        st.plotly_chart(fig_violin, use_container_width=True, key=pkey("pm_violin_type"))

        st.markdown("---")
        st.subheader("🎻 Price Distribution by Grade")

        fig_violin_grade = go.Figure()
        grades = [g for g in pm_df["Grade"].dropna().unique()]
        grades = sorted(grades, key=lambda x: str(x))

        for g in grades:
            data = pm_df.loc[pm_df["Grade"] == g, "Price (CAD)"]
            fig_violin_grade.add_trace(go.Violin(
                y=data,
                name=str(g),
                box_visible=True,
                meanline_visible=True,
                opacity=0.6,
            ))

        fig_violin_grade.update_layout(
            title="Price Distribution by Ammolite Grade",
            yaxis_title="Price (CAD)",
            xaxis_title="Grade",
            height=600,
            showlegend=False,
            violinmode="group",
        )
        st.plotly_chart(fig_violin_grade, use_container_width=True, key=pkey("pm_violin_grade"))

        st.markdown("---")
        if st.checkbox("📊 View Detailed Price Statistics Table", key=wkey("pm_price_stats")):
            price_stats = (
                pm_df.groupby(["Product Type", "Grade"])["Price (CAD)"]
                .agg(["count", "mean", "median", "std", "min", "max"])
                .round(2)
                .rename(columns={"count": "Sales", "mean": "Mean", "median": "Median", "std": "Std Dev", "min": "Min", "max": "Max"})
                .sort_values("Mean", ascending=False)
            )
            st.dataframe(price_stats, use_container_width=True)

    # =====================================================
    # TAB 5: EFFICIENCY METRICS
    # =====================================================
    with pm_tabs[4]:
        st.subheader("⚡ Sales Efficiency Analysis")

        st.markdown('<div class="insight-box">', unsafe_allow_html=True)
        st.markdown(
            """
            Efficiency = revenue per sale. Bubble chart compares volume vs revenue,
            bubble size = total revenue contribution.
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        efficiency = (
            pm_df.groupby("Product Type")
            .agg(**{"Sales": ("Sale ID", "count"), "Total Revenue": ("Price (CAD)", "sum"), "Avg Price": ("Price (CAD)", "mean")})
            .reset_index()
        )
        efficiency["Efficiency"] = efficiency["Total Revenue"] / efficiency["Sales"].replace(0, np.nan)
        efficiency["Efficiency"] = efficiency["Efficiency"].fillna(0)
        efficiency["Revenue %"] = ((efficiency["Total Revenue"] / efficiency["Total Revenue"].sum()) * 100).round(1) if efficiency["Total Revenue"].sum() else 0

        fig_eff = px.scatter(
            efficiency,
            x="Sales",
            y="Total Revenue",
            size="Total Revenue",
            color="Efficiency",
            hover_name="Product Type",
            title="Sales Volume vs Revenue (Bubble Size = Total Revenue)",
            labels={"Sales": "Number of Sales", "Total Revenue": "Total Revenue (CAD)", "Efficiency": "Revenue per Sale"},
            size_max=80,
        )
        fig_eff.update_layout(height=600, xaxis_title="Sales Volume", yaxis_title="Total Revenue (CAD)")

        if not efficiency.empty:
            med_sales = efficiency["Sales"].median()
            med_rev = efficiency["Total Revenue"].median()
            fig_eff.add_hline(y=med_rev, line_dash="dash", line_color="gray", opacity=0.5)
            fig_eff.add_vline(x=med_sales, line_dash="dash", line_color="gray", opacity=0.5)

        st.plotly_chart(fig_eff, use_container_width=True, key=pkey("pm_eff_scatter"))

        st.markdown("---")
        st.subheader("📊 Efficiency Rankings")

        eff_sorted = efficiency.sort_values("Efficiency", ascending=False)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🏆 Top 5 Most Efficient")
            for _, row in eff_sorted.head(5).iterrows():
                st.metric(row["Product Type"], f"${row['Efficiency']:,.2f}/sale", f"{row['Revenue %']:.1f}% of revenue")

        with c2:
            st.markdown("### ⚠️ Bottom 5 Least Efficient")
            for _, row in eff_sorted.tail(5).iterrows():
                st.metric(row["Product Type"], f"${row['Efficiency']:,.2f}/sale", f"{row['Revenue %']:.1f}% of revenue")

        st.markdown("---")
        if st.checkbox("📊 View Efficiency Data Table", key=wkey("pm_eff_table")):
            show = eff_sorted[["Product Type", "Sales", "Total Revenue", "Efficiency", "Revenue %"]].copy()
            st.dataframe(show, use_container_width=True)

    # =====================================================
    # TAB 6: STRATEGIC INSIGHTS
    # =====================================================
    with pm_tabs[5]:
        st.subheader("🎯 Strategic Recommendations")

        fossil_revenue = pm_df.loc[pm_df["Product Type"] == "Fossil", "Price (CAD)"].sum() if (pm_df["Product Type"] == "Fossil").any() else 0
        total_revenue = pm_df["Price (CAD)"].sum()
        fossil_pct = (fossil_revenue / total_revenue * 100) if total_revenue else 0

        with st.expander("🚀 Immediate Actions (0-3 Months)", expanded=False):
            st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
            st.markdown(
                """
                **Priority 1: Protect Pricing Power**
                - Maintain low discounting; reinforce value-based selling
                - Document/standardize premium value propositions
                - Train team to avoid discount-led negotiations

                **Priority 2: Secure Supply Chain**
                - Backup suppliers for top revenue categories
                - Safety stock for high-efficiency items

                **Priority 3: Quick Wins**
                - Bundle high + low efficiency products
                - Test selective price increases on inelastic premium items
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("📈 Short-Term Strategy (3-6 Months)", expanded=False):
            st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
            st.markdown(
                """
                **Portfolio Rebalancing**
                - Reduce dependency on the top category by growing 2–3 secondary categories
                - Expand SKUs where Grade/price shows strong demand

                **Sales Force Alignment**
                - Incentivize profit contribution, not just volume
                - Reduce effort on low-efficiency products

                **Customer Segmentation**
                - Identify premium vs volume buyers and tailor offers
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("🎯 Long-Term Vision (6-12 Months)", expanded=False):
            st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
            st.markdown(
                """
                **Sustainable Diversification**
                - Build a balanced portfolio mix to lower concentration risk

                **Premium Brand Evolution**
                - Clear tiering: Flagship / Core / Access-premium

                **Operational Excellence**
                - Upgrade CRM + inventory + BI workflows for scale
                """,
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
        st.markdown(
            f"""
            ### 📋 Executive Summary

            **Current State:** ${total_revenue:,.0f} revenue from {len(pm_df):,} transactions with {avg_disc:.2f}% avg discount.

            {"High concentration (" + f"{fossil_pct:.1f}%" + " in dominant category) presents both opportunity and risk."
             if fossil_pct > 50 else
             "Revenue is distributed across product categories with a more balanced mix."}

            **Strategic Priorities:**
            1. Protect pricing power + supply stability
            2. Rebalance portfolio and align incentives
            3. Improve systems and operational efficiency
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
# -----------------------------
# -----------------------------
# TAB: Customer Segments (RFM added)
# -----------------------------
if page == 'Customer Segments':
    st.subheader("Customer Segments – Who Buys and Who Matters?")
    s_df = f.copy()

    s_tabs = st.tabs(["Overview","New x Returning", "Segment × Channel", "Customer Value", "RFM"])

    with s_tabs[0]:
        seg = (s_df.groupby("Customer Type", as_index=False)[metric_col].sum().sort_values(metric_col, ascending=False))

        fig = px.pie(seg,names="Customer Type",values=metric_col,title="Net Sales by Customer Segment",hole=0.35)
        fig.update_traces(textposition="inside",texttemplate="%{label}<br>(%{percent})",hovertemplate="<b>%{label}</b><br>Net Sales: $%{value:,.0f}<extra></extra>")
        fig = style_fig(fig, height=430)
        fig.update_layout(showlegend=True,legend=dict(orientation="v",yanchor="top",y=1,xanchor="left",x=1.05),margin=dict(r=160))

        st.plotly_chart(fig, use_container_width=True, key=pkey("seg_pie"))

        st.subheader("Description")
        st.write("""
               This chart shows **net sales (CAD) by customer segment**. It provides a breakdown of revenue contribution by different customer types and highlights trends for business strategy.
               """)

        st.subheader("Insights")
        seg = f.groupby("Customer Type", as_index=False)[metric_col].sum().sort_values(metric_col, ascending=False)
        top_segment_share = seg[metric_col].iloc[0] / seg[metric_col].sum() if seg[metric_col].sum() > 0 else np.nan
        top_segments = seg["Customer Type"].head(3).tolist()
        minor_segments_present = len(seg) > 3
        missing_segments = f["Customer Type"].isna().sum()

        bullets = []
        if np.isfinite(top_segment_share):
            bullets.append(
                f"- **{top_segments[0]}** is the top segment, contributing ~{top_segment_share * 100:.0f}% of total sales. "
                "This indicates that most of the revenue is driven by this segment, highlighting its importance for sales strategy."
            )
        if minor_segments_present:
            bullets.append(
                f"- Other notable segments include: {', '.join(top_segments[1:])}. "
                "These segments also contribute meaningfully, but less than the top segment."
            )
        if missing_segments > 0:
            bullets.append(
                f"- There are {missing_segments} records with missing Customer Type. "
                "Incomplete data can affect analysis accuracy, so consider reviewing or cleaning these records."
            )

        st.markdown("\n".join(bullets) if bullets else "- No insights available.")

        recs = []
        if np.isfinite(top_segment_share) and top_segment_share > 0.3:
            recs.append(
                f"- Focus on top segments: {', '.join(top_segments)}. "
                "Prioritizing these segments could maximize revenue and resource efficiency."
            )
        if missing_segments > 0:
            recs.append(
                "- Investigate and clean missing (NaN) data. "
                "Improving data quality ensures more reliable analysis and better decision-making."
            )

        if recs:
            st.markdown("### Recommendations")
            st.markdown("\n".join(recs))

    with s_tabs[1]:
        st.markdown("#### New vs Returning Customers Over Time")

        days_option = st.selectbox("Select time frame for new customers:",options=[30, 60, 90],index=2)
        recent_threshold = pd.Timestamp.today() - pd.Timedelta(days=days_option)
        first_purchase = df.groupby("Customer Name")["Date"].min().reset_index()
        first_purchase.rename(columns={"Date": "FirstPurchase"}, inplace=True)

        df_new_returning = df.merge(first_purchase, on="Customer Name", how="left")
        df_new_returning["CustomerStatus"] = df_new_returning["FirstPurchase"].apply(lambda x: "New" if x >= recent_threshold else "Returning")
        df_new = df_new_returning[(df_new_returning["CustomerStatus"] == "New") &(df_new_returning["Date"] >= recent_threshold)]

        df_returning = df_new_returning[df_new_returning["CustomerStatus"] == "Returning"]
        df_combined = pd.concat([df_new, df_returning])
        df_combined["Month"] = df_combined["Date"].dt.to_period("M").dt.to_timestamp()
        monthly_rev = df_combined.groupby(["Month", "CustomerStatus"], as_index=False)["Net Sales"].sum()

        fig = px.line(monthly_rev,x="Month",y="Net Sales",color="CustomerStatus",title="Monthly Revenue: New vs Returning Customers",markers=True,color_discrete_map={"New": "#1f77b4", "Returning": "#ff7f0e"})
        fig.update_layout(xaxis_title="Month",yaxis_title="Net Sales (CAD)",legend=dict(title="Customer Status"),margin=dict(t=80, r=50, l=50, b=50))
        fig = style_fig(fig, height=450) if 'style_fig' in globals() else fig
        st.plotly_chart(fig, use_container_width=True)

        top_new = (df_new.groupby(["Customer Name", "Customer Type"], as_index=False)["Net Sales"].sum().sort_values("Net Sales", ascending=False).head(10))

        top_returning = (df_returning.groupby(["Customer Name", "Customer Type"], as_index=False)["Net Sales"].sum().sort_values("Net Sales", ascending=False).head(10))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Top 10 New Customers by Spend**")
            st.dataframe(top_new[["Customer Name", "Customer Type", "Net Sales"]].style.format({"Net Sales": "${:,.0f}"}),use_container_width=True)

        with c2:
            st.markdown("**Top 10 Returning Customers by Spend**")
            st.dataframe(top_returning[["Customer Name", "Customer Type", "Net Sales"]].style.format({"Net Sales": "${:,.0f}"}),use_container_width=True)

        st.subheader("Description")
        st.markdown("""
        - Line chart shows monthly net sales from **New vs Returning customers**.  
        - **New customers**: all purchases by customers whose first-ever purchase is within the last 90 days.  
        - **Returning customers**: all purchases by customers whose first-ever purchase is older than 90 days.  
        - Tables list the top 10 new and returning customers by net sales.
        """)

        st.subheader("Insights")
        insights = [
            "- Returning customers generate the majority of revenue each month.",
            "- Revenue peaks are driven mainly by returning customers.",
            "- New customer revenue is lower and more variable.",
            "- Top returning customers significantly outperform top new customers in spend."
        ]
        st.markdown("\n".join(insights))

        st.subheader("Recommendations")
        recs = [
            "- Prioritize retention and loyalty programs for returning customers.",
            "- Nurture new customers within the first 90 days to drive repeat purchases.",
            "- Target high-spending new customers with personalized follow-ups to convert them into returning customers."
        ]
        st.markdown("\n".join(recs))

    with s_tabs[2]:
        seg_ch = s_df.groupby(["Customer Type", "Channel"],as_index=False)[metric_col].sum()
        fig = px.bar(seg_ch,x="Customer Type",y=metric_col,color="Channel",barmode="stack",title=f"{metric_label} by Segment × Channel")
        fig.update_layout(xaxis_title="",yaxis_title=metric_label,margin=dict(t=120))
        fig = style_fig(fig, height=470)
        fig.update_layout(legend=dict(orientation="v",yanchor="top",y=1,xanchor="left",x=1.02),margin=dict(r=180))
        st.plotly_chart(fig, use_container_width=True, key=pkey("seg_stack"))

        st.subheader("Description")
        st.write("""
        This chart shows **net sales (CAD) by customer segment**, broken down by sales channel. 
        It helps identify which customer types and channels contribute most to revenue.
        """)

        st.subheader("Insights")

        seg_summary = seg_ch.groupby("Customer Type", as_index=False)[metric_col].sum().sort_values(metric_col,
                                                                                                    ascending=False)
        top_segment_share = seg_summary[metric_col].iloc[0] / seg_summary[metric_col].sum() if seg_summary[
                                                                                                   metric_col].sum() > 0 else np.nan
        top_segments = seg_summary["Customer Type"].head(3).tolist()
        minor_segments_present = len(seg_summary) > 3
        missing_segments = seg_summary["Customer Type"].isna().sum()

        top_channels = \
        seg_ch[seg_ch["Customer Type"].isin(top_segments)].groupby(["Customer Type", "Channel"], as_index=False)[
            metric_col].sum()
        dominant_channels = top_channels.loc[top_channels.groupby("Customer Type")[metric_col].idxmax()]

        insights = []
        if np.isfinite(top_segment_share):
            insights.append(
                f"- **{top_segments[0]}** is the top segment, contributing ~{top_segment_share * 100:.0f}% of total sales."
            )
        if minor_segments_present:
            insights.append(
                f"- Other top segments include {', '.join(top_segments[1:])}, contributing noticeably less."
            )
        if missing_segments > 0:
            insights.append(
                f"- There are {missing_segments} records with missing Customer Type, indicating incomplete data."
            )

        for _, row in dominant_channels.iterrows():
            insights.append(
                f"- For **{row['Customer Type']}**, the dominant sales channel is **{row['Channel']}**, contributing {row[metric_col]:,.0f} CAD."
            )

        st.markdown("\n".join(insights) if insights else "- No insights available.")

        recs = []
        if np.isfinite(top_segment_share) and top_segment_share > 0.3:
            recs.append(
                f"- Focus on high-value segments: {', '.join(top_segments)}. Concentrating efforts here can maximize revenue."
            )
        if missing_segments > 0:
            recs.append(
                "- Investigate and clean missing Customer Type data to improve accuracy and decision-making."
            )
        recs.append(
            "- Leverage dominant channels for top segments (e.g., Online, Wholesale) to boost sales efficiency."
        )
        if minor_segments_present:
            recs.append(
                "- Explore growth opportunities in minor segments through targeted promotions or partnerships."
            )

        if recs:
            st.subheader("Recommendations")
            st.markdown("\n".join(recs))

    with s_tabs[3]:
        cust_stats = (df.groupby(["Customer Name", "Customer Type"], as_index=False).agg(Orders=("OrderCount", "sum"),Total_Net_Sales=("Net Sales", "sum"), Avg_Order=("Net Sales", "mean"), Last_Purchase=("Date", "max"))
        )
        cust_stats["Recency"] = (pd.Timestamp.today() - cust_stats["Last_Purchase"]).dt.days
        cust_stats["CLV"] = cust_stats["Avg_Order"] * cust_stats["Orders"]
        for col in ["Orders", "Total_Net_Sales", "Avg_Order", "CLV", "Recency"]:
            cust_stats[col] = pd.to_numeric(cust_stats[col], errors="coerce")
        cust_stats["Last_Purchase_str"] = cust_stats["Last_Purchase"].dt.strftime("%Y-%m-%d")
        cust_stats["CLV_scaled"] = cust_stats["CLV"] / cust_stats["CLV"].max() * 100

        top_cust_stats = cust_stats.sort_values(by="Total_Net_Sales", ascending=False).head(20)

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("#### Top 20 Customers by Net Sales")
            st.dataframe(top_cust_stats[["Customer Name", "Customer Type", "Orders", "Total_Net_Sales", "Avg_Order"]].style.format({"Total_Net_Sales": "{:,.0f}", "Avg_Order": "{:,.0f}"}),use_container_width=True)

        cust_stats['hover_text'] = (
                "Customer: " + cust_stats['Customer Name'] + "<br>" +
                "Customer Type: " + cust_stats['Customer Type'] + "<br>" +
                "Orders: " + cust_stats['Orders'].astype(str) + "<br>" +
                "Total Net Sales: $" + cust_stats['Total_Net_Sales'].map("{:,.0f}".format) + "<br>" +
                "Avg Order: $" + cust_stats['Avg_Order'].map("{:,.0f}".format) + "<br>" +
                "CLV: $" + cust_stats['CLV'].map("{:,.0f}".format) + "<br>" +
                "Recency (days): " + cust_stats['Recency'].astype(str) + "<br>" +
                "Last Purchase: " + cust_stats['Last_Purchase'].dt.strftime("%Y-%m-%d")
        )
        with c2:
            fig = px.scatter(cust_stats,x="Orders",y="Total_Net_Sales",color="Customer Type",size="CLV_scaled", title="Customer Value – Orders vs Total Net Sales (bubble = CLV)", hover_name='hover_text',labels={"Customer Type": ""})
            fig.update_layout(xaxis_title="Orders",yaxis_title="Total Net Sales (CAD)",legend=dict( orientation="v",x=1.02, xanchor="left",y=1, yanchor="top"),margin=dict(t=120,   r=150,l=50,b=50))
            fig = style_fig(fig, height=450) if 'style_fig' in globals() else fig
            st.plotly_chart(fig, use_container_width=True, key=pkey("seg_scatter"))

        st.subheader("Description")
        st.write("""
        The table shows the top 20 customers ranked by **total net sales**, dominated by Galleries and Museums.  
        The chart plots **Orders vs Total Net Sales**, with bubble size representing **Customer Lifetime Value (CLV)**.
        """)

        st.subheader("Insights")
        top_customers = top_cust_stats["Customer Name"].tolist()
        top_types = top_cust_stats["Customer Type"].value_counts().head(3).index.tolist()

        insights = [
            f"- **{top_types[0]}** customers generate the highest sales and CLV.",
            f"- High net sales result from both frequent orders and high average order value.",
            "- A few customers stand out as high-value despite fewer orders, indicating strong growth potential."
        ]

        st.markdown("\n".join(insights))

        st.subheader("Recommendations")
        recs = [
            "- Prioritize retention and relationship management for top Galleries and Museums.",
            "- Use targeted upselling for high-value, low-frequency buyers.",
            "- Focus growth efforts on mid-tier customers with increasing CLV."
        ]

        st.markdown("\n".join(recs))


    with s_tabs[4]:
        st.markdown("#### RFM Bubble Chart: Recency × Frequency × Monetary")

        ref_date = s_df["Date"].max()

        customer_type_map = s_df.groupby("Customer Name")["Customer Type"].first().reset_index()

        rfm = s_df.groupby("Customer Name", as_index=False).agg(LastPurchase=("Date", "max"),Frequency=("OrderCount", "sum"),Monetary=("Net Sales", "sum"))
        rfm = rfm.merge(customer_type_map, on="Customer Name", how="left")
        rfm["RecencyDays"] = (ref_date - rfm["LastPurchase"]).dt.days
        rfm = rfm.replace([np.inf, -np.inf], np.nan).dropna(subset=["RecencyDays", "Frequency", "Monetary"])
        rfm["CLV_scaled"] = (rfm["Monetary"] * rfm["Frequency"]) / (rfm["Monetary"] * rfm["Frequency"]).max() * 100

        st.markdown("#### Filter Options")
        col1, col2, col3 = st.columns(3)

        with col1:
            max_frequency = int(rfm["Frequency"].max())
            default_min_orders = min(1, max_frequency)
            min_orders = st.number_input("Minimum number of orders:",min_value=1,max_value=max_frequency,value=default_min_orders,step=1)

        with col2:
            max_recency_val = int(rfm["RecencyDays"].max())
            default_max_recency = min(90, max_recency_val)
            max_recency = st.slider("Maximum recency (days):",min_value=0,max_value=max_recency_val,value=default_max_recency)

        with col3:
            max_sales_val = int(rfm["Monetary"].max())
            default_min_sales = min(100, max_sales_val)
            min_sales = st.number_input("Minimum net sales:",min_value=0,max_value=max_sales_val,value=default_min_sales,step=100)

        rfm_filtered = rfm[
            (rfm["Frequency"] >= min_orders) &
            (rfm["RecencyDays"] <= max_recency) &
            (rfm["Monetary"] >= min_sales)
            ]

        rfm_filtered["HoverLabel"] = rfm_filtered.apply(lambda row: f"{row['Customer Name']} / {row['Customer Type']}",axis=1)

        fig = px.scatter(rfm_filtered,x="RecencyDays",y="Frequency",size="CLV_scaled",color="Monetary",hover_name="HoverLabel", hover_data={}, title="RFM Bubble Chart: Recency × Frequency × Monetary",color_continuous_scale="Viridis",size_max=40)
        fig.update_layout(xaxis_title="Recency (days since last purchase)",yaxis_title="Frequency (Number of Orders)",margin=dict(t=50, l=50, r=50, b=50))
        fig = style_fig(fig, height=450) if 'style_fig' in globals() else fig
        st.plotly_chart(fig, use_container_width=True, key=pkey("rfm_bubble_2d"))

        st.subheader("Description")
        st.write("""
        The RFM bubble chart plots customers by recency (days since last purchase) on the x-axis and frequency (number of orders) on the y-axis, with bubble size and color representing monetary value. Larger, brighter bubbles indicate higher-spending customers.***.
        """)

        st.subheader("Insights")
        insights = [
            "- High-value customers are recent and purchase frequently.",
            "- Inactive customers cluster at high Recency with low Frequency.",
            "- Some customers spend a lot despite low purchase frequency."
        ]
        st.markdown("\n".join(insights))

        st.subheader("Recommendations")
        recs = [
            "- Retain top customers with loyalty programs or exclusive offers.",
            "- Re-engage inactive customers using targeted campaigns.",
            "- Encourage repeat purchases from high-spend, low-frequency customers."
        ]
        st.markdown("\n".join(recs))


# -----------------------------
# TAB: Geography & Channels (Price-Drivers style layout)  YOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO
# -----------------------------
if page == 'Geography & Channels':
    st.subheader("Geography & Channels")

    df = f.copy()

    # ---- metric setup ----
    metric = metric_col
    metric_name = metric_label if "metric_label" in globals() else metric

    # ---- make sure metric exists ----
    if metric not in df.columns:
        df[metric] = 0.0
    df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0.0)

    # ---- make sure core cols exist ----
    for col in ["Country", "Channel", "City"]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].astype(str).fillna("Unknown")

    # ---- Month setup (prefer existing Month; else derive from Date) ----
    if "Month" in df.columns:
        df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    elif "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Month"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    else:
        df["Month"] = pd.NaT

    # ---- lag column (shipping) ----
    if "Days to Ship" in df.columns:
        lag_col = "Days to Ship"
        df[lag_col] = pd.to_numeric(df[lag_col], errors="coerce")
    elif "Days_to_Ship" in df.columns:
        lag_col = "Days_to_Ship"
        df[lag_col] = pd.to_numeric(df[lag_col], errors="coerce")
    elif ("Date" in df.columns) and ("Shipped Date" in df.columns):
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Shipped Date"] = pd.to_datetime(df["Shipped Date"], errors="coerce")
        df["Days_to_Ship"] = (df["Shipped Date"] - df["Date"]).dt.days
        lag_col = "Days_to_Ship"
    else:
        lag_col = None

    # ---- helpers (define only if missing) ----
    if "rank_df" not in globals():
        def rank_df(dfin: pd.DataFrame) -> pd.DataFrame:
            out = dfin.reset_index(drop=True).copy()
            out.insert(0, "#", range(1, len(out) + 1))
            return out

    if "fig_tight" not in globals():
        def fig_tight(fig, height=520):
            fig.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=height)
            try:
                fig = style_fig(fig, height=height)
            except Exception:
                pass
            return fig

    if "download_html" not in globals():
        def download_html(fig, filename: str, label: str = "Download chart (HTML)"):
            try:
                html = fig.to_html(full_html=True, include_plotlyjs="cdn")
                st.download_button(
                    label,
                    data=html.encode("utf-8"),
                    file_name=filename,
                    mime="text/html",
                    key=pkey("dl_html"),
                )
            except Exception:
                pass

    if "heatmap_from_pivot" not in globals():
        def heatmap_from_pivot(pv: pd.DataFrame, title: str, unit: str):
            hm = px.imshow(
                pv,
                aspect="auto",
                title=title,
                labels=dict(
                    x=pv.columns.name or "Channel",
                    y=pv.index.name or "Country",
                    color=unit,
                ),
            )
            return fig_tight(hm, height=520)

    def insights_expander(title: str, insights_md: str, why_md: str, recs_md: str):
        with st.expander(f"Insights - {title}", expanded=False):
            st.markdown(f"**Insights:**\n{insights_md if insights_md.strip() else '-'}")
            st.markdown(f"\n**Why it helps:**\n{why_md if why_md.strip() else '-'}")
            st.markdown(f"\n**Recommendations:**\n{recs_md if recs_md.strip() else '-'}")

    # -----------------------------
    # Dynamic Insights helpers
    # -----------------------------
    def _is_money_metric(name: str, col: str) -> bool:
        s = f"{name} {col}".lower()
        money_words = ["sales", "revenue", "net", "gross", "amount", "cad", "$", "value"]
        return any(w in s for w in money_words)

    METRIC_IS_MONEY = _is_money_metric(metric_name, metric)

    def fmt_metric(x):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "—"
        try:
            v = float(x)
        except Exception:
            return "—"
        if METRIC_IS_MONEY:
            return f"${v:,.0f} CAD"
        return f"{int(round(v)):,}"

    def fmt_pct(p):
        if p is None or (isinstance(p, float) and not np.isfinite(p)):
            return "—"
        return f"{p*100:.1f}%"

    def share_top_k(agg_df, k=3):
        if agg_df is None or agg_df.empty or "value" not in agg_df.columns:
            return np.nan
        total = float(agg_df["value"].sum())
        if total <= 0:
            return np.nan
        topk = float(agg_df.sort_values("value", ascending=False)["value"].head(k).sum())
        return topk / total

    def safe_first_share(series: pd.Series):
        if series is None or len(series) == 0:
            return np.nan
        total = float(series.sum())
        if total <= 0:
            return np.nan
        return float(series.iloc[0]) / total

    def bullet(lines):
        lines = [l for l in lines if l and str(l).strip()]
        return "\n".join([f"- {l}" for l in lines]) if lines else "- —"

    # ---- aggregations ----
    country_totals = df.groupby("Country")[metric].sum().sort_values(ascending=False)
    channel_totals = df.groupby("Channel")[metric].sum().sort_values(ascending=False)

    top_country = str(country_totals.index[0]) if len(country_totals) else "—"
    top_channel = str(channel_totals.index[0]) if len(channel_totals) else "—"

    cons_rate = np.nan
    for ccol in ["Consignment? (Y/N)", "Consignment", "Consignment?"]:
        if ccol in df.columns:
            s = df[ccol].astype(str).str.strip().str.lower()
            cons_rate = float(s.isin(["y", "yes", "true", "1"]).mean() * 100) if len(s) else np.nan
            break

    neg_lag_rows = 0
    if lag_col is not None and lag_col in df.columns:
        neg_lag_rows = int((pd.to_numeric(df[lag_col], errors="coerce") < 0).sum())

    # -----------------------------
    # Sub-tabs (UPDATED)
    # - Removed: Overview
    # - Renamed: Time -> Shipping Lag
    # - Removed: Data
    # -----------------------------
    tabs = st.tabs(["World Map", "Geography × Channels", "Shipping Lag"])

    # ======================
    # TAB 0: World Map
    # ======================
    with tabs[0]:
        st.subheader(f"World map - {metric_name} ($ CAD)" if METRIC_IS_MONEY else f"World map - {metric_name}")

        agg = country_totals.reset_index().rename(columns={metric: "value"})
        total_val = float(agg["value"].sum()) if not agg.empty else 0.0
        agg["share"] = np.where(total_val > 0, agg["value"] / total_val, np.nan)

        if agg.empty:
            st.info("No country data available for current filters.")
        else:
            fig = px.choropleth(
                agg,
                locations="Country",
                locationmode="country names",
                color="value",
                hover_name="Country",
                custom_data=["share"],
                projection="natural earth",
            )
            fig.update_traces(
                hovertemplate="<b>%{location}</b><br>Value: %{z:$,.0f} CAD<br>Share: %{customdata[0]:.1%}<extra></extra>"
                if METRIC_IS_MONEY
                else "<b>%{location}</b><br>Value: %{z:,.0f}<br>Share: %{customdata[0]:.1%}<extra></extra>"
            )
            fig = fig_tight(fig, height=520)
            st.plotly_chart(fig, use_container_width=True, key=pkey("geo_world"))
            download_html(fig, "01_world_map.html")

            st.subheader("Top markets")
            top_tbl = agg.sort_values("value", ascending=False).head(15).copy()
            top_tbl = rank_df(top_tbl)
            st.dataframe(top_tbl.set_index("#")[["Country", "value", "share"]], use_container_width=True)

        # ---- Dynamic insights (World Map) ----
        n_countries = int(agg["Country"].nunique()) if not agg.empty else 0
        top1_share = share_top_k(agg, k=1)
        top3_share = share_top_k(agg, k=3)
        top5_share = share_top_k(agg, k=5)
        top_channel_share = safe_first_share(channel_totals)

        ins_lines = [
            f"Countries in view: **{n_countries}**.",
            (f"Top market: **{top_country}** ({fmt_pct(top1_share)} of total)." if np.isfinite(top1_share) else ""),
            (f"Top 3 markets contribute **{fmt_pct(top3_share)}** of total." if np.isfinite(top3_share) else ""),
            (f"Top 5 markets contribute **{fmt_pct(top5_share)}** of total." if np.isfinite(top5_share) else ""),
            (f"Top channel overall: **{top_channel}** ({fmt_pct(top_channel_share)} of total)." if np.isfinite(top_channel_share) else ""),
            (f"Consignment rate: **{cons_rate:.1f}%**." if np.isfinite(cons_rate) else ""),
        ]
        why_lines = [
            "Shows where demand/value is concentrated so you can prioritize markets fast.",
            "Makes it easy to spot new/under-served regions worth testing.",
        ]
        recs = []
        if np.isfinite(top1_share) and top1_share >= 0.50:
            recs.append(f"High concentration in **{top_country}** → reduce risk by growing the next 2–3 markets.")
        elif np.isfinite(top3_share) and top3_share >= 0.75:
            recs.append("Strong top-3 concentration → focus inventory + marketing there, but run small tests elsewhere.")

        if np.isfinite(top_channel_share) and top_channel_share >= 0.60:
            recs.append(f"Heavy channel dependence on **{top_channel}** → protect performance (backup channel plan).")

        if np.isfinite(cons_rate) and cons_rate >= 50:
            recs.append("Consignment is a big share → track cash timing + returns separately (avoid mixing with standard sales).")

        if not recs:
            recs = [
                "Focus spend + inventory on top markets first.",
                "Expand to next-tier markets using the best-performing channel patterns from the heatmap tab.",
            ]

        insights_expander("World Map", bullet(ins_lines), bullet(why_lines), bullet(recs))
        st.divider()

    # ======================
    # TAB 1: Geography × Channels
    # ======================
    with tabs[1]:
        top_n = st.slider("Top N countries", 3, 30, 12, key="geo_top_n")

        colA, colB = st.columns(2)

        with colA:
            st.subheader(f"Top countries by {metric_name}")
            top_c = country_totals.head(top_n).reset_index().rename(columns={metric: "value"})
            fig1 = px.bar(top_c, x="Country", y="value", title=f"Top {top_n} Countries ({metric_name})")
            fig1.update_layout(xaxis={"categoryorder": "total descending"})
            fig1.update_traces(
                hovertemplate="<b>%{x}</b><br>Value: %{y:$,.0f} CAD<extra></extra>"
                if METRIC_IS_MONEY
                else "<b>%{x}</b><br>Value: %{y:,.0f}<extra></extra>"
            )
            fig1 = fig_tight(fig1, height=460)
            st.plotly_chart(fig1, use_container_width=True, key=pkey("geo_top_c"))
            download_html(fig1, "02_top_countries.html")

        with colB:
            st.subheader(f"{metric_name} by channel")
            ch = channel_totals.reset_index().rename(columns={metric: "value"})
            fig2 = px.bar(ch, x="Channel", y="value", title=f"{metric_name} by Channel")
            fig2.update_layout(xaxis={"categoryorder": "total descending"})
            fig2.update_traces(
                hovertemplate="<b>%{x}</b><br>Value: %{y:$,.0f} CAD<extra></extra>"
                if METRIC_IS_MONEY
                else "<b>%{x}</b><br>Value: %{y:,.0f}<extra></extra>"
            )
            fig2 = fig_tight(fig2, height=460)
            st.plotly_chart(fig2, use_container_width=True, key=pkey("geo_ch_bar"))
            download_html(fig2, "03_channel_bar.html")

        st.subheader("Country × Channel heatmap (Top countries)")
        top_idx = country_totals.head(top_n).index
        df_top = df[df["Country"].isin(top_idx)]
        pv = df_top.pivot_table(values=metric, index="Country", columns="Channel", aggfunc="sum", fill_value=0)

        if pv.empty:
            st.info("Not enough data for the heatmap in current filters.")
        else:
            unit = "$ CAD" if METRIC_IS_MONEY else "value"
            fig3 = heatmap_from_pivot(pv, f"Heatmap: {metric_name} ({unit})", unit)
            st.plotly_chart(fig3, use_container_width=True, key=pkey("geo_hm"))
            download_html(fig3, "04_country_channel_heatmap.html")

        # ---- Dynamic insights (Geography × Channels) ----
        total_metric_all = float(df[metric].sum()) if metric in df.columns else np.nan
        top_n_share = (float(country_totals.head(top_n).sum()) / total_metric_all) if np.isfinite(total_metric_all) and total_metric_all > 0 else np.nan

        hotspot = None
        if not pv.empty:
            stack = pv.stack()
            if len(stack) > 0:
                (hc, hch) = stack.idxmax()
                hotspot = (hc, hch, float(stack.max()))

        best_channels = []
        if not pv.empty:
            top3_countries = country_totals.head(min(3, len(country_totals))).index.tolist()
            for c in top3_countries:
                if c in pv.index:
                    best_ch = pv.loc[c].idxmax()
                    best_val = float(pv.loc[c].max())
                    best_channels.append(f"**{c}** → best channel: **{best_ch}** ({fmt_metric(best_val)}).")

        ins_lines = [
            (f"Top {top_n} countries contribute **{fmt_pct(top_n_share)}** of total." if np.isfinite(top_n_share) else ""),
            (f"Top channel overall: **{top_channel}** ({fmt_pct(safe_first_share(channel_totals))} of total)." if len(channel_totals) else ""),
        ]
        if hotspot is not None:
            ins_lines.append(f"Biggest hotspot: **{hotspot[0]} × {hotspot[1]}** ({fmt_metric(hotspot[2])}).")
        ins_lines += best_channels

        why_lines = [
            "Shows which countries and channels drive results, and where each market behaves differently.",
            "Heatmap reveals the best country+channel combinations to scale.",
        ]

        recs = []
        if np.isfinite(top_n_share) and top_n_share >= 0.80:
            recs.append(f"Most results come from the top {top_n} countries → protect those markets (stock + campaigns).")

        ch_share = safe_first_share(channel_totals)
        if np.isfinite(ch_share) and ch_share >= 0.60:
            recs.append(f"Results are heavily driven by **{top_channel}** → diversify tests into the #2 channel to reduce risk.")

        if hotspot is not None and np.isfinite(total_metric_all) and total_metric_all > 0:
            hotspot_share = hotspot[2] / total_metric_all
            if hotspot_share >= 0.25:
                recs.append(f"One hotspot is huge ({fmt_pct(hotspot_share)}) → build a repeatable playbook for that combo.")

        if not recs:
            recs = [
                "Treat smaller countries as experiments; scale only those with repeatable traction.",
                "Pick 1–2 winning channels per top country and build a playbook around them.",
                "Don’t force one global channel strategy—optimize per market.",
            ]

        insights_expander("Geography × Channels", bullet(ins_lines), bullet(why_lines), bullet(recs))
        st.divider()

    # ======================
    # TAB 2: Shipping Lag
    # ======================
    with tabs[2]:
        st.subheader("Shipping lag")

        if lag_col is None or lag_col not in df.columns:
            st.info("No shipping lag available (need Days to Ship or Date + Shipped Date).")

            insights_md = bullet(["No shipping lag column available in this file."])
            why_md = bullet([
                "Helps identify where fulfillment delays occur so operations fixes are targeted.",
                "Prevents guessing by showing delay hotspots alongside volume."
            ])
            recs_md = bullet([
                "Add **Days to Ship** or **Date + Shipped Date** to enable lag insights.",
                "Standardize date formats and ensure shipped dates are after order dates."
            ])
            insights_expander("Shipping Lag", insights_md, why_md, recs_md)
            st.divider()

        else:
            clean_neg = st.toggle("Treat negative lag rows as missing", value=True, key="lag_clean_neg")

            lag_df = df.dropna(subset=[lag_col]).copy()
            lag_df["Ship Lag (days)"] = pd.to_numeric(lag_df[lag_col], errors="coerce")
            lag_df = lag_df.dropna(subset=["Ship Lag (days)"])

            if clean_neg:
                lag_df = lag_df[lag_df["Ship Lag (days)"] >= 0]

            if lag_df.empty:
                st.info("No usable shipping lag values after filters.")

                insights_md = bullet(["No usable shipping lag values after cleaning/filters."])
                why_md = bullet([
                    "Highlights where fulfillment delays cluster so ops fixes happen where they matter most.",
                    "Prevents optimizing low-impact areas."
                ])
                recs_md = bullet([
                    "Check your lag/date columns for blanks or invalid values.",
                    "If you derive lag from dates, confirm **Date** and **Shipped Date** are parsed correctly."
                ])
                insights_expander("Shipping Lag", insights_md, why_md, recs_md)
                st.divider()

            else:
                col1, col2 = st.columns(2)

                with col1:
                    by_country = (
                        lag_df.groupby("Country")["Ship Lag (days)"]
                        .mean()
                        .sort_values(ascending=False)
                        .head(20)
                        .reset_index()
                    )
                    fig1 = px.bar(by_country, x="Country", y="Ship Lag (days)", title="Avg Ship Lag by Country (days)")
                    fig1.update_layout(xaxis={"categoryorder": "total descending"})
                    fig1 = fig_tight(fig1, height=420)
                    st.plotly_chart(fig1, use_container_width=True, key=pkey("lag_country"))
                    download_html(fig1, "06_ship_lag_by_country.html")

                    pick = st.selectbox(
                        "Country → city drilldown",
                        sorted(lag_df["Country"].unique().tolist()),
                        key="lag_pick",
                    )
                    by_city = (
                        lag_df[lag_df["Country"] == pick]
                        .groupby("City")["Ship Lag (days)"]
                        .mean()
                        .sort_values(ascending=False)
                        .head(15)
                        .reset_index()
                    )
                    fig2 = px.bar(by_city, x="City", y="Ship Lag (days)", title=f"Avg Ship Lag by City in {pick} (Top 15)")
                    fig2.update_layout(xaxis={"categoryorder": "total descending"})
                    fig2 = fig_tight(fig2, height=420)
                    st.plotly_chart(fig2, use_container_width=True, key=pkey("lag_city"))
                    download_html(fig2, "07_ship_lag_by_city.html")

                with col2:
                    min_orders = st.slider("Minimum orders per Country+City", 2, 15, 5, key="lag_min_orders")

                    order_col = "Sale ID" if "Sale ID" in lag_df.columns else metric
                    cc = (
                        lag_df.groupby(["Country", "City"])
                        .agg(
                            orders=(order_col, "count"),
                            avg_lag=("Ship Lag (days)", "mean"),
                            med_lag=("Ship Lag (days)", "median"),
                            total_metric=(metric, "sum"),
                        )
                        .reset_index()
                    )
                    cc = cc[cc["orders"] >= min_orders].copy()
                    cc = cc.sort_values(["avg_lag", "orders"], ascending=[False, False]).head(25)

                    cc["total_metric"] = cc["total_metric"].round(0)
                    cc["avg_lag"] = cc["avg_lag"].round(1)
                    cc["med_lag"] = cc["med_lag"].round(1)

                    cc = rank_df(cc).rename(columns={"total_metric": f"Total ({metric_name})"})
                    st.dataframe(
                        cc.set_index("#")[["Country", "City", "orders", "avg_lag", "med_lag", f"Total ({metric_name})"]],
                        use_container_width=True,
                    )

                    top_countries = lag_df.groupby("Country")[metric].sum().sort_values(ascending=False).head(12).index
                    sub = lag_df[lag_df["Country"].isin(top_countries)].copy()
                    top_cities = sub.groupby("City")[metric].sum().sort_values(ascending=False).head(20).index
                    sub = sub[sub["City"].isin(top_cities)].copy()

                    pv2 = sub.pivot_table(values="Ship Lag (days)", index="Country", columns="City", aggfunc="mean")
                    if not pv2.empty:
                        fig3 = heatmap_from_pivot(pv2, "Avg Ship Lag Heatmap (Country × City)", "days")
                        st.plotly_chart(fig3, use_container_width=True, key=pkey("lag_hm"))
                        download_html(fig3, "08_ship_lag_heatmap_country_city.html")

                # ---- Dynamic insights (Shipping Lag) ----
                mean_lag = float(lag_df["Ship Lag (days)"].mean())
                med_lag = float(lag_df["Ship Lag (days)"].median())
                p90_lag = float(lag_df["Ship Lag (days)"].quantile(0.90))

                lag_ins = [
                    f"Avg lag: **{mean_lag:.1f} days** (median **{med_lag:.1f}**, p90 **{p90_lag:.1f}**).",
                    (f"Negative lag rows detected: **{neg_lag_rows}** (data issue)." if neg_lag_rows > 0 else "No negative lag rows detected (or already cleaned)."),
                ]

                # worst country by avg lag (min sample size)
                order_col = "Sale ID" if "Sale ID" in lag_df.columns else metric
                by_cty = (
                    lag_df.groupby("Country")
                    .agg(orders=(order_col, "count"), avg_lag=("Ship Lag (days)", "mean"), total=(metric, "sum"))
                    .reset_index()
                )
                by_cty = by_cty[by_cty["orders"] >= 5].sort_values("avg_lag", ascending=False)
                if not by_cty.empty:
                    wc = by_cty.iloc[0]
                    lag_ins.append(f"Worst avg lag (min 5 orders): **{wc['Country']}** at **{wc['avg_lag']:.1f} days**.")

                lag_why = [
                    "Highlights where fulfillment delays cluster so ops fixes happen where they matter most.",
                    "Combines lag with volume so you don’t waste time optimizing low-impact areas.",
                ]

                lag_recs = []
                if p90_lag >= 14:
                    lag_recs.append("p90 lag is high (≥14 days) → prioritize fixes for delayed lanes first (carrier / warehouse / cutoff times).")
                if mean_lag >= 10:
                    lag_recs.append("Average lag is high (≥10 days) → review fulfillment workflow and set tighter SLAs.")
                if neg_lag_rows > 0:
                    lag_recs.append("Clean or exclude negative lag rows so lag KPIs remain trustworthy.")
                lag_recs += [
                    "Fix the biggest delay hotspots first (high lag + meaningful volume).",
                    "Track lag monthly by country/city to confirm improvements.",
                ]

                insights_expander("Shipping Lag", bullet(lag_ins), bullet(lag_why), bullet(lag_recs))
                st.divider()

# -----------------------------
# TAB 6: Inventory Timing 
# -----------------------------
# ---Helpers--- #
try:
    from scipy.stats import norm
except Exception:
    norm = None

def _ensure_month_and_ownership(df_in: pd.DataFrame) -> pd.DataFrame:
    dfx = df_in.copy()
    # Date + Month
    if "Date" in dfx.columns:
        dfx["Date"] = pd.to_datetime(dfx["Date"], errors="coerce")
        dfx = dfx.dropna(subset=["Date"])
        dfx["Month"] = dfx["Date"].dt.to_period("M").astype(str)
    # Ownership mapping (if needed)
    if "Ownership" not in dfx.columns and "Consignment? (Y/N)" in dfx.columns:
        dfx["Ownership"] = dfx["Consignment? (Y/N)"].map({"Y": "Consigned", "N": "Owned"})
    return dfx

def compute_3mma_forecast_and_thresholds(monthly_cnt: pd.DataFrame, z_service: float, horizon_months: int = 3):
    if monthly_cnt is None or monthly_cnt.empty:
        return None

    y = monthly_cnt["Sales_Count"].astype(float).values
    y_series = pd.Series(y)

    if len(y_series) >= 3:
        ma3_hist = y_series.rolling(3, min_periods=3).mean()
        forecast_next_val = float(y_series.tail(3).mean())
    else:
        ma3_hist = y_series.rolling(3, min_periods=1).mean()
        forecast_next_val = float(y_series.mean()) if len(y_series) else 0.0

    sigma_month = float(np.std(y, ddof=1)) if len(y) > 1 else 0.0
    safety_1m = float(z_service * sigma_month)
    optimal_1m = max(float(forecast_next_val + safety_1m), 0.0)

    eval_mask = (~pd.isna(ma3_hist)) & (monthly_cnt["Sales_Count"] > 0)
    if eval_mask.any():
        actual = monthly_cnt.loc[eval_mask, "Sales_Count"].values
        forecast = ma3_hist.loc[eval_mask].values
        mape = np.mean(np.abs(actual - forecast) / actual)
        acc = max(0.0, (1 - mape) * 100)
    else:
        acc = np.nan

    return {
        "forecast_next_val": forecast_next_val,
        "ma3_hist": ma3_hist,
        "sigma_month": sigma_month,
        "safety_1m": safety_1m,
        "optimal_1m": optimal_1m,
        "forecast_accuracy_pct": acc
    }

def deviation_sales_vs_thresholds(monthly_cnt: pd.DataFrame, z_service: float):
    if monthly_cnt is None or monthly_cnt.empty:
        return None

    out = compute_3mma_forecast_and_thresholds(monthly_cnt, z_service, horizon_months=3)
    if out is None:
        return None

    safety_1m = int(round(out["safety_1m"]))
    optimal_1m = int(round(out["optimal_1m"]))

    y = monthly_cnt["Sales_Count"].astype(int).values

    above_mask = y > optimal_1m
    above_periods = int(above_mask.sum())
    above_units_total = int((y[above_mask] - optimal_1m).sum())

    below_mask = y < safety_1m
    below_periods = int(below_mask.sum())
    below_units_total = int((safety_1m - y[below_mask]).sum())

    return {
        "above_periods": above_periods,
        "above_units_total": above_units_total,
        "below_periods": below_periods,
        "below_units_total": below_units_total,
    }

# -- inventory -- #
def render_inventory_analysis_tab(df_in: pd.DataFrame):
    st.markdown("### Inventory Analysis – Sales vs Forecast, Safety Stock & Optimal Level")

    df = _ensure_month_and_ownership(df_in)

    required_cols = ["Date", "Sale ID"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns in dataset: {missing}")
        return

    # Parameters
    HORIZON_MONTHS = 3
    SERVICE_LEVEL = 0.90
    if norm is None:
        st.warning("scipy is not available; cannot compute Z from service level.")
        return
    Z_SERVICE = float(norm.ppf(SERVICE_LEVEL))

    all_label = "All Product Types (Total Inventory)"
    product_type_list = (
        sorted(df["Product Type"].dropna().unique().tolist())
        if "Product Type" in df.columns else []
    )

    scope_choice = st.selectbox(
        "Product Type Selector:",
        [all_label] + product_type_list,
        index=0,
        key=wkey("inv_scope")
    )

    if scope_choice == all_label:
        df_scope = df.copy()
        scope_title = "All Product Types"
    else:
        df_scope = df[df["Product Type"] == scope_choice].copy()
        scope_title = f"Product Type: {scope_choice}"

    monthly_cnt = (
        df_scope.groupby("Month")["Sale ID"]
                .count()
                .reset_index(name="Sales_Count")
    )

    if monthly_cnt.empty:
        st.info("No data available to compute inventory analysis with current filters.")
        return

    monthly_cnt["Month_dt"] = pd.to_datetime(monthly_cnt["Month"], format="%Y-%m", errors="coerce")
    monthly_cnt = (
        monthly_cnt.dropna(subset=["Month_dt"])
                   .sort_values("Month_dt")
                   .reset_index(drop=True)
    )

    if monthly_cnt.empty:
        st.info("No valid months after parsing. Check the 'Date' column format.")
        return

    pack = compute_3mma_forecast_and_thresholds(monthly_cnt, Z_SERVICE, horizon_months=HORIZON_MONTHS)
    if pack is None:
        st.info("Unable to compute forecast/thresholds for the current scope.")
        return

    ma3_hist = pack["ma3_hist"]
    forecast_next_val = float(pack["forecast_next_val"])
    sigma_month = float(pack["sigma_month"])
    safety_stock_1m = float(pack["safety_1m"])
    optimal_stock_1m = float(pack["optimal_1m"])
    forecast_accuracy_pct_scope = pack["forecast_accuracy_pct"]

    safety_1m_int = int(round(safety_stock_1m))
    optimal_1m_int = int(round(optimal_stock_1m))

    # KPIs
    total_units_sold = int(df["Sale ID"].count())

    most_pt, most_pct = "N/A", 0.0
    least_pt, least_pct = "N/A", 0.0
    if "Product Type" in df.columns:
        pt_counts = (
            df.dropna(subset=["Product Type"])
              .groupby("Product Type")["Sale ID"]
              .count()
              .sort_values(ascending=False)
        )
        if not pt_counts.empty and total_units_sold > 0:
            most_pt = str(pt_counts.index[0])
            most_pct = float(pt_counts.iloc[0] / total_units_sold * 100.0)
            least_pt = str(pt_counts.index[-1])
            least_pct = float(pt_counts.iloc[-1] / total_units_sold * 100.0)

    forecast_acc_text = (
        "N/A" if pd.isna(forecast_accuracy_pct_scope)
        else f"{float(forecast_accuracy_pct_scope):.1f}%"
    )

    over_best = {"pt": "N/A", "periods": 0, "units": 0}
    under_best = {"pt": "N/A", "periods": 0, "units": 0}

    if "Product Type" in df.columns and product_type_list:
        for pt in product_type_list:
            g = df[df["Product Type"] == pt].copy()
            mc = g.groupby("Month")["Sale ID"].count().reset_index(name="Sales_Count")
            mc["Month_dt"] = pd.to_datetime(mc["Month"], format="%Y-%m", errors="coerce")
            mc = mc.dropna(subset=["Month_dt"]).sort_values("Month_dt").reset_index(drop=True)
            if mc.empty:
                continue

            dev = deviation_sales_vs_thresholds(mc, Z_SERVICE)
            if dev is None:
                continue

            if (dev["above_periods"] > over_best["periods"]) or (
                dev["above_periods"] == over_best["periods"] and dev["above_units_total"] > over_best["units"]
            ):
                over_best = {"pt": str(pt), "periods": dev["above_periods"], "units": dev["above_units_total"]}

            if (dev["below_periods"] > under_best["periods"]) or (
                dev["below_periods"] == under_best["periods"] and dev["below_units_total"] > under_best["units"]
            ):
                under_best = {"pt": str(pt), "periods": dev["below_periods"], "units": dev["below_units_total"]}

        # -----------------------------
    # KPIs
    # -----------------------------
    k1, k2, k3 = st.columns(3)
    k4, k5, k6 = st.columns(3)

    k1.metric("Units sold (total)", f"{total_units_sold:,}")
    k2.metric(
        "Most demanded Product Type",
        f"{most_pt}",
        delta=(f"+{most_pct:.1f}%" if most_pt != "N/A" else None),
    )
    k3.metric(
        "Least demanded Product Type",
        f"{least_pt}",
        delta=(f"-{least_pct:.1f}%" if least_pt != "N/A" else None),
    )
    k4.metric("Forecast accuracy (current scope)", forecast_acc_text)

    k5.metric(
        "Most above Optimal (1M)",
        f"{over_best['pt']}",
        delta=(
            f"{over_best['periods']} months | {over_best['units']} units"
            if over_best["pt"] != "N/A" and over_best["periods"] > 0
            else None
        ),
    )

    k6.metric(
        "Most below Safety (1M)",
        f"{under_best['pt']}",
        delta=(
            f"{under_best['periods']} months | {under_best['units']} units"
            if under_best["pt"] != "N/A" and under_best["periods"] > 0
            else None
        ),
    )

    # -----------------------------
    # Recommendations (dropdown)
    # -----------------------------
    most_delta_txt = (f"+{most_pct:.1f}%" if most_pt != "N/A" else "N/A")
    least_delta_txt = (f"-{least_pct:.1f}%" if least_pt != "N/A" else "N/A")

    over_delta_txt = (
        f"{over_best['periods']} months | {over_best['units']} units"
        if over_best["pt"] != "N/A" and over_best["periods"] > 0
        else "N/A"
    )
    under_delta_txt = (
        f"{under_best['periods']} months | {under_best['units']} units"
        if under_best["pt"] != "N/A" and under_best["periods"] > 0
        else "N/A"
    )

    with st.expander("Recommendations", expanded=False):
        st.markdown(
            f"""
- **Most demanded Product Type:** **{most_pt}** ({most_delta_txt})  
  The product with the strongest positive demand trend. It is recommended to **review inventory levels to ensure adequate supply and avoid potential stockouts**.

- **Most above Optimal (1M):** **{over_best['pt']}** ({over_delta_txt})  
  The product showing the highest fluctuation above the optimal stock level over the last month. It is recommended to **maintain active monitoring to detect atypical demand or stocking behavior**.

- **Least demanded Product Type:** **{least_pt}** ({least_delta_txt})  
  The product with the strongest negative demand trend. It is recommended to **maintain inventory levels between safety and optimal thresholds to reduce overstock risk**.

- **Most below Safety (1M):** **{under_best['pt']}** ({under_delta_txt})  
  The product with the highest fluctuation below the safety stock level over the last month. It is recommended to **conduct a deeper investigation into atypical demand patterns or supply disruptions**.
"""
        )

    st.markdown("---")

    # -----------------------------
    # Chart (line chart)
    # -----------------------------
    last_month_dt = monthly_cnt["Month_dt"].max()
    next_month = last_month_dt + pd.DateOffset(months=1)

    ext_months = list(monthly_cnt["Month_dt"]) + [next_month]
    actual_ext = list(monthly_cnt["Sales_Count"].astype(int)) + [None]
    forecast_ext = list(ma3_hist) + [forecast_next_val]
    forecast_ext_plot = [(None if pd.isna(v) else float(v)) for v in forecast_ext]
    safety_ext = [safety_1m_int] * len(ext_months)
    optimal_ext = [optimal_1m_int] * len(ext_months)

    fig_inv = go.Figure()
    fig_inv.add_trace(go.Scatter(x=ext_months, y=actual_ext, mode="lines+markers", name="Actual Sales (Monthly Items)"))
    fig_inv.add_trace(go.Scatter(
        x=ext_months, y=forecast_ext_plot, mode="lines+markers",
        name="Trending Line", line=dict(dash="dash")
    ))
    fig_inv.add_trace(go.Scatter(
        x=ext_months, y=safety_ext, mode="lines",
        name="Safety Stock (1 month)", line=dict(dash="dot")
    ))
    fig_inv.add_trace(go.Scatter(
        x=ext_months, y=optimal_ext, mode="lines+markers",
        name="Optimal Stock (1 month)"
    ))

    fig_inv.update_layout(
        xaxis_title="Month",
        yaxis_title="Units",
        title=f"Inventory performance (sales vs optimal & safety level) — {scope_title}",
        height=550
    )
    st.plotly_chart(fig_inv, use_container_width=True)

    # -----------------------------
    # Insights (dropdown)
    # -----------------------------
    with st.expander("Insights", expanded=False):
        st.markdown("#### 1) Model used for Safety (minimum) and Optimal (maximum) levels")
        st.markdown(
            "- **Forecast (3MMA)** estimates expected demand for the next month.\n"
            "- **Monthly volatility (σ)** is computed as the standard deviation of historical monthly sales.\n"
            "- **Safety Stock (minimum threshold):** **Safety = Z × σ**\n"
            "- **Optimal Stock (target / maximum):** **Optimal = Forecast + Safety**"
        )

        st.markdown("#### 2) How the 3MMA forecast was computed")
        st.markdown(
            "- For month *t*: **MA₃(t) = (Sales(t-2) + Sales(t-1) + Sales(t)) / 3**\n"
            "- The **next-month forecast** is: **Forecast(next) = mean(last 3 observed months)**\n"
            "- If fewer than 3 months exist, the model falls back to the mean of available months."
        )

        st.markdown("#### 3) How Z is computed (service level factor)")
        st.markdown(
            f"- Service level = **{SERVICE_LEVEL:.0%}**\n"
            f"- Compute: **Z = Φ⁻¹(service level)** using the standard normal distribution.\n"
            f"- Here: **Z ≈ {Z_SERVICE:.2f}**"
        )

        expected_units_horizon = float(forecast_next_val * HORIZON_MONTHS)
        st.markdown("#### 4) Expected units for the projected horizon")
        st.markdown(
            f"**Scope selected:** `{scope_title}`  \n"
            f"**Projected horizon:** `{HORIZON_MONTHS}` month(s)  \n\n"
            f"**Expected units to be sold in the projected period:** **{int(round(expected_units_horizon))} units**"
        )

    # -----------------------------
    # TABLE: STOCK STATUS vs OPTIMAL (3M) + RESTOCK 1M + FORECAST NEXT 3
    # -----------------------------
    st.markdown("---")
    st.subheader("Stock Status vs 3-Month Optimal Stock (with 1-Month Restock)")

    H_TABLE = 3

    forecast_3m_total = float(forecast_next_val * H_TABLE)
    sigma_3m = sigma_month * np.sqrt(H_TABLE)
    safety_3m = float(Z_SERVICE * sigma_3m)
    optimal_3m = max(float(forecast_3m_total + safety_3m), 0.0)
    optimal_3m_int = int(round(optimal_3m))

    rows = []
    product_type_name = "All Product Types" if scope_choice == all_label else scope_choice
    stock = optimal_3m_int

    # --- Historical periods (simulate inventory with restock to 1M optimal) ---
    for _, row_ in monthly_cnt.iterrows():
        period_label = row_["Month_dt"].strftime("%Y-%m")
        total_sales = int(row_["Sales_Count"])

        stock = max(stock - total_sales, 0)
        restock_to_opt_1m = max(optimal_1m_int - stock, 0)

        rows.append({
            "Product Type": product_type_name,
            "Period": period_label,
            "Total Sales (units)": total_sales,
            "Stock Status (units)": stock,
            "Re-stock to Optimal 1M (units)": restock_to_opt_1m,
        })

        stock += restock_to_opt_1m

    # --- Future projected periods (next H_TABLE months) ---
    forecast_next_val_int = int(round(forecast_next_val))

    for k in range(1, H_TABLE + 1):
        future_dt = monthly_cnt["Month_dt"].max() + pd.DateOffset(months=k)
        period_label = future_dt.strftime("%Y-%m")
        total_sales = forecast_next_val_int

        stock = max(stock - total_sales, 0)
        restock_to_opt_1m = max(optimal_1m_int - stock, 0)

        rows.append({
            "Product Type": product_type_name,
            "Period": period_label,
            "Total Sales (units)": total_sales,
            "Stock Status (units)": stock,
            "Re-stock to Optimal 1M (units)": restock_to_opt_1m,
        })

        stock += restock_to_opt_1m

    table_df = pd.DataFrame(rows)

    # --- Attribute suggestions (based on historical sales prior to each period) ---
    attr_cols = ["Species", "Grade", "Finish", "Dominant Color", "Color Count (#)"]
    df_attr = df_scope.copy()

    if "Month" not in df_attr.columns:
        df_attr["Month"] = pd.to_datetime(df_attr["Date"], errors="coerce").dt.to_period("M").astype(str)

    df_attr["Month_dt"] = pd.to_datetime(df_attr["Month"], format="%Y-%m", errors="coerce")

    for col in attr_cols:
        if col not in df_attr.columns:
            df_attr[col] = "N/A"
        df_attr[col] = df_attr[col].fillna("N/A")

    for col in attr_cols:
        table_df[col] = ""

    for i, row_ in table_df.iterrows():
        period_dt = pd.to_datetime(row_["Period"], format="%Y-%m", errors="coerce")
        df_prev = df_attr[df_attr["Month_dt"] < period_dt].dropna(subset=["Month_dt"])
        if df_prev.empty:
            continue

        top_grp = (
            df_prev.groupby(attr_cols)["Sale ID"]
                  .count()
                  .reset_index(name="Sales_Count")
                  .sort_values("Sales_Count", ascending=False)
                  .head(1)
        )
        if top_grp.empty:
            continue

        top_row = top_grp.iloc[0]
        for col in attr_cols:
            table_df.at[i, col] = top_row[col]

    cols_show = [
        "Product Type",
        "Period",
        "Total Sales (units)",
        "Stock Status (units)",
        "Re-stock to Optimal 1M (units)",
    ] + attr_cols

    # --- Next projected period (the one shown in the line chart) ---
    next_period_dt = monthly_cnt["Month_dt"].max() + pd.DateOffset(months=1)
    next_period_label = next_period_dt.strftime("%Y-%m")

    next_row = table_df.loc[table_df["Period"] == next_period_label].head(1)

    if not next_row.empty:
        next_restock_units = int(next_row["Re-stock to Optimal 1M (units)"].iloc[0])
        specs_txt = (
            f"Species: **{str(next_row['Species'].iloc[0])}**, "
            f"Grade: **{str(next_row['Grade'].iloc[0])}**, "
            f"Finish: **{str(next_row['Finish'].iloc[0])}**, "
            f"Dominant Color: **{str(next_row['Dominant Color'].iloc[0])}**, "
            f"Color Count: **{str(next_row['Color Count (#)'].iloc[0])}**"
        )
    else:
        next_restock_units = None
        specs_txt = None

    # --- Explanation dropdown (only text) ---
    with st.expander("How to read this table", expanded=False):
        st.markdown(
            """
This table uses a **3-month optimal stock level** as a reference and simulates current inventory levels against that target.  
The **Restock** column shows the number of units recommended to purchase in order to reach the optimal level.  
The table highlights which attributes are suggested for replenishment based on recent sales trends.
"""
        )

        if next_restock_units is not None and specs_txt is not None:
            st.markdown(
                f"""
For the **next projected period ({next_period_label})**, the recommended replenishment to reach the optimal level is **{next_restock_units} units**, targeting: {specs_txt}.
"""
            )
        else:
            st.markdown(
                f"""
For the **next projected period ({next_period_label})**, there is not enough data to recommend a restock quantity and attribute specifications.
"""
            )

    # --- Table visible by default (outside expander) ---
    st.dataframe(table_df[cols_show], use_container_width=True)

    csv_data = table_df[cols_show].to_csv(index=False).encode("utf-8")
    file_label = product_type_name.replace(" ", "_").lower()
    st.download_button(
        label="Download stock status table as CSV",
        data=csv_data,
        file_name=f"stock_status_{file_label}.csv",
        mime="text/csv",
    )

# -----------------------------
# Forecast + Timing sub-tabs)
# -----------------------------
if page == 'Inventory Timing':
    st.subheader("Inventory")

    # 6 tabs 
    tab0, tab1, tab2 = st.tabs(
        ["Inventory Forecast", "Timing Curve (CDF)", "Monthly Volume"]
    )

    # -----------------------------
    # SubTab Inventory Forecast 
    # -----------------------------
    with tab0:
        render_inventory_analysis_tab(f)  # uses the filtered df

    # -----------------------------
    # Prep data for Timing tabs (2-6)
    # -----------------------------
    df_f = f.copy()

    # choose best date for shipment timing
    ship_date_col = (
        "Shipped Date"
        if ("Shipped Date" in df_f.columns and df_f["Shipped Date"].notna().any())
        else "Date"
    )
    df_f[ship_date_col] = pd.to_datetime(df_f[ship_date_col], errors="coerce")
    df_f["__month_dt"] = df_f[ship_date_col].dt.to_period("M").dt.to_timestamp()

    # units proxy (use a quantity-like column if exists, else 1 per row)
    unit_candidates = [c for c in ["Units", "Unit", "Quantity", "Qty", "Pieces"] if c in df_f.columns]
    if unit_candidates:
        df_f["__units"] = pd.to_numeric(df_f[unit_candidates[0]], errors="coerce").fillna(0)
    elif "OrderCount" in df_f.columns:
        df_f["__units"] = pd.to_numeric(df_f["OrderCount"], errors="coerce").fillna(1)
    else:
        df_f["__units"] = 1

    # product proxy
    if "Product Type" in df_f.columns:
        df_f["__product"] = df_f["Product Type"].fillna("Unknown").astype(str)
    else:
        df_f["__product"] = "Unknown"

    df_f = df_f.dropna(subset=["__month_dt"])

    monthly_series = (
        df_f.groupby("__month_dt")["__units"]
        .sum()
        .sort_index()
    )

    product_volume = (
        df_f.groupby("__product")["__units"]
        .sum()
        .sort_values()
    )

    total_units = int(monthly_series.sum()) if len(monthly_series) else 0
    avg_monthly = float(monthly_series.mean()) if len(monthly_series) else 0.0
    peak_month = monthly_series.idxmax().strftime("%B %Y") if len(monthly_series) else "—"

    # -----------------------------
    # SubTab Timing Curve (CDF)
    # -----------------------------
    from matplotlib.ticker import PercentFormatter

    with tab1:
        st.subheader("📈 Shipment Timing Curve (CDF)")
        st.write(
            "This curve shows the cumulative percentage of total shipments completed over time. "
            "It helps identify when most inventory movement occurs."
        )

        if monthly_series.empty or monthly_series.sum() == 0:
            st.info("Not enough shipment/timing data to plot under the current filters.")
        else:
            cdf = monthly_series.cumsum() / monthly_series.sum()

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(cdf.index, cdf.values, marker="o")
            ax.set_title("Cumulative Distribution of Shipments")
            ax.set_ylabel("Percentage of Total Shipments")
            ax.yaxis.set_major_formatter(PercentFormatter(1.0))
            ax.set_ylim(0, 1.05)
            ax.grid(alpha=0.25)

            st.pyplot(fig, use_container_width=True)

    # -----------------------------
    # SubTab Monthly Volume
    # -----------------------------
    with tab2:
        st.subheader("📅 Monthly Shipping Volume")

        if monthly_series.empty:
            st.info("Not enough monthly shipment data under current filters.")
        else:
            fig2, ax2 = plt.subplots(figsize=(10, 4))
            ax2.bar(monthly_series.index, monthly_series.values)
            ax2.set_title("Monthly Shipments (Seasonality)")
            ax2.set_ylabel("Units Shipped")
            ax2.grid(alpha=0.25, axis="y")

            st.pyplot(fig2, use_container_width=True)

    st.divider()

    with st.expander("💡 Insights & Executive Summary", expanded=False):

        # ---- Trend Insight ----
        trend_df = monthly_series.reset_index()
        trend_df.columns = ["Month", "Units"]
        trend_df["t"] = np.arange(len(trend_df))

        slope = np.polyfit(trend_df["t"], trend_df["Units"], 1)[0] if len(trend_df) > 1 else 0
        trend_label = "Increasing" if slope > 0.05 else "Decreasing" if slope < -0.05 else "Stable"

        st.markdown("### 📌 Key Insights")
        st.write(f"- Overall shipment trend: **{trend_label}**")
        st.write(f"- Peak shipment month: **{peak_month}**")
        st.write("- The CDF shows when most inventory movement occurs during the year.")
        st.write("- Monthly volume highlights seasonality and demand clustering.")

        st.markdown("### 🧭 Recommendations")
        st.write("- Prepare inventory ahead of peak shipment periods.")
        st.write("- Align procurement cycles with observed shipment timing.")
        st.write("- Review low-activity months to optimize holding costs.")
        st.write("- Consider capturing *Received Date* to enable inventory aging analysis.")

        st.markdown("### 📄 Executive Summary")
        st.write(
            "This section consolidates timing insights derived from shipment behavior. "
            "The cumulative timing curve explains *when* inventory moves, while monthly volume "
            "reveals *how much* moves over time. Together, these insights support better "
            "inventory planning, replenishment, and operational efficiency."
        )


# -----------------------------
# End of TAB 6: Inventory Timing 
# -----------------------------

# ============================
# TAB 7: OWNERSHIP
# ============================
#-----Helpers--------#

def render_ownership_analysis_tab(df_in: pd.DataFrame):
    st.markdown("### Ownership Analysis – Revenue, Units, Sale Amount & Efficiency")

    df = _ensure_month_and_ownership(df_in)

    # Basic validations
    required_cols = ["Ownership", "Price (CAD)", "Sale ID", "Month"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns in dataset: {missing}")
        return

    # Monthly revenue pivot (Owned vs Consigned)
    monthly_revenue = (
        df.groupby(["Month", "Ownership"])["Price (CAD)"]
          .sum()
          .reset_index()
          .pivot(index="Month", columns="Ownership", values="Price (CAD)")
          .fillna(0)
    )
    if "Owned" not in monthly_revenue.columns:
        monthly_revenue["Owned"] = 0.0
    if "Consigned" not in monthly_revenue.columns:
        monthly_revenue["Consigned"] = 0.0
    monthly_revenue["Total"] = monthly_revenue.sum(axis=1)

    # KPIs (REMOVE "Total Sales (CAD)")
    c1, c2, c3, c4 = st.columns(4)

    revenue_by_ownership = df.groupby("Ownership")["Price (CAD)"].sum().to_dict()
    total_revenue = sum(revenue_by_ownership.values())

    owned_revenue = float(revenue_by_ownership.get("Owned", 0.0))
    consigned_revenue = float(revenue_by_ownership.get("Consigned", 0.0))

    owned_pct = (owned_revenue / total_revenue * 100) if total_revenue > 0 else 0.0
    consigned_pct = (consigned_revenue / total_revenue * 100) if total_revenue > 0 else 0.0

    monthly_revenue_sorted = monthly_revenue.copy()
    monthly_revenue_sorted["Month_dt"] = pd.to_datetime(monthly_revenue_sorted.index, format="%Y-%m", errors="coerce")
    monthly_revenue_sorted = monthly_revenue_sorted.dropna(subset=["Month_dt"]).sort_values("Month_dt")
    growth_series = monthly_revenue_sorted["Total"].pct_change().dropna()
    avg_monthly_growth_pct = float(growth_series.mean() * 100) if not growth_series.empty else 0.0

    c1.metric("Owned Revenue %", f"{owned_pct:.1f}%")
    c2.metric("Consigned Revenue %", f"{consigned_pct:.1f}%")
    c3.metric("Avg Monthly Revenue Growth", f"{avg_monthly_growth_pct:.1f}%")

    # Commercial ROI KPI (Revenue per Sale) + dynamic "best"
    df_roi_kpi = df.dropna(subset=["Ownership", "Price (CAD)", "Sale ID"]).copy()
    if df_roi_kpi.empty:
        c4.metric("Commercial ROI Advantage", "N/A", delta="Not enough data")
    else:
        roi_base_kpi = (
            df_roi_kpi.groupby("Ownership", as_index=False)
                      .agg(Sales=("Sale ID", "count"), Revenue_CAD=("Price (CAD)", "sum"))
        )
        roi_base_kpi = roi_base_kpi[roi_base_kpi["Sales"] > 0]
        if len(roi_base_kpi) < 2:
            only_row = roi_base_kpi.iloc[0]
            c4.metric("Commercial ROI Advantage", "N/A", delta=f"Only `{only_row['Ownership']}` has valid sales")
        else:
            roi_base_kpi["Revenue_per_Sale"] = roi_base_kpi["Revenue_CAD"] / roi_base_kpi["Sales"]
            best = roi_base_kpi.loc[roi_base_kpi["Revenue_per_Sale"].idxmax()]
            worst = roi_base_kpi.loc[roi_base_kpi["Revenue_per_Sale"].idxmin()]
            if float(worst["Revenue_per_Sale"]) > 0:
                ratio = float(best["Revenue_per_Sale"]) / float(worst["Revenue_per_Sale"])
                pct_advantage = (ratio - 1.0) * 100.0
                c4.metric("Commercial ROI Advantage", f"{pct_advantage:,.0f}%", delta=f"Best ROI: {best['Ownership']}")
            else:
                c4.metric("Commercial ROI Advantage", "∞", delta=f"Best ROI: {best['Ownership']}")

    st.markdown("---")
    st.subheader("Monthly Trend: Owned vs Consigned")

    view_option = st.radio(
        "Select metric to display:",
        ["Revenue (CAD)", "Sales Count"],
        horizontal=True,
        key=wkey("own_metric")
    )

    # Revenue time series
    rev_df = monthly_revenue[["Owned", "Consigned"]].copy().reset_index()
    rev_df["Month_dt"] = pd.to_datetime(rev_df["Month"], format="%Y-%m", errors="coerce")
    rev_df = rev_df.dropna(subset=["Month_dt"]).sort_values("Month_dt")

    # Sales counts time series
    monthly_count = (
        df.groupby(["Month", "Ownership"])["Sale ID"]
          .count()
          .reset_index(name="Sales_Count")
          .pivot(index="Month", columns="Ownership", values="Sales_Count")
          .fillna(0)
    )
    if "Owned" not in monthly_count.columns:
        monthly_count["Owned"] = 0
    if "Consigned" not in monthly_count.columns:
        monthly_count["Consigned"] = 0
    count_df = monthly_count.reset_index()
    count_df["Month_dt"] = pd.to_datetime(count_df["Month"], format="%Y-%m", errors="coerce")
    count_df = count_df.dropna(subset=["Month_dt"]).sort_values("Month_dt")

    if view_option == "Revenue (CAD)":
        base_df = rev_df.copy()
        y_label = "Revenue (CAD)"
        name_owned = "Owned Revenue"
        name_cons = "Consigned Revenue"
    else:
        base_df = count_df.copy()
        y_label = "Sales Count"
        name_owned = "Owned Sales Count"
        name_cons = "Consigned Sales Count"

    # Trending Line (3M MA)
    if len(base_df) >= 3:
        last_month = base_df["Month_dt"].max()
        next_month = last_month + pd.DateOffset(months=1)

        owned_series = base_df["Owned"].astype(float)
        owned_hist_ma = owned_series.rolling(window=3, min_periods=3).mean()
        owned_next = float(owned_series.tail(3).mean())

        cons_series = base_df["Consigned"].astype(float)
        cons_hist_ma = cons_series.rolling(window=3, min_periods=3).mean()
        cons_next = float(cons_series.tail(3).mean())

        x_forecast = pd.concat([base_df["Month_dt"], pd.Series([next_month])], ignore_index=True)
        y_owned_forecast = pd.concat([owned_hist_ma, pd.Series([owned_next])], ignore_index=True)
        y_cons_forecast = pd.concat([cons_hist_ma, pd.Series([cons_next])], ignore_index=True)
    else:
        x_forecast = base_df["Month_dt"]
        y_owned_forecast = pd.Series([None] * len(base_df))
        y_cons_forecast = pd.Series([None] * len(base_df))

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=base_df["Month_dt"], y=base_df["Owned"], mode="lines+markers", name=name_owned))
    fig_line.add_trace(go.Scatter(x=base_df["Month_dt"], y=base_df["Consigned"], mode="lines+markers", name=name_cons))

    # Rename "Forecast (3M MA)" -> "Trending Line"
    fig_line.add_trace(go.Scatter(
        x=x_forecast,
        y=y_owned_forecast,
        mode="lines+markers",
        name=f"{name_owned} – Trending Line",
        line=dict(dash="dash")
    ))
    fig_line.add_trace(go.Scatter(
        x=x_forecast,
        y=y_cons_forecast,
        mode="lines+markers",
        name=f"{name_cons} – Trending Line",
        line=dict(dash="dash")
    ))

    fig_line.update_layout(
        xaxis_title="Month",
        yaxis_title=y_label,
        legend_title="Ownership / Trend",
        height=450
    )

    col_fc1, col_fc2 = st.columns([2, 1])
    with col_fc1:
        st.plotly_chart(fig_line, use_container_width=True)

    with col_fc2:
        st.markdown("#### Forecasted Units by Product Type, Grade & Ownership (Next Month)")

        selected_pt = None
        total_all = None

        if view_option != "Sales Count":
            st.info("Switch to 'Sales Count' to see units forecast by Product Type, Grade & Ownership.")
        else:
            if "Product Type" not in df.columns:
                st.info("No Product Type column available.")
            else:
                product_types = sorted(df["Product Type"].dropna().unique().tolist())
                if not product_types:
                    st.write("No product type data available.")
                else:
                    selected_pt = st.selectbox("Select Product Type:", product_types, key=wkey("pt_select"))

                    df_pt = df[df["Product Type"] == selected_pt].copy()

                    monthly_pt_own_grade = (
                        df_pt.groupby(["Month", "Ownership", "Grade"])["Sale ID"]
                             .count()
                             .reset_index(name="Sales_Count")
                    )

                    if monthly_pt_own_grade.empty or monthly_pt_own_grade["Month"].nunique() < 3:
                        st.write("Not enough data (≥ 3 months) to compute a 3-month forecast for this product type.")
                    else:
                        monthly_pt_own_grade["Month_dt"] = pd.to_datetime(
                            monthly_pt_own_grade["Month"], format="%Y-%m", errors="coerce"
                        )
                        monthly_pt_own_grade = monthly_pt_own_grade.dropna(subset=["Month_dt"]).sort_values("Month_dt")

                        unique_months = monthly_pt_own_grade["Month_dt"].drop_duplicates().sort_values()
                        last3_months = unique_months.tail(3)

                        last3 = monthly_pt_own_grade[monthly_pt_own_grade["Month_dt"].isin(last3_months)]
                        forecast_by_own_grade = (
                            last3.groupby(["Ownership", "Grade"])["Sales_Count"]
                                 .mean()
                                 .reset_index(name="Forecast_Units")
                        )
                        forecast_by_own_grade["Forecast_Units"] = forecast_by_own_grade["Forecast_Units"].round().astype(int)

                        totals_by_own = (
                            forecast_by_own_grade.groupby("Ownership")["Forecast_Units"]
                                                 .sum()
                                                 .reset_index(name="Total_Units")
                        )
                        total_all = int(forecast_by_own_grade["Forecast_Units"].sum())

                        st.markdown("**Total forecasted units (next month) by Ownership**")
                        st.dataframe(totals_by_own, hide_index=True, use_container_width=True)
                        st.metric("Total forecasted units (next month – all ownerships)", total_all)

                        ownership_options = totals_by_own["Ownership"].tolist()
                        if ownership_options:
                            selected_own = st.radio(
                                "Show grade detail for:",
                                ownership_options,
                                horizontal=True,
                                key=wkey("own_detail")
                            )
                            detail_filtered = forecast_by_own_grade[forecast_by_own_grade["Ownership"] == selected_own]
                            st.markdown(f"**Detail by Grade – {selected_own}**")
                            st.dataframe(
                                detail_filtered[["Grade", "Forecast_Units"]],
                                hide_index=True,
                                use_container_width=True
                            )

        with st.expander("Insights: Forecast model (Next Month)", expanded=False):
            st.markdown(
                "- The forecast is a **3-month moving average (3MMA)** computed on **Sales Count** (units).\n"
                "- For each **Ownership × Grade** segment: **Forecast(next month) = mean(units in last 3 months)**.\n"
                "- Requires **≥ 3 distinct months** for the selected Product Type."
            )

            # Add final recommendation line (uses selected Product Type + total_all)
            if selected_pt is not None and total_all is not None:
                st.markdown(
                    f"- **Recommendations:** Due the trending line, we recommend ensuring at least **{int(total_all)} units** "
                    f"for **{selected_pt}** for the next month, and splitting it by the ownership detailed above."
                )

    st.markdown("---")
    st.subheader("Commercial ROI and Monthly Mean Sale Amount by Ownership")

    df_roi = df.copy()
    df_roi = df_roi.dropna(subset=["Ownership", "Price (CAD)", "Sale ID"])
    if df_roi.empty:
        st.info("No data available to compute commercial ROI.")
        return

    roi_base = (
        df_roi.groupby("Ownership", as_index=False)
              .agg(Sales=("Sale ID", "count"), Revenue_CAD=("Price (CAD)", "sum"))
    )
    roi_base["Revenue_per_Sale"] = roi_base["Revenue_CAD"] / roi_base["Sales"]
    roi_base["Revenue_CAD"] = roi_base["Revenue_CAD"].round(2)
    roi_base["Revenue_per_Sale"] = roi_base["Revenue_per_Sale"].round(2)

    mean_sale_amount_monthly = (
        df.groupby(["Month", "Ownership"])["Price (CAD)"]
          .mean()
          .reset_index(name="Mean_Sale_Amount_CAD")
    )
    mean_sale_amount_monthly["Month_dt"] = pd.to_datetime(mean_sale_amount_monthly["Month"], format="%Y-%m", errors="coerce")
    mean_sale_amount_monthly = mean_sale_amount_monthly.dropna(subset=["Month_dt"]).sort_values("Month_dt")

    col_roi, col_mean = st.columns(2)
    with col_roi:
        fig_roi = px.bar(
            roi_base,
            x="Revenue_per_Sale",
            y="Ownership",
            orientation="h",
            text="Revenue_per_Sale",
            labels={"Revenue_per_Sale": "Commercial ROI (Revenue per Sale, CAD)", "Ownership": "Ownership"},
            title="Commercial ROI by Ownership",
        )
        fig_roi.update_traces(texttemplate="$%{text:,.2f}", textposition="outside")
        fig_roi.update_layout(xaxis_title="Revenue per Sale (CAD)", yaxis_title="Ownership", height=450)
        st.plotly_chart(fig_roi, use_container_width=True)

    with col_mean:
        fig_mean_sale_amount_month = px.bar(
            mean_sale_amount_monthly,
            x="Month_dt",
            y="Mean_Sale_Amount_CAD",
            color="Ownership",
            barmode="group",
            labels={"Month_dt": "Month", "Mean_Sale_Amount_CAD": "Mean Sale Amount (CAD)", "Ownership": "Ownership"},
            title="Monthly Mean Sale Amount by Ownership",
        )
        fig_mean_sale_amount_month.update_layout(xaxis_tickformat="%Y-%m")
        st.plotly_chart(fig_mean_sale_amount_month, use_container_width=True)

    st.markdown("#### Summary (Commercial ROI vs Volume)")
    with st.expander("What is Commercial ROI and how is it calculated?", expanded=False):
        st.markdown(
            "- **Commercial ROI (in this dashboard)** is a *sales-efficiency proxy*, not an accounting ROI.\n"
            "- We define it as **Revenue per Sale**: **Total Revenue (CAD) / Number of Sales**.\n"
            "- It compares **sale amount power** vs **volume**, but does not include costs, margins, or inventory investment."
        )

    st.dataframe(roi_base[["Ownership", "Sales", "Revenue_CAD", "Revenue_per_Sale"]], use_container_width=True)
    if len(roi_base) >= 2:
        best = roi_base.loc[roi_base["Revenue_per_Sale"].idxmax()]
        worst = roi_base.loc[roi_base["Revenue_per_Sale"].idxmin()]
        if float(worst["Revenue_per_Sale"]) > 0:
            ratio = float(best["Revenue_per_Sale"]) / float(worst["Revenue_per_Sale"])
            st.markdown(
                f"**Recommendation:** On average, each `{best['Ownership']}` sale generates "
                f"**{ratio:,.1f}×** more revenue than each `{worst['Ownership']}` sale."
            )
        else:
            st.markdown(
                f"**Recommendation:** `{best['Ownership']}` shows the highest commercial ROI "
                f"(revenue per sale). `{worst['Ownership']}` has very low or zero ROI."
            )

    # Product profiles
    st.markdown("---")
    col_prof1, col_prof2 = st.columns(2)

    group_cols = ["Product Type", "Species", "Grade", "Finish", "Dominant Color", "Color Count (#)"]

    df_combo = df.dropna(subset=["Product Type"]).copy()
    for c in group_cols:
        if c not in df_combo.columns:
            df_combo[c] = "N/A"
        df_combo[c] = df_combo[c].fillna("N/A")

    # Capture descriptions for recommendations
    top_mean_desc = {}      # { "Owned": "desc", "Consigned": "desc" }
    most_freq_desc = {}     # { "Owned": "desc", "Consigned": "desc" }

    with col_prof1:
        st.markdown("#### Top Product Profile by Mean Sale Amount per Ownership")

        if df_combo.empty:
            st.info("No product data available to compute top product profiles.")
        else:
            group_cols_own = ["Ownership"] + group_cols
            hv_agg_own = (
                df_combo.groupby(group_cols_own)["Price (CAD)"]
                        .agg(Mean_Sale_Amount_CAD="mean", Sales_Count="count")
                        .reset_index()
            )

            ownership_order = ["Owned", "Consigned"]
            available_owns = [o for o in ownership_order if o in hv_agg_own["Ownership"].unique().tolist()]
            if not available_owns:
                available_owns = sorted(hv_agg_own["Ownership"].dropna().unique().tolist())

            if not available_owns:
                st.info("No ownership data available to compute profiles.")
            else:
                for own_label in available_owns:
                    subset = hv_agg_own[hv_agg_own["Ownership"] == own_label]
                    if subset.empty:
                        continue

                    idx = subset["Mean_Sale_Amount_CAD"].idxmax()
                    row = subset.loc[idx]

                    parts = []
                    for c in group_cols:
                        v = row[c]
                        if c == "Color Count (#)":
                            try:
                                v = int(v)
                            except Exception:
                                pass
                        parts.append(str(v))

                    combo_label = " – ".join(parts)
                    mean_val = float(row["Mean_Sale_Amount_CAD"])
                    sales_n = int(row["Sales_Count"])

                    top_mean_desc[own_label] = combo_label

                    st.metric(
                        label=f"{own_label} – Top Mean Sale Amount",
                        value=f"${mean_val:,.2f}",
                        delta=f"{combo_label} | Total sales: {sales_n}"
                    )

    with col_prof2:
        st.markdown("#### Most Frequent Product Profile by Ownership")

        if df_combo.empty:
            st.info("No product data available to compute frequent product profiles.")
        else:
            group_cols_own = ["Ownership"] + group_cols
            freq_agg = (
                df_combo.groupby(group_cols_own)["Sale ID"]
                        .count()
                        .reset_index(name="Sales_Count")
            )

            ownership_order = ["Owned", "Consigned"]
            available_owns = [o for o in ownership_order if o in freq_agg["Ownership"].unique().tolist()]
            if not available_owns:
                available_owns = sorted(freq_agg["Ownership"].dropna().unique().tolist())

            for own_label in available_owns:
                subset = freq_agg[freq_agg["Ownership"] == own_label]
                if subset.empty:
                    continue

                row = subset.sort_values("Sales_Count", ascending=False).iloc[0]

                parts = []
                for c in group_cols:
                    v = row[c]
                    if c == "Color Count (#)":
                        try:
                            v = int(v)
                        except Exception:
                            pass
                    parts.append(str(v))

                combo_label = " – ".join(parts)
                sales_n = int(row["Sales_Count"])

                most_freq_desc[own_label] = combo_label

                st.metric(
                    label=f"{own_label} – Most Frequent Profile",
                    value=f"{sales_n} sales",
                    delta=combo_label
                )

    # Recommendations dropdown for product profiles
    with st.expander("Recommendations: Product Profiles", expanded=False):
        owned_top = top_mean_desc.get("Owned", "N/A")
        cons_top = top_mean_desc.get("Consigned", "N/A")
        owned_freq = most_freq_desc.get("Owned", "N/A")
        cons_freq = most_freq_desc.get("Consigned", "N/A")

        st.markdown(
            f"""
It is recommended to encourage sales of the following product profiles, as they represent the highest **average sale amount** per ownership:

- **Owned – Top Mean Sale Amount:** {owned_top}  
- **Consigned – Top Mean Sale Amount:** {cons_top}

It is recommended to maintain an optimal inventory level per ownership for the following profiles, as they represent the **highest sales frequency**:

- **Owned – Most Frequent Profile:** {owned_freq}  
- **Consigned – Most Frequent Profile:** {cons_freq}
"""
        )

    st.markdown("---")
    st.subheader("Sale Amount Distribution by Ownership")

    df_eff = df.dropna(subset=["Price (CAD)"]).copy()
    if df_eff.empty:
        st.info("No data available to plot sale amount distribution.")
    else:
        fig_violin = px.violin(
            df_eff,
            x="Ownership",
            y="Price (CAD)",
            box=True,
            points="all",
            labels={"Ownership": "Ownership", "Price (CAD)": "Sale Amount (Price per Sale, CAD)"},
            title="Distribution of Sale Amount per Ownership (Price per Sale)",
        )
        fig_violin.update_layout(height=500)
        st.plotly_chart(fig_violin, use_container_width=True)

        with st.expander("How to read this violin plot (terms)", expanded=False):
            st.markdown(
                "- **Violin width** indicates where values are more frequent (higher density).\n"
                "- **Median** is the 50th percentile.\n"
                "- **Q1/Q3** are the 25th/75th percentiles (IQR = Q3 − Q1).\n"
                "- **Upper/Lower fence**: Q3 + 1.5×IQR / Q1 − 1.5×IQR; points beyond are **outliers**."
            )

    st.markdown("---")
    st.subheader("Month-over-Month % Change by Product Type & Ownership")

    metric_choice_pt = st.radio(
        "Metric:",
        ["Sales Count", "Revenue (CAD)"],
        horizontal=True,
        key=wkey("pt_own_mom_metric")
    )

    df_mom_pt = df.dropna(subset=["Product Type"]).copy()
    if df_mom_pt["Month"].nunique() < 2:
        st.info("Not enough monthly data to compute month-over-month change.")
        return

    if metric_choice_pt == "Sales Count":
        agg = (
            df_mom_pt.groupby(["Product Type", "Ownership", "Month"])["Sale ID"]
                     .count()
                     .reset_index(name="Metric_Value")
        )
    else:
        agg = (
            df_mom_pt.groupby(["Product Type", "Ownership", "Month"])["Price (CAD)"]
                     .sum()
                     .reset_index(name="Metric_Value")
        )

    if agg.empty:
        st.info("No data available for the selected metric.")
        return

    pivot = (
        agg.pivot_table(index=["Product Type", "Ownership"], columns="Month", values="Metric_Value", aggfunc="sum")
           .fillna(0)
    )
    pivot = pivot.reindex(sorted(pivot.columns, key=lambda x: pd.to_datetime(x, format="%Y-%m", errors="coerce")), axis=1)

    pct = pivot.pct_change(axis=1) * 100
    pct = pct.replace([np.inf, -np.inf], np.nan)
    pct_clean = pct.round(1).dropna(axis=1, how="all")

    avg_growth = pct_clean.mean(axis=1, skipna=True)
    avg_growth_df = avg_growth.reset_index()
    avg_growth_df.columns = ["Product Type", "Ownership", "Avg_MoM_Growth"]

    kpi_col1, kpi_col2 = st.columns(2)

    with kpi_col1:
        sub_owned = avg_growth_df[avg_growth_df["Ownership"] == "Owned"]
        if not sub_owned.empty:
            best_owned = sub_owned.loc[sub_owned["Avg_MoM_Growth"].idxmax()]
            worst_owned = sub_owned.loc[sub_owned["Avg_MoM_Growth"].idxmin()]

            st.markdown("#### Owned – Long-Term Performance")
            st.metric(
                label=f"Best Avg MoM ({metric_choice_pt})",
                value=f"{best_owned['Avg_MoM_Growth']:+.2f}%",
                delta=f"{best_owned['Product Type']}"
            )
            st.metric(
                label=f"Worst Avg MoM ({metric_choice_pt})",
                value=f"{worst_owned['Avg_MoM_Growth']:+.2f}%",
                delta=f"{worst_owned['Product Type']}"
            )

            with st.expander("Recommendations – Owned (Long-Term Performance)", expanded=False):
                st.markdown(
                    f"""
**{best_owned['Product Type']}** shows the strongest upward trend over time. It is recommended to maintain an optimal inventory allocation.  

**{worst_owned['Product Type']}** shows the most consistent downward trend over time. It is recommended to review seasonality and reassess inventory levels.
"""
                )

    with kpi_col2:
        sub_con = avg_growth_df[avg_growth_df["Ownership"] == "Consigned"]
        if not sub_con.empty:
            best_con = sub_con.loc[sub_con["Avg_MoM_Growth"].idxmax()]
            worst_con = sub_con.loc[sub_con["Avg_MoM_Growth"].idxmin()]

            st.markdown("#### Consigned – Long-Term Performance")
            st.metric(
                label=f"Best Avg MoM ({metric_choice_pt})",
                value=f"{best_con['Avg_MoM_Growth']:+.2f}%",
                delta=f"{best_con['Product Type']}"
            )
            st.metric(
                label=f"Worst Avg MoM ({metric_choice_pt})",
                value=f"{worst_con['Avg_MoM_Growth']:+.2f}%",
                delta=f"{worst_con['Product Type']}"
            )

            with st.expander("Recommendations – Consigned (Long-Term Performance)", expanded=False):
                st.markdown(
                    f"""
**{best_con['Product Type']}** shows the strongest upward trend over time. It is recommended to maintain an optimal inventory allocation.  

**{worst_con['Product Type']}** shows the most consistent downward trend over time. It is recommended to review seasonality and reassess inventory levels.
"""
                )

    st.markdown("Each cell shows the **% change vs previous month** for that Product Type & Ownership.")
    st.dataframe(pct_clean.style.format(lambda v: "—" if pd.isna(v) else f"{v:+.1f}%"), use_container_width=True)

    export_df = pct_clean.reset_index()
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download MoM % change table as CSV",
        data=csv_bytes,
        file_name=f"mom_pct_change_{metric_choice_pt.replace(' ', '_').lower()}.csv",
        mime="text/csv",
    )


if page == 'Ownership':
    # Integrated from sales_analysis.py: Ownership Analysis logic
    render_ownership_analysis_tab(f)

# ============================
# End of TAB 7: OWNERSHIP
# ============================


# -----------------------------
# TAB: Seasonality (upgrade)
# -----------------------------
if page == 'Seasonality':

    # =========================================================
    # Header Row: Title + Caption (LEFT) | Time Grain (RIGHT)
    # =========================================================
    h_left, h_right = st.columns([0.75, 0.25], vertical_alignment="top")

    with h_left:
        st.markdown("## Seasonality Analysis")
        st.caption(
            "These three views collectively reveal where pricing sensitivity impacts performance, "
            "which months are most vulnerable due to product dependency, and which products remain "
            "reliable campaign candidates during seasonal slowdowns."
        )

    with h_right:
        grain = st.radio(
            "Time Grain",
            ["Monthly", "Weekly"],
            index=0,
            horizontal=True,
            key=pkey("seasonality_time_grain"),
        )

    # =========================================================
    # Base dataframe
    # =========================================================
    t_df = f.copy()

    # ---- pick revenue + price columns ----
    if "Net Sales" in t_df.columns:
        revenue_col = "Net Sales"
    elif "Price (CAD)" in t_df.columns:
        revenue_col = "Price (CAD)"
    else:
        revenue_col = metric_col

    price_col = "Price (CAD)" if "Price (CAD)" in t_df.columns else revenue_col

    # ---- ensure Date / Month exist ----
    if "Date" in t_df.columns:
        t_df["Date"] = pd.to_datetime(t_df["Date"], errors="coerce")

    if "Month" in t_df.columns:
        t_df["Month"] = pd.to_datetime(t_df["Month"], errors="coerce")
    elif "Date" in t_df.columns:
        t_df["Month"] = t_df["Date"].dt.to_period("M").dt.to_timestamp()
    else:
        t_df["Month"] = pd.NaT

    # ---- numeric safety ----
    t_df[revenue_col] = pd.to_numeric(t_df[revenue_col], errors="coerce")
    t_df[price_col] = pd.to_numeric(t_df[price_col], errors="coerce")

    # =========================================================
    # Normalize Period based on Time Grain
    # =========================================================
    if grain == "Weekly":
        if "Date" not in t_df.columns:
            st.warning("Weekly view requires a 'Date' column. Falling back to Monthly.")
            grain = "Monthly"
        else:
            t_df["PeriodStart"] = t_df["Date"].dt.to_period("W-MON").dt.start_time
            t_df["PeriodLabel"] = t_df["PeriodStart"].dt.strftime("Wk of %b %d, %Y")
            PERIOD_NAME = "Week"
            X_TICKFORMAT = "%b %d<br>%Y"
            X_DTICK = "D7"

    if grain == "Monthly":
        t_df["PeriodStart"] = pd.to_datetime(t_df["Month"], errors="coerce").dt.to_period("M").dt.to_timestamp()
        t_df["PeriodLabel"] = t_df["PeriodStart"].dt.strftime("%b %Y")
        PERIOD_NAME = "Month"
        X_TICKFORMAT = "%b %Y"
        X_DTICK = "M1"

    # =========================================================
    # Subtabs (unchanged)
    # =========================================================
    s1, s2, s3 = st.tabs(
        [
            "Price Elasticity",
            "Revenue Fragility",
            "Seasonal Campaign Opportunities",
        ]
    )

   # =========================================================
    # SUBTAB 1 — Seasonal Price Sensitivity (DUAL-SCOPE LINES)
    # Bubbles/Flags = filtered by Product Type
    # Revenue + Volume lines = ALWAYS ALL SALES (do NOT change with Product Type filter)
    # X = MonthStart (Month-Year) | Y = Revenue
    # Bubble Size = Avg Price | Color = Grade
    # Flags (high-confidence) per Grade vs rolling 3-period baseline:
    #   Avg Price >= +5% AND Revenue <= -10% AND Volume <= -10%
    # Bubble hover shows Flag Type + Flag Reason ONLY when flagged
    # =========================================================
    with s1:
        # -----------------------------
        # Title + Help button (same row)
        # -----------------------------
        t1, t2 = st.columns([0.85, 0.15], vertical_alignment="center")
        with t1:
            st.subheader("Seasonal Price Sensitivity & Revenue Impact")
        with t2:
            if st.button("❓ Help", key=pkey("seasonality_help_btn")):
                show_seasonality_help()

        # -----------------------------
        # Validation
        # -----------------------------
        if "Product Type" not in t_df.columns or "Grade" not in t_df.columns:
            st.info("Need both 'Product Type' and 'Grade' columns to build this view.")
        elif "Month" not in t_df.columns:
            st.info("Need 'Month' column for Month-Year seasonality view.")
        else:
            df_el = t_df.dropna(subset=["Month", "Product Type", "Grade", price_col, revenue_col]).copy()

            if df_el.empty:
                st.info("Not enough Month + Product Type + Grade + Price + Revenue data.")
            else:
                # -----------------------------
                # Normalize Month
                # -----------------------------
                df_el["MonthStart"] = (
                    pd.to_datetime(df_el["Month"], errors="coerce")
                    .dt.to_period("M")
                    .dt.to_timestamp()
                )
                df_el = df_el.dropna(subset=["MonthStart"])
                df_el["MonthLabel"] = df_el["MonthStart"].dt.strftime("%b %Y")

                # ✅ df_all is ALWAYS all sales (used for revenue/volume lines)
                df_all = df_el.copy()

                # -----------------------------
                # Product Type Filter (bubbles + flags only)
                # -----------------------------
                pt_list = sorted(df_el["Product Type"].astype(str).unique().tolist())
                pt_choice = st.selectbox(
                    "Filter by Product Type (bubbles + flags only)",
                    options=["All"] + pt_list,
                    index=0,
                    key=pkey("seasonality_pt_filter"),
                )

                df_view = df_el if pt_choice == "All" else df_el[df_el["Product Type"].astype(str) == pt_choice]

                if df_view.empty:
                    st.info("No data for the selected Product Type.")
                else:
                    # -----------------------------
                    # Aggregate Month x Grade (FILTERED)
                    # -----------------------------
                    base = (
                        df_view.groupby(["MonthStart", "Grade"], as_index=False)
                        .agg(
                            Avg_Price=(price_col, "mean"),
                            Revenue=(revenue_col, "sum"),
                            Volume=(revenue_col, "size"),  # txn count as proxy volume
                        )
                        .sort_values("MonthStart")
                    )

                    if base.empty:
                        st.info("No data after grouping.")
                    else:
                        base["Grade"] = base["Grade"].astype(str)
                        base["MonthLabel"] = base["MonthStart"].dt.strftime("%b %Y")

                        # Optional grade ordering (AAA/AA/A/B)
                        grade_order = ["AAA", "AA", "A", "B","Collectibles"]
                        present = [g for g in grade_order if g in base["Grade"].unique()]
                        if present:
                            base["Grade"] = pd.Categorical(base["Grade"], categories=present, ordered=True)
                        base["GradeStr"] = base["Grade"].astype(str)

                        # -----------------------------
                        # HIGH-CONFIDENCE FLAGS (FILTERED, per Grade) vs rolling 3-period baseline
                        # -----------------------------
                        base_sorted = base.sort_values(["GradeStr", "MonthStart"]).copy()

                        base_sorted["Roll_Avg_Price"] = (
                            base_sorted.groupby("GradeStr")["Avg_Price"]
                            .transform(lambda x: x.rolling(3, min_periods=2).mean())
                        )
                        base_sorted["Roll_Revenue"] = (
                            base_sorted.groupby("GradeStr")["Revenue"]
                            .transform(lambda x: x.rolling(3, min_periods=2).mean())
                        )
                        base_sorted["Roll_Volume"] = (
                            base_sorted.groupby("GradeStr")["Volume"]
                            .transform(lambda x: x.rolling(3, min_periods=2).mean())
                        )

                        base_sorted["Price_vs_Roll_%"] = np.where(
                            base_sorted["Roll_Avg_Price"] > 0,
                            (base_sorted["Avg_Price"] - base_sorted["Roll_Avg_Price"]) / base_sorted["Roll_Avg_Price"],
                            np.nan,
                        )
                        base_sorted["Revenue_vs_Roll_%"] = np.where(
                            base_sorted["Roll_Revenue"] > 0,
                            (base_sorted["Revenue"] - base_sorted["Roll_Revenue"]) / base_sorted["Roll_Revenue"],
                            np.nan,
                        )
                        base_sorted["Volume_vs_Roll_%"] = np.where(
                            base_sorted["Roll_Volume"] > 0,
                            (base_sorted["Volume"] - base_sorted["Roll_Volume"]) / base_sorted["Roll_Volume"],
                            np.nan,
                        )

                        base_sorted["Flag_PriceResistance"] = (
                            (base_sorted["Price_vs_Roll_%"] >= 0.05) &
                            (base_sorted["Revenue_vs_Roll_%"] <= -0.10) &
                            (base_sorted["Volume_vs_Roll_%"] <= -0.10)
                        )

                        base_sorted["Flag Reason"] = ""
                        m = base_sorted["Flag_PriceResistance"]
                        base_sorted.loc[m, "Flag Reason"] = (
                            "Avg Price ↑ "
                            + (base_sorted.loc[m, "Price_vs_Roll_%"] * 100).round(1).astype(str)
                            + "%, Revenue ↓ "
                            + (base_sorted.loc[m, "Revenue_vs_Roll_%"] * 100).round(1).astype(str)
                            + "%, Volume ↓ "
                            + (base_sorted.loc[m, "Volume_vs_Roll_%"] * 100).round(1).astype(str)
                            + "% vs 3-period average (same grade)"
                        )

                        flags = base_sorted[base_sorted["Flag_PriceResistance"]].copy()
                        flags["Trigger"] = "Price Resistance (High Confidence)"
                        if not flags.empty:
                            flags["MonthLabel"] = flags["MonthStart"].dt.strftime("%b %Y")

                        # -----------------------------
                        # Flag summary
                        # -----------------------------
                        if flags.empty:
                            st.success("No high-confidence pricing resistance detected for the selected filter.")
                        else:
                            st.warning("High-confidence pricing resistance detected — review ⚠ markers and hover for details.")

                        # -----------------------------
                        # Add flag info into base (for bubble hover)
                        # -----------------------------
                        base["Flag Type"] = ""
                        base["Flag Reason"] = ""
                        if not flags.empty:
                            trig_map = flags.set_index(["MonthStart", "GradeStr"])["Trigger"].to_dict()
                            reas_map = flags.set_index(["MonthStart", "GradeStr"])["Flag Reason"].to_dict()

                            base["Flag Type"] = base.apply(
                                lambda r: trig_map.get((r["MonthStart"], str(r["GradeStr"])), ""),
                                axis=1,
                            )
                            base["Flag Reason"] = base.apply(
                                lambda r: reas_map.get((r["MonthStart"], str(r["GradeStr"])), ""),
                                axis=1,
                            )

                        # -----------------------------
                        # Bubble chart (FILTERED)
                        # -----------------------------
                        fig = px.scatter(
                            base,
                            x="MonthStart",
                            y="Revenue",
                            color="GradeStr",
                            size="Avg_Price",
                            size_max=55,
                            title="",
                        )

                        # -----------------------------
                        # ✅ Total Revenue line (ALL SALES)
                        # -----------------------------
                        rev_line_all = (
                            df_all.groupby("MonthStart", as_index=False)[revenue_col]
                            .sum()
                            .sort_values("MonthStart")
                        )
                        fig.add_scatter(
                            x=rev_line_all["MonthStart"],
                            y=rev_line_all[revenue_col],
                            mode="lines+markers",
                            name="Total Revenue (All Products)",
                            line=dict(width=3),
                            hovertemplate="<b>%{x|%b %Y}</b><br>Total Revenue: $%{y:,.0f}<extra></extra>",
                        )

                        # -----------------------------
                        # ✅ Total Volume line (ALL SALES) — secondary axis
                        # -----------------------------
                        vol_line_all = (
                            df_all.groupby("MonthStart", as_index=False)
                            .size()
                            .rename(columns={"size": "Volume"})
                            .sort_values("MonthStart")
                        )
                        fig.add_scatter(
                            x=vol_line_all["MonthStart"],
                            y=vol_line_all["Volume"],
                            mode="lines+markers",
                            name="Total Volume (All Products)",
                            line=dict(width=2, dash="dot"),
                            yaxis="y2",
                            hovertemplate="<b>%{x|%b %Y}</b><br>Total Volume: %{y:,.0f} txns<extra></extra>",
                        )

                        # -----------------------------
                        # Flag markers (FILTERED) — hover shows ONLY flag type + reason
                        # -----------------------------
                        if not flags.empty:
                            fig.add_scatter(
                                x=flags["MonthStart"],
                                y=flags["Revenue"],
                                mode="markers",
                                name="⚠ Flagged",
                                marker=dict(size=14, symbol="x"),
                                customdata=np.column_stack([
                                    flags["GradeStr"].astype(str),
                                    flags["Flag Reason"].astype(str),
                                    flags["Trigger"].astype(str),
                                ]),
                                hovertemplate=(
                                    "<b>%{x|%b %Y}</b><br>"
                                    "Grade: %{customdata[0]}<br>"
                                    "<b>Flag Type:</b> %{customdata[2]}<br>"
                                    "<b>Flag Reason:</b> %{customdata[1]}"
                                    "<extra></extra>"
                                ),
                            )

                        # -----------------------------
                        # Layout formatting + y2 axis
                        # -----------------------------
                        fig.update_layout(
                            xaxis_title="Month-Year",
                            yaxis_title="Revenue (CAD)",
                            legend_title_text="Grade",
                            hovermode="closest",
                            yaxis2=dict(
                                title="Volume (Transactions)",
                                overlaying="y",
                                side="right",
                                showgrid=False,
                            ),
                        )
                        fig.update_xaxes(type="date", tickformat="%b %Y", dtick="M1")
                        fig.update_yaxes(tickprefix="$", separatethousands=True)

                        # -----------------------------
                        # style_fig (may reset hovertemplates)
                        # -----------------------------
                        fig = style_fig(fig, height=600)

                        # -----------------------------
                        # ✅ FORCE bubble hover AFTER style_fig
                        # Show Flag Type + Flag Reason ONLY when flagged (blank otherwise)
                        # -----------------------------
                        base_plot = base.copy()
                        base_plot["GradeStr"] = base_plot["GradeStr"].astype(str)

                        flag_type = base_plot["Flag Type"].astype(str).fillna("")
                        flag_reason = base_plot["Flag Reason"].astype(str).fillna("")

                        flag_block_type = np.where(flag_type != "", "<b>Flag Type:</b> " + flag_type + "<br>", "")
                        flag_block_reason = np.where(flag_reason != "", "<b>Flag Reason:</b> " + flag_reason, "")

                        # customdata: [Volume, FlagTypeBlock, FlagReasonBlock, Avg_Price]
                        base_cd = np.column_stack([
                            base_plot["Volume"].astype(float),
                            flag_block_type,
                            flag_block_reason,
                            base_plot["Avg_Price"].astype(float),
                        ])

                        for tr in fig.data:
                            # only bubble traces (exclude flagged X markers and the lines)
                            if getattr(tr, "mode", "") == "markers" and tr.name not in ["⚠ Flagged"]:
                                grade_name = str(tr.name)
                                mask = (base_plot["GradeStr"] == grade_name)

                                tr.customdata = base_cd[mask.values]
                                tr.hovertemplate = (
                                    "<b>%{x|%b %Y}</b><br>"
                                    f"Grade: {grade_name}<br>"
                                    "Revenue: $%{y:,.0f}<br>"
                                    "Avg Price: $%{customdata[3]:,.2f}<br>"
                                    "Volume (txn): %{customdata[0]:,.0f}"
                                    "<br><br>"
                                    "%{customdata[1]}%{customdata[2]}"
                                    "<extra></extra>"
                                )

                        # ✅ Re-apply line hovers AFTER style_fig (defensive)
                        for tr in fig.data:
                            if tr.name == "Total Revenue (All Products)":
                                tr.hovertemplate = "<b>%{x|%b %Y}</b><br>Total Revenue: $%{y:,.0f}<extra></extra>"
                            if tr.name == "Total Volume (All Products)":
                                tr.hovertemplate = "<b>%{x|%b %Y}</b><br>Total Volume: %{y:,.0f} txns<extra></extra>"

                        st.plotly_chart(
                            fig,
                            use_container_width=True,
                            key=pkey("seasonality_tab1_dual_scope_lines"),
                        )

        # =========================================================
        # SUBTAB 2 — Fragile Periods (PERCENT + SEASONALITY + DROPDOWN MODE)
        # (hover fixed to not truncate; re-applied after style_fig)
        # =========================================================
        with s2:
            h1, h2 = st.columns([0.85, 0.15], vertical_alignment="center")
            with h1:
                st.subheader("Dependency risk on critical products across seasonal revenue cycles")
            with h2:
                if st.button("❓ Help", key=pkey("fragility_help_btn")):
                    show_fragility_help()

            if "Product Type" not in t_df.columns:
                st.info("Need 'Product Type' to build the fragility scenario.")
            else:
                df2 = t_df.dropna(subset=["PeriodStart", "Product Type", revenue_col]).copy()
                if df2.empty:
                    st.info("Not enough data for the fragility scenario.")
                else:
                    mode = st.selectbox(
                        "Critical Product Method",
                        options=[
                            "Overall critical product (top revenue across the whole dataset)",
                            "Seasonal critical product (top revenue per period)",
                        ],
                        index=0,
                        key=pkey("fragility_critical_mode"),
                    )

                    # Totals per period
                    totals = df2.groupby("PeriodStart")[revenue_col].sum().sort_index()
                    out = pd.DataFrame({"PeriodStart": totals.index, "Total": totals.values}).sort_values("PeriodStart")
                    out["PeriodLabel"] = out["PeriodStart"].dt.strftime("Wk of %b %d, %Y" if grain == "Weekly" else "%b %Y")

                    # Always create columns
                    out["Critical_PT"] = pd.Series([np.nan] * len(out), index=out.index)
                    out["Critical_Grade"] = pd.Series([np.nan] * len(out), index=out.index)

                    critical_pt = "—"
                    critical_grade = "—"

                    if mode.startswith("Overall critical"):
                        pt_tot = df2.groupby("Product Type")[revenue_col].sum().sort_values(ascending=False)
                        critical_pt = str(pt_tot.index[0]) if len(pt_tot) else "Unknown"

                        if "Grade" in df2.columns:
                            g_tot = (
                                df2[df2["Product Type"] == critical_pt]
                                .dropna(subset=["Grade"])
                                .groupby("Grade")[revenue_col]
                                .sum()
                                .sort_values(ascending=False)
                            )
                            critical_grade = str(g_tot.index[0]) if len(g_tot) else "N/A"
                        else:
                            critical_grade = "N/A"

                        critical_by_period = (
                            df2[df2["Product Type"] == critical_pt]
                            .groupby("PeriodStart")[revenue_col]
                            .sum()
                        )
                        out["At_Risk"] = critical_by_period.reindex(out["PeriodStart"]).fillna(0).values
                        out["Critical_PT"] = critical_pt
                        out["Critical_Grade"] = critical_grade

                        at_risk_label = f"At Risk: {critical_pt}"
                        if critical_grade not in ["—", "N/A"]:
                            at_risk_label += f" (Top Grade: {critical_grade})"
                    else:
                        mpt = (
                            df2.groupby(["PeriodStart", "Product Type"], as_index=False)[revenue_col]
                            .sum()
                            .sort_values(["PeriodStart", revenue_col], ascending=[True, False])
                        )
                        top_mpt = mpt.groupby("PeriodStart", as_index=False).head(1).copy()
                        top_mpt = top_mpt.rename(columns={revenue_col: "At_Risk", "Product Type": "Critical_PT"})

                        if top_mpt.empty:
                            out["At_Risk"] = 0.0
                            out["Critical_PT"] = "Unknown"
                            out["Critical_Grade"] = "N/A"
                        else:
                            if "Grade" in df2.columns:
                                mpg = (
                                    df2.dropna(subset=["Grade"])
                                    .groupby(["PeriodStart", "Product Type", "Grade"], as_index=False)[revenue_col]
                                    .sum()
                                    .sort_values(["PeriodStart", "Product Type", revenue_col], ascending=[True, True, False])
                                )
                                top_grade = mpg.groupby(["PeriodStart", "Product Type"], as_index=False).head(1)
                                top_grade = top_grade.rename(columns={"Grade": "Critical_Grade"})
                                top_mpt = top_mpt.merge(
                                    top_grade[["PeriodStart", "Product Type", "Critical_Grade"]],
                                    left_on=["PeriodStart", "Critical_PT"],
                                    right_on=["PeriodStart", "Product Type"],
                                    how="left",
                                ).drop(columns=["Product Type"])
                            else:
                                top_mpt["Critical_Grade"] = "N/A"

                            out = out.merge(
                                top_mpt[["PeriodStart", "At_Risk", "Critical_PT", "Critical_Grade"]],
                                on="PeriodStart",
                                how="left",
                                suffixes=("", "_m"),
                            )

                            # ✅ If merge created suffixed columns, use them
                            if "Critical_PT_m" in out.columns:
                                out["Critical_PT"] = out["Critical_PT_m"].combine_first(out["Critical_PT"])
                                out.drop(columns=["Critical_PT_m"], inplace=True)

                            if "Critical_Grade_m" in out.columns:
                                out["Critical_Grade"] = out["Critical_Grade_m"].combine_first(out["Critical_Grade"])
                                out.drop(columns=["Critical_Grade_m"], inplace=True)

                            # ✅ Now safe to fill
                            out["At_Risk"] = out["At_Risk"].fillna(0.0)
                            out["Critical_PT"] = out["Critical_PT"].fillna("Unknown")
                            out["Critical_Grade"] = out["Critical_Grade"].fillna("N/A")



                        at_risk_label = "At Risk: Per-period #1 Product"

                    out["At_Risk_Share"] = np.where(out["Total"] > 0, out["At_Risk"] / out["Total"], 0.0)
                    out["Other_Share"] = (1.0 - out["At_Risk_Share"]).clip(lower=0.0)

                    avg_total = float(out["Total"].mean()) if len(out) else 0.0
                    out["Seasonality_Index"] = np.where(avg_total > 0, out["Total"] / avg_total, np.nan)

                    risk_share_thresh = st.slider(
                        "Seasonal Risk Threshold (At Risk %)",
                        min_value=10,
                        max_value=80,
                        value=35,
                        step=5,
                        key=pkey("frag_risk_thresh"),
                    ) / 100.0
                    out["Seasonal_Risk"] = (out["At_Risk_Share"] >= risk_share_thresh) & (out["Seasonality_Index"] < 1.0)

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric(f"Avg {PERIOD_NAME.lower()} revenue baseline", f"${avg_total:,.0f}" if avg_total else "—")
                    with c2:
                        st.metric("Seasonal risk threshold", f"{int(risk_share_thresh*100)}%")
                    with c3:
                        if mode.startswith("Overall critical"):
                            st.metric("Overall critical product / top grade", f"{critical_pt} / {critical_grade}")
                        else:
                            st.metric("Critical product method", "Per-period (seasonal)")

                    fig = make_subplots(specs=[[{"secondary_y": True}]])

                    fig.add_trace(
                        go.Bar(
                            x=out["PeriodLabel"],
                            y=out["At_Risk_Share"],
                            name=at_risk_label,
                            customdata=np.column_stack([
                                out["Critical_PT"].astype(str),
                                out["Critical_Grade"].astype(str),
                            ]),
                        ),
                        secondary_y=False,
                    )
                    fig.add_trace(
                        go.Bar(
                            x=out["PeriodLabel"],
                            y=out["Other_Share"],
                            name="Total Revenue",
                        ),
                        secondary_y=False,
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=out["PeriodLabel"],
                            y=out["Seasonality_Index"],
                            mode="lines+markers",
                            name=f"Seasonality Index ({PERIOD_NAME} vs Avg)",
                        ),
                        secondary_y=True,
                    )

                    risk_periods = out[out["Seasonal_Risk"]]
                    if not risk_periods.empty:
                        for _, r in risk_periods.iterrows():
                            fig.add_annotation(
                                x=r["PeriodLabel"],
                                y=0.98,
                                xref="x",
                                yref="y",
                                text="⚠ Seasonal Risk",
                                showarrow=False,
                                yanchor="top",
                            )

                    fig.update_layout(
                        barmode="stack",
                        xaxis_title=f"{PERIOD_NAME} (Period)",
                        legend_title_text="Legend",
                        hovermode="x unified",
                    )
                    fig.update_yaxes(
                        title_text="Share of Total Revenue (%)",
                        tickformat=".0%",
                        range=[0, 1],
                        secondary_y=False,
                    )
                    fig.update_yaxes(
                        title_text=f"Seasonality Index (1.0 = Avg {PERIOD_NAME.lower()})",
                        tickformat=".2f",
                        secondary_y=True,
                    )

                    fig = style_fig(fig, height=520)

                    # ✅ Re-apply hover templates AFTER style_fig (and inject at_risk_label correctly)
                    fig.data[0].hovertemplate = (
                        "<b>%{x}</b><br>"
                        "{at_risk_label}: %{y:.0%}<br>"
                        "Critical Product: %{customdata[0]}<br>"
                        "Top Grade: %{customdata[1]}"
                        "<extra></extra>"
                    )
                    fig.data[1].hovertemplate = (
                        "<b>%{x}</b><br>"
                        "Remaining Share: %{y:.0%}"
                        "<extra></extra>"
                    )
                    fig.data[2].hovertemplate = (
                        "<b>%{x}</b><br>"
                        "Seasonality Index: %{y:.2f}"
                        "<extra></extra>"
                    )

                    st.plotly_chart(fig, use_container_width=True, key=pkey("tim_fragile_bar_pct_plus_seasonality_line"))

        # =========================================================
        # SUBTAB 3 — Seasonal Campaign Opportunities (Ranked Heatmap + Opportunity Score in Hover)
        # Uses same PeriodStart/Label + slow-period selection by SeasonalityIndex
        # =========================================================
        with s3:
            h1, h2 = st.columns([0.86, 0.14], vertical_alignment="center")
            with h1:
                st.subheader("Products that consistently capture demand during below-average revenue periods")
            with h2:
                if st.button("❓ Help", key=pkey("seasonality_help_btns")):
                    show_opportunity_help()

            if "Product Type" not in t_df.columns:
                st.info("Need 'Product Type' to build campaign opportunity insights.")
            else:
                df3 = t_df.dropna(subset=["PeriodStart", "Product Type", revenue_col]).copy()
                if df3.empty:
                    st.info("Not enough data to analyze campaign opportunities.")
                else:
                    # Period label already available; keep consistent
                    df3["PeriodLabel"] = df3["PeriodStart"].dt.strftime("Wk of %b %d, %Y" if grain == "Weekly" else "%b %Y")

                    # Totals + Seasonality Index
                    monthly = (
                        df3.groupby("PeriodStart", as_index=False)[revenue_col]
                        .sum()
                        .rename(columns={revenue_col: "TotalRevenue"})
                        .sort_values("PeriodStart")
                    )
                    avg_period = float(monthly["TotalRevenue"].mean()) if len(monthly) else 0.0
                    monthly["SeasonalityIndex"] = np.where(avg_period > 0, monthly["TotalRevenue"] / avg_period, np.nan)
                    monthly["PeriodLabel"] = monthly["PeriodStart"].dt.strftime("Wk of %b %d, %Y" if grain == "Weekly" else "%b %Y")

                    c1, c2, c3 = st.columns([0.4, 0.3, 0.3])
                    with c1:
                        slow_idx = st.slider(
                            f"Slow-period threshold (Seasonality Index) — {PERIOD_NAME}",
                            min_value=0.6,
                            max_value=1.0,
                            value=0.9,
                            step=0.05,
                            key=pkey("camp_slow_idx"),
                        )
                    with c2:
                        top_n = st.slider(
                            f"Number of slow periods to analyze — {PERIOD_NAME}",
                            min_value=3,
                            max_value=24 if grain == "Weekly" else 12,
                            value=8 if grain == "Weekly" else 6,
                            step=1,
                            key=pkey("camp_top_n"),
                        )
                    with c3:
                        metric = st.radio(
                            "Heatmap metric",
                            ["Share of Period (%)", "Revenue (CAD)"],
                            index=0,
                            key=pkey("camp_metric"),
                        )

                    slow_periods = (
                        monthly[monthly["SeasonalityIndex"] < slow_idx]
                        .sort_values("TotalRevenue")
                        .head(top_n)
                        .sort_values("PeriodStart")
                    )

                    if slow_periods.empty:
                        st.info("No periods meet the selected slow-period criteria.")
                    else:
                        period_order = slow_periods["PeriodLabel"].tolist()

                        sub = df3[df3["PeriodStart"].isin(slow_periods["PeriodStart"])].copy()

                        mix = (
                            sub.groupby(["Product Type", "PeriodStart"], as_index=False)[revenue_col]
                            .sum()
                            .rename(columns={revenue_col: "Revenue"})
                        )

                        totals = (
                            mix.groupby("PeriodStart", as_index=False)["Revenue"]
                            .sum()
                            .rename(columns={"Revenue": "PeriodTotal"})
                        )
                        mix = mix.merge(totals, on="PeriodStart", how="left")
                        mix["Share"] = np.where(mix["PeriodTotal"] > 0, mix["Revenue"] / mix["PeriodTotal"], 0.0)
                        mix["PeriodLabel"] = mix["PeriodStart"].dt.strftime("Wk of %b %d, %Y" if grain == "Weekly" else "%b %Y")

                        # Pivot
                        if metric == "Share of Period (%)":
                            pv = (
                                mix.pivot_table(
                                    index="Product Type",
                                    columns="PeriodLabel",
                                    values="Share",
                                    fill_value=0.0,
                                )
                                .reindex(columns=period_order)
                            )
                        else:
                            pv = (
                                mix.pivot_table(
                                    index="Product Type",
                                    columns="PeriodLabel",
                                    values="Revenue",
                                    fill_value=0.0,
                                )
                                .reindex(columns=period_order)
                            )

                        # Ranking
                        prod_stats = (
                            mix.groupby("Product Type", as_index=False)
                            .agg(
                                Avg_Share=("Share", "mean"),
                                Total_Revenue=("Revenue", "sum"),
                                Periods_Present=("PeriodStart", "nunique"),
                            )
                        )
                        total_periods = len(slow_periods)
                        prod_stats["Consistency_%"] = np.where(
                            total_periods > 0,
                            prod_stats["Periods_Present"] / total_periods,
                            0.0,
                        )
                        prod_stats["Opportunity_Score"] = (
                            prod_stats["Consistency_%"] * 0.6 +
                            prod_stats["Avg_Share"] * 0.4
                        )
                        prod_stats = prod_stats.sort_values("Opportunity_Score", ascending=False).reset_index(drop=True)
                        prod_stats["Rank"] = prod_stats.index + 1

                        rank_label_map = {
                            row["Product Type"]: f"{int(row['Rank'])}. {row['Product Type']}"
                            for _, row in prod_stats.iterrows()
                        }

                        pv_ranked = pv.reindex(prod_stats["Product Type"].tolist()).copy()
                        pv_ranked.index = pv_ranked.index.map(lambda x: rank_label_map.get(x, x))

                        color_label = "Share of Period" if metric == "Share of Period (%)" else "Revenue (CAD)"
                        fig = px.imshow(
                            pv_ranked,
                            aspect="auto",
                            color_continuous_scale="Blues",
                            labels=dict(
                                x=f"Slow {PERIOD_NAME} (Period)",
                                y="Product Type (Ranked)",
                                color=color_label,
                            ),
                            title="",
                        )

                        if metric == "Share of Period (%)":
                            fig.update_coloraxes(colorbar_tickformat=".0%")
                        else:
                            fig.update_coloraxes(colorbar_tickprefix="$", colorbar_separatethousands=True)

                        fig = style_fig(fig, height=520)

                        opp_score_map = prod_stats.set_index("Product Type")["Opportunity_Score"].to_dict()
                        rank_map = prod_stats.set_index("Product Type")["Rank"].to_dict()

                        row_products = [
                            label.split(". ", 1)[1] if ". " in label else label
                            for label in pv_ranked.index.tolist()
                        ]
                        row_customdata = np.column_stack([
                            [rank_map.get(p, np.nan) for p in row_products],
                            [opp_score_map.get(p, np.nan) for p in row_products],
                        ])

                        rows, cols = pv_ranked.shape
                        customdata = np.repeat(row_customdata[:, None, :], cols, axis=1)

                        heat = fig.data[0]
                        heat.customdata = customdata

                        if metric == "Share of Period (%)":
                            heat.hovertemplate = (
                                "<b>%{y}</b><br>"
                                "Period: %{x}<br>"
                                "Share of Period: %{z:.0%}<br>"
                                "Rank: #%{customdata[0]:.0f}<br>"
                                "Opportunity Score: %{customdata[1]:.3f}"
                                "<extra></extra>"
                            )
                        else:
                            heat.hovertemplate = (
                                "<b>%{y}</b><br>"
                                "Period: %{x}<br>"
                                "Revenue: $%{z:,.0f}<br>"
                                "Rank: #%{customdata[0]:.0f}<br>"
                                "Opportunity Score: %{customdata[1]:.3f}"
                                "<extra></extra>"
                            )

                        st.plotly_chart(fig, use_container_width=True, key=pkey("camp_heatmap_ranked_hover_score"))


    # -----------------------------
    # TAB: Compliance (DIR expanders + metric tiles) — Chart 1 & 3 removed
    # -----------------------------
if page == 'Compliance':
    st.subheader("Compliance – COA & Export Permits")

    # Base = your dashboard's already-filtered dataframe
    c_base = f.copy()

    import math

    # -----------------------------
    # Prep (local to Compliance tab only)
    # -----------------------------
    if "Price (CAD)" in c_base.columns:
        c_base["Price (CAD)"] = pd.to_numeric(c_base["Price (CAD)"], errors="coerce")

    if "Date" in c_base.columns:
        c_base["Date"] = pd.to_datetime(c_base["Date"], errors="coerce")
    if "Shipped Date" in c_base.columns:
        c_base["Shipped Date"] = pd.to_datetime(c_base["Shipped Date"], errors="coerce")

    # COA Status
    if "COA #" in c_base.columns:
        coa_str = c_base["COA #"].astype(str).str.strip()
        c_base["COA_Clean"] = coa_str.replace({"": None, "nan": None, "NaN": None, "None": None})

        valid_mask = c_base["COA_Clean"].notna() & c_base["COA_Clean"].str.match(r"^COA-\d{6}$")
        invalid_mask = c_base["COA_Clean"].notna() & ~valid_mask

        c_base["COA Status"] = "No COA"
        c_base.loc[valid_mask, "COA Status"] = "With COA"
        c_base.loc[invalid_mask, "COA Status"] = "Invalid COA"
    elif "Has COA" in c_base.columns:
        c_base["COA Status"] = np.where(c_base["Has COA"].fillna(False), "With COA", "No COA")
    else:
        c_base["COA Status"] = "No COA"

    # Export permit clean column
    if "Export Permit (PDF link)" in c_base.columns:
        permit_str = c_base["Export Permit (PDF link)"].astype(str).str.strip()
        c_base["Export_Permit_Clean"] = permit_str.replace({"": None, "nan": None, "NaN": None, "None": None})
    else:
        c_base["Export_Permit_Clean"] = None

    # Days_to_Ship
    if "Days to Ship" in c_base.columns:
        c_base["Days_to_Ship"] = pd.to_numeric(c_base["Days to Ship"], errors="coerce")
    elif "Date" in c_base.columns and "Shipped Date" in c_base.columns:
        c_base["Days_to_Ship"] = (c_base["Shipped Date"] - c_base["Date"]).dt.days
    else:
        c_base["Days_to_Ship"] = np.nan

    # ProdGrade helper (still used by hover, and some metrics if you add later)
    pt = c_base["Product Type"].fillna("Unknown Product").astype(str) if "Product Type" in c_base.columns else "Unknown Product"
    gr = c_base["Grade"].fillna("Unknown Grade").astype(str) if "Grade" in c_base.columns else "Unknown Grade"
    c_base["ProdGrade"] = pt + " | " + gr

    # Warn about invalid COA rows
    invalid_count = int((c_base["COA Status"] == "Invalid COA").sum()) if "COA Status" in c_base.columns else 0
    if invalid_count > 0:
        st.warning(f"{invalid_count} rows have **Invalid COA** format and are excluded when COA selector is **All**.")
        with st.expander("Show invalid COA rows (excluded)"):
            show_cols = [c for c in ["Sale ID", "COA #", "Product Type", "Grade", "Price (CAD)", "Country", "Customer Name"] if c in c_base.columns]
            st.dataframe(c_base.loc[c_base["COA Status"] == "Invalid COA", show_cols].head(200), use_container_width=True)

    def _apply_coa_selector(df_in: pd.DataFrame, widget_key: str) -> pd.DataFrame:
        choice = st.selectbox(
            "COA selector",
            ["All", "With COA", "Without COA"],
            index=0,
            key=widget_key,
        )
        df = df_in.copy()
        # "All" excludes invalid
        df = df[df["COA Status"] != "Invalid COA"]

        if choice == "With COA":
            return df[df["COA Status"] == "With COA"]
        if choice == "Without COA":
            return df[df["COA Status"] == "No COA"]
        return df

    def _fmt_money(x):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "—"
        return f"${x:,.0f}"

    def _fmt_num(x):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "—"
        if isinstance(x, (int, np.integer)):
            return f"{int(x):,}"
        return f"{x:,.1f}"

    def _fmt_pct(x):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return "—"
        return f"{x:.1f}%"

    # Expander with sub-tabs + metric tiles
    def render_dir_expander_metrics(title: str, definitions_md: str, metrics: list[dict], recommendations_md: str):
        with st.expander(f"📌 {title}: Definitions / Insights / Recommendations", expanded=False):
            dtab, itab, rtab = st.tabs(["Definitions", "Insights", "Recommendations"])

            with dtab:
                st.markdown(definitions_md)

            with itab:
                if not metrics:
                    st.info("No quick stats available for the current filters.")
                else:
                    cols = st.columns(3)
                    for i, m in enumerate(metrics):
                        with cols[i % 3]:
                            st.metric(
                                label=m.get("label", ""),
                                value=m.get("value", "—"),
                                delta=m.get("delta", None),
                                help=m.get("help", None),
                            )

            with rtab:
                st.markdown(recommendations_md)

    t2, t4, t5, t6, t7 = st.tabs(
        [
            "COA Premium by Grade",
            "COA Adoption by Price Bucket",
            "Shipping Delay Distribution",
            "Compliance Score vs Order Value",
            "COA Coverage by Product Type",
        ]
    )

    # ======================
    # COA Premium by Grade (was Chart 2)
    # ======================
    with t2:
        st.markdown("### COA Price Premium by Grade")
        c_df = _apply_coa_selector(c_base, "coa_sel_premium_grade")

        if c_df.empty or "Grade" not in c_df.columns or "Price (CAD)" not in c_df.columns:
            st.info("No data available under current filters.")
        else:
            price_df = c_df.dropna(subset=["Grade", "Price (CAD)"]).copy()
            agg_price = (
                price_df.groupby(["Grade", "COA Status"], dropna=False)
                .agg(
                    Avg_Price_CAD=("Price (CAD)", "mean"),
                    Sale_Count=(("Sale ID" if "Sale ID" in price_df.columns else "Price (CAD)"), "count"),
                )
                .reset_index()
            )

            if agg_price.empty:
                st.info("No Grade/COA combinations found.")
            else:
                grade_order = sorted(agg_price["Grade"].astype(str).unique().tolist())
                fig2 = px.bar(
                    agg_price,
                    x="Grade",
                    y="Avg_Price_CAD",
                    color="COA Status",
                    barmode="group",
                    category_orders={"Grade": grade_order},
                    hover_data=["Sale_Count"],
                    labels={"Avg_Price_CAD": "Average Price (CAD)"},
                    title="Average Price by Grade and COA Status",
                )
                fig2 = style_fig(fig2, height=520)
                st.plotly_chart(fig2, use_container_width=True, key=pkey("comp_premium_grade"))

        # DIR expander
        total_rows = int(len(c_df))
        coa_rate = float((c_df["COA Status"] == "With COA").mean() * 100) if ("COA Status" in c_df.columns and len(c_df) > 0) else None

        overall_with = None
        overall_without = None
        premium_abs = None
        premium_pct = None
        if "Price (CAD)" in c_df.columns and "COA Status" in c_df.columns:
            with_prices = c_df.dropna(subset=["Price (CAD)"])
            if not with_prices.empty:
                overall_with = float(with_prices.loc[with_prices["COA Status"] == "With COA", "Price (CAD)"].mean())
                overall_without = float(with_prices.loc[with_prices["COA Status"] == "No COA", "Price (CAD)"].mean())
                if np.isfinite(overall_with) and np.isfinite(overall_without):
                    premium_abs = overall_with - overall_without
                    premium_pct = (premium_abs / overall_without * 100) if overall_without != 0 else None

        best_grade = None
        best_premium = None
        if "agg_price" in locals() and not agg_price.empty:
            pv = agg_price.pivot_table(index="Grade", columns="COA Status", values="Avg_Price_CAD", aggfunc="first")
            if "With COA" in pv.columns and "No COA" in pv.columns:
                pv["Premium"] = pv["With COA"] - pv["No COA"]
                if pv["Premium"].notna().any():
                    best_grade = pv["Premium"].idxmax()
                    best_premium = float(pv.loc[best_grade, "Premium"])

        definitions_md = """
**What this chart shows**
- **Bar height** = average sale price (CAD).
- Grouped by **Grade** and split by **COA Status**.
- Use this to estimate a **COA premium** within each grade.
"""
        metrics = [
            {"label": "Rows in view", "value": _fmt_num(total_rows)},
            {"label": "COA rate", "value": _fmt_pct(coa_rate)},
            {"label": "Mean price (With COA)", "value": _fmt_money(overall_with)},
            {"label": "Mean price (No COA)", "value": _fmt_money(overall_without)},
            {"label": "COA premium (mean)", "value": _fmt_money(premium_abs), "delta": _fmt_pct(premium_pct)},
        ]
        if best_grade is not None:
            metrics.append({"label": "Largest premium grade", "value": f"{best_grade} ({_fmt_money(best_premium)})"})

        recs_md = """
**Recommendations**
- If premium is large for a grade, prioritize **COA completion** for that grade’s inventory.
- If premium is near-zero, validate whether the grade already signals quality strongly enough.
- Averages can be skewed—consider adding a **median** version later.
"""
        render_dir_expander_metrics("COA Premium by Grade", definitions_md, metrics, recs_md)

    # ======================
    # COA Adoption by Price Bucket (was Chart 4)
    # ======================
    with t4:
        st.markdown("### COA Adoption by Price Bucket")
        c_df = _apply_coa_selector(c_base, "coa_sel_price_bucket")

        if c_df.empty or "Price (CAD)" not in c_df.columns:
            st.info("No data available under current filters.")
        else:
            price_df = c_df.dropna(subset=["Price (CAD)"]).copy()
            if price_df.empty:
                st.info("No rows with valid prices remain.")
            else:
                def round_up(x: float, step: int) -> int:
                    return int(math.ceil(x / step) * step)

                # Ammolite “customer-intuitive” bins (10 bins)
                edges_base = [0, 250, 500, 1000, 2000, 5000, 10000, 20000, 30000, 50000]
                max_price = float(price_df["Price (CAD)"].max())
                step_for_cap = 1000 if max_price <= 100000 else 5000

                if not np.isfinite(max_price) or max_price <= 0:
                    st.info("Prices are missing or non-positive; cannot build bins.")
                else:
                    cap = round_up(max_price, step_for_cap)
                    if cap <= edges_base[-1]:
                        cap = edges_base[-1] + step_for_cap

                    edges = edges_base + [cap]  # 11 edges => 10 bins

                    price_df["PriceBin"] = pd.cut(
                        price_df["Price (CAD)"],
                        bins=edges,
                        include_lowest=True,
                        right=True
                    )

                    labels = []
                    for i in range(10):
                        low = int(edges[i])
                        high = int(edges[i + 1])
                        start = low if i == 0 else (low + 1)
                        labels.append(f"${start:,.0f} - ${high:,.0f}")

                    bin_categories = price_df["PriceBin"].cat.categories
                    label_map = {bin_categories[i]: labels[i] for i in range(len(bin_categories))}
                    price_df["PriceBinLabel"] = price_df["PriceBin"].map(label_map)

                    price_df["PriceBinLabel"] = pd.Categorical(
                        price_df["PriceBinLabel"],
                        categories=labels,
                        ordered=True
                    )

                    st.caption(f"Using preset bins up to ${cap:,.0f} (max price ${max_price:,.0f}).")

                    grp = (
                        price_df.groupby(["PriceBinLabel", "COA Status"], dropna=False, observed=False)
                        .size()
                        .reset_index(name="Sale_Count")
                    )

                    if grp.empty:
                        st.info("No price bins could be formed.")
                    else:
                        ordered_labels = labels  # keep all bins even if empty

                        pivot = (
                            grp.pivot(index="PriceBinLabel", columns="COA Status", values="Sale_Count")
                            .reindex(ordered_labels)
                            .fillna(0)
                        )

                        with_coa = pivot["With COA"] if "With COA" in pivot.columns else 0
                        no_coa = pivot["No COA"] if "No COA" in pivot.columns else 0

                        pivot["With_COA_Count"] = with_coa
                        pivot["No_COA_Count"] = no_coa
                        pivot["Total_Count"] = pivot["With_COA_Count"] + pivot["No_COA_Count"]
                        pivot["COA_Rate"] = pivot["With_COA_Count"] / pivot["Total_Count"].replace(0, pd.NA)
                        pivot = pivot.reset_index()

                        grp["PriceBinLabel"] = pd.Categorical(grp["PriceBinLabel"], categories=ordered_labels, ordered=True)
                        grp = grp.sort_values("PriceBinLabel")

                        fig4 = go.Figure()
                        for status in sorted(grp["COA Status"].dropna().unique()):
                            d = grp[grp["COA Status"] == status]
                            fig4.add_bar(x=d["PriceBinLabel"].astype(str), y=d["Sale_Count"], name=status)

                        fig4.add_trace(
                            go.Scatter(
                                x=ordered_labels,
                                y=(pivot["COA_Rate"] * 100),
                                name="COA Adoption (%)",
                                mode="lines+markers",
                                yaxis="y2",
                            )
                        )

                        fig4.update_layout(
                            barmode="stack",
                            xaxis=dict(title="Price Bucket (CAD)"),
                            yaxis=dict(title="Number of Sales"),
                            yaxis2=dict(
                                title="COA Adoption (%)",
                                overlaying="y",
                                side="right",
                                range=[0, 100],
                            ),
                            title="COA Adoption and Sales Volume by Price Bucket",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                        )

                        fig4 = style_fig(fig4, height=560)
                        st.plotly_chart(fig4, use_container_width=True, key=pkey("comp_price_bucket"))

        # DIR expander
        total_sales = int(price_df.shape[0]) if "price_df" in locals() else 0
        overall_coa_rate = None
        if "pivot" in locals() and not pivot.empty and "With_COA_Count" in pivot.columns and "Total_Count" in pivot.columns:
            tot_with = float(pivot["With_COA_Count"].sum())
            tot_total = float(pivot["Total_Count"].sum())
            overall_coa_rate = (tot_with / tot_total * 100) if tot_total > 0 else None

        most_volume_bin = None
        most_volume_n = None
        best_bin = None
        best_rate = None
        worst_bin = None
        worst_rate = None
        if "pivot" in locals() and not pivot.empty and "Total_Count" in pivot.columns and "COA_Rate" in pivot.columns:
            pv2 = pivot.copy()
            pv2["COA_Rate_pct"] = pv2["COA_Rate"] * 100
            if pv2["Total_Count"].notna().any():
                idx = pv2["Total_Count"].idxmax()
                most_volume_bin = str(pv2.loc[idx, "PriceBinLabel"])
                most_volume_n = int(pv2.loc[idx, "Total_Count"])
            if pv2["COA_Rate_pct"].notna().any():
                best_idx = pv2["COA_Rate_pct"].idxmax()
                worst_idx = pv2["COA_Rate_pct"].idxmin()
                best_bin = str(pv2.loc[best_idx, "PriceBinLabel"])
                best_rate = float(pv2.loc[best_idx, "COA_Rate_pct"])
                worst_bin = str(pv2.loc[worst_idx, "PriceBinLabel"])
                worst_rate = float(pv2.loc[worst_idx, "COA_Rate_pct"])

        definitions_md = """
**What this chart shows**
- **Stacked bars**: sales count per price bucket split by **COA Status**.
- **Line**: **COA Adoption (%)** = With COA / Total within that bucket.
- Buckets use preset ranges + a dynamic top cap.
"""
        metrics = [
            {"label": "Sales (priced rows)", "value": _fmt_num(total_sales)},
            {"label": "Overall COA adoption", "value": _fmt_pct(overall_coa_rate)},
        ]
        if most_volume_bin is not None:
            metrics.append({"label": "Highest volume bucket", "value": most_volume_bin})
            metrics.append({"label": "Volume in top bucket", "value": _fmt_num(most_volume_n)})
        if best_bin is not None:
            metrics.append({"label": "Best adoption bucket", "value": best_bin, "delta": _fmt_pct(best_rate)})
        if worst_bin is not None:
            metrics.append({"label": "Worst adoption bucket", "value": worst_bin, "delta": _fmt_pct(worst_rate)})

        recs_md = """
**Recommendations**
- If adoption drops at higher prices, enforce “**COA required above $X**”.
- If adoption is low at low prices, consider **batch COA workflows** to reduce overhead.
- Prioritize improvements in the **highest volume bucket** for maximum impact.
"""
        render_dir_expander_metrics("COA Adoption by Price Bucket", definitions_md, metrics, recs_md)

    # ======================
    # Shipping Delay Distribution (was Chart 5)
    # ======================
    with t5:
        st.markdown("### Shipping Delay Distribution by Compliance Group")
        c_df = _apply_coa_selector(c_base, "coa_sel_ship_dist")

        if c_df.empty or "Country" not in c_df.columns:
            st.info("No data available under current filters.")
        else:
            ship_df = c_df.copy()
            ship_df = ship_df.dropna(subset=["Days_to_Ship"])
            ship_df = ship_df[ship_df["Days_to_Ship"] >= 0]

            if ship_df.empty:
                st.info("No valid shipping intervals remain.")
            else:
                non_canada_mask = ship_df["Country"].astype(str).str.lower().ne("canada")
                no_permit_mask = ship_df["Export_Permit_Clean"].isna()
                invalid_export_df = ship_df[non_canada_mask & no_permit_mask]

                excluded_no_permit = int(len(invalid_export_df))
                if excluded_no_permit > 0:
                    st.warning(f"{excluded_no_permit} export rows without permits were excluded from the violin plot.")
                    with st.expander("Show excluded rows (export without permit)"):
                        cols = [c for c in ["Sale ID", "Date", "Shipped Date", "Days_to_Ship", "Product Type", "Grade", "Country", "Customer Name", "Export Permit (PDF link)"] if c in invalid_export_df.columns]
                        st.dataframe(invalid_export_df[cols].head(200), use_container_width=True)

                ship_df_chart = ship_df[~(non_canada_mask & no_permit_mask)].copy()
                if ship_df_chart.empty:
                    st.info("After exclusions, no data remains.")
                else:
                    ship_df_chart["Country_display"] = ship_df_chart["Country"].astype(str)
                    ship_df_chart.loc[ship_df_chart["Country_display"].str.lower().eq("canada"), "Country_display"] = "Canada"

                    is_domestic = ship_df_chart["Country_display"].str.lower().eq("canada")
                    has_coa = ship_df_chart["COA Status"].eq("With COA")
                    has_permit = ship_df_chart["Export_Permit_Clean"].notna() | is_domestic

                    ship_df_chart["Compliance_Group"] = "Domestic - No COA"
                    ship_df_chart.loc[is_domestic & has_coa, "Compliance_Group"] = "Domestic - With COA"
                    ship_df_chart.loc[~is_domestic & has_coa & has_permit, "Compliance_Group"] = "Export - With COA & Permit"
                    ship_df_chart.loc[~is_domestic & ~has_coa & has_permit, "Compliance_Group"] = "Export - No COA & Permit"

                    possible_order = [
                        "Domestic - No COA",
                        "Domestic - With COA",
                        "Export - No COA & Permit",
                        "Export - With COA & Permit",
                    ]
                    present_groups = [g for g in possible_order if g in ship_df_chart["Compliance_Group"].unique()]
                    ship_df_chart["Compliance_Group"] = pd.Categorical(
                        ship_df_chart["Compliance_Group"],
                        categories=present_groups,
                        ordered=True,
                    )

                    fig5 = px.violin(
                        ship_df_chart,
                        x="Compliance_Group",
                        y="Days_to_Ship",
                        color="Compliance_Group",
                        box=True,
                        points="all",
                        title="Shipping Delay Distribution by Compliance Group",
                        labels={"Days_to_Ship": "Days from Sale to Shipment"},
                    )
                    fig5.update_layout(xaxis_tickangle=-20)
                    fig5 = style_fig(fig5, height=560)
                    st.plotly_chart(fig5, use_container_width=True, key=pkey("comp_ship_dist"))

        # DIR expander
        count_rows = int(len(ship_df_chart)) if "ship_df_chart" in locals() else 0
        iqr = None
        fastest_group = None
        fastest_med = None
        slowest_group = None
        slowest_med = None

        if "ship_df_chart" in locals() and not ship_df_chart.empty:
            q25 = float(ship_df_chart["Days_to_Ship"].quantile(0.25))
            q75 = float(ship_df_chart["Days_to_Ship"].quantile(0.75))
            iqr = q75 - q25

            med = ship_df_chart.groupby("Compliance_Group")["Days_to_Ship"].median().sort_values()
            if not med.empty:
                fastest_group = str(med.index[0])
                fastest_med = float(med.iloc[0])
                slowest_group = str(med.index[-1])
                slowest_med = float(med.iloc[-1])

        definitions_md = """
**What this chart shows**
- Distribution of **Days_to_Ship** by **Compliance_Group**.
- “Export without permit” rows are excluded (export groups reflect permit-present records).
- Violin width ≈ density; the **box** shows quartiles.
"""
        metrics = [
            {"label": "Rows used", "value": _fmt_num(count_rows)},
            {"label": "Excluded (no permit)", "value": _fmt_num(excluded_no_permit if "excluded_no_permit" in locals() else None)},
            {"label": "IQR (days)", "value": _fmt_num(iqr)},
        ]
        if fastest_group is not None:
            metrics.append({"label": "Fastest median group", "value": fastest_group, "delta": f"{_fmt_num(fastest_med)}d"})
        if slowest_group is not None:
            metrics.append({"label": "Slowest median group", "value": slowest_group, "delta": f"{_fmt_num(slowest_med)}d"})

        recs_md = """
**Recommendations**
- If export groups have higher median + wider spread, tighten **documentation readiness** and **carrier SLAs**.
- If “Domestic - With COA” is slower than “Domestic - No COA”, COA creation may be gating fulfillment—consider **pre-generating COAs**.
- Target groups with the widest spread for **variance reduction** (standardize steps).
"""
        render_dir_expander_metrics("Shipping Delay Distribution", definitions_md, metrics, recs_md)

    # ======================
    # Compliance Score vs Order Value (was Chart 6)
    # ======================
    with t6:
        st.markdown("### Compliance Score vs Average Order Value (Domestic vs Export)")
        c_df = _apply_coa_selector(c_base, "coa_sel_comp_score")

        if c_df.empty or "Country" not in c_df.columns or "Price (CAD)" not in c_df.columns:
            st.info("No data available under current filters.")
        else:
            comp_df = c_df.dropna(subset=["Price (CAD)"]).copy()

            country_str = comp_df["Country"].astype(str)
            is_domestic = country_str.str.lower().eq("canada")
            comp_df["Market_Type"] = np.where(is_domestic, "Domestic", "Export")

            has_coa = comp_df["COA Status"].eq("With COA")
            has_permit = comp_df["Export_Permit_Clean"].notna()

            comp_df["Compliance_Score"] = 0
            comp_df.loc[is_domestic & has_coa, "Compliance_Score"] = 2

            exp_mask = ~is_domestic
            comp_df.loc[exp_mask & has_coa & has_permit, "Compliance_Score"] = 2
            partial_mask = exp_mask & ((has_coa & ~has_permit) | (~has_coa & has_permit))
            comp_df.loc[partial_mask, "Compliance_Score"] = 1

            score_label_map = {
                0: "0 - No COA / No Permit",
                1: "1 - Partial Compliance",
                2: "2 - Fully Compliant",
            }
            comp_df["Compliance_Score_Label"] = comp_df["Compliance_Score"].map(score_label_map)

            agg_comp = (
                comp_df.groupby(["Market_Type", "Compliance_Score", "Compliance_Score_Label"], dropna=False)
                .agg(
                    Avg_Price_CAD=("Price (CAD)", "mean"),
                    Order_Count=(("Sale ID" if "Sale ID" in comp_df.columns else "Price (CAD)"), "count"),
                )
                .reset_index()
            )

            if agg_comp.empty:
                st.info("No combinations available under current filters.")
            else:
                score_order = [
                    "0 - No COA / No Permit",
                    "1 - Partial Compliance",
                    "2 - Fully Compliant",
                ]
                market_order = ["Domestic", "Export"]

                fig6 = px.bar(
                    agg_comp,
                    x="Compliance_Score_Label",
                    y="Avg_Price_CAD",
                    color="Market_Type",
                    category_orders={"Compliance_Score_Label": score_order, "Market_Type": market_order},
                    barmode="group",
                    hover_data=["Order_Count"],
                    labels={
                        "Compliance_Score_Label": "Compliance Score",
                        "Avg_Price_CAD": "Average Order Value (CAD)",
                        "Market_Type": "Market",
                    },
                    title="Average Order Value by Compliance Score and Market Type",
                )
                fig6 = style_fig(fig6, height=560)
                st.plotly_chart(fig6, use_container_width=True, key=pkey("comp_score_aov"))

        # DIR expander
        rows_used = int(len(comp_df)) if "comp_df" in locals() else 0

        def _get_avg(market, score):
            if "agg_comp" not in locals() or agg_comp.empty:
                return None
            sub = agg_comp[(agg_comp["Market_Type"] == market) & (agg_comp["Compliance_Score"] == score)]
            return float(sub["Avg_Price_CAD"].iloc[0]) if len(sub) else None

        d0, d2 = _get_avg("Domestic", 0), _get_avg("Domestic", 2)
        e0, e2 = _get_avg("Export", 0), _get_avg("Export", 2)

        dom_uplift_abs = (d2 - d0) if (d0 is not None and d2 is not None) else None
        dom_uplift_pct = ((d2 - d0) / d0 * 100) if (d0 is not None and d2 is not None and d0 != 0) else None
        exp_uplift_abs = (e2 - e0) if (e0 is not None and e2 is not None) else None
        exp_uplift_pct = ((e2 - e0) / e0 * 100) if (e0 is not None and e2 is not None and e0 != 0) else None

        best_combo = None
        if "agg_comp" in locals() and not agg_comp.empty:
            idx = agg_comp["Avg_Price_CAD"].idxmax()
            best_combo = (str(agg_comp.loc[idx, "Market_Type"]), int(agg_comp.loc[idx, "Compliance_Score"]), float(agg_comp.loc[idx, "Avg_Price_CAD"]))

        definitions_md = """
**What this chart shows**
- **Compliance_Score** (0/1/2) vs **Average Order Value**, split by **Domestic** and **Export**.
- Score logic:
  - **Domestic**: COA drives compliance.
  - **Export**: COA + Permit = fully compliant; one of them = partial.
"""
        metrics = [
            {"label": "Rows used", "value": _fmt_num(rows_used)},
            {"label": "Domestic: Score2 vs 0", "value": _fmt_money(dom_uplift_abs), "delta": _fmt_pct(dom_uplift_pct)},
            {"label": "Export: Score2 vs 0", "value": _fmt_money(exp_uplift_abs), "delta": _fmt_pct(exp_uplift_pct)},
        ]
        if best_combo is not None:
            metrics.append({"label": "Highest AOV combo", "value": f"{best_combo[0]} (Score {best_combo[1]})", "delta": _fmt_money(best_combo[2])})

        recs_md = """
**Recommendations**
- If Score 2 orders have higher value, treat compliance as a **revenue lever**, not just paperwork.
- For exports, standardize a “**permit + COA checklist**” to move orders from Score 0/1 → 2.
- If Score 1 ≈ Score 2, focus on whichever component (COA vs permit) is cheaper/faster to improve.
"""
        render_dir_expander_metrics("Compliance Score vs Order Value", definitions_md, metrics, recs_md)

    # ======================
    # COA Coverage by Product Type (was Chart 7)
    # ======================
    with t7:
        st.markdown("### COA Coverage by Product Type")
        c_df = _apply_coa_selector(c_base, "coa_sel_coverage_pt")

        if c_df.empty or "Product Type" not in c_df.columns:
            st.info("No data available under current filters.")
        else:
            df7 = c_df.copy()
            df7["Has_Valid_COA"] = df7["COA Status"].eq("With COA")

            agg7 = (
                df7.groupby("Product Type", dropna=False)
                .agg(
                    COA_Rate=("Has_Valid_COA", "mean"),
                    Order_Count=(("Sale ID" if "Sale ID" in df7.columns else "Has_Valid_COA"), "count"),
                )
                .reset_index()
                .sort_values("COA_Rate", ascending=False)
            )

            if agg7.empty:
                st.info("No product types available.")
            else:
                fig7 = px.bar(
                    agg7,
                    x="Product Type",
                    y="COA_Rate",
                    hover_data=["Order_Count"],
                    text_auto=".0%",
                    title="COA Coverage Rate by Product Type",
                    labels={"COA_Rate": "COA Coverage Rate"},
                )
                fig7.update_layout(yaxis_tickformat=".0%")
                fig7 = style_fig(fig7, height=560)
                st.plotly_chart(fig7, use_container_width=True, key=pkey("comp_coverage_pt"))

        # DIR expander
        overall_rate = float(df7["Has_Valid_COA"].mean() * 100) if ("df7" in locals() and not df7.empty and "Has_Valid_COA" in df7.columns) else None
        pt_count = int(df7["Product Type"].nunique()) if ("df7" in locals() and "Product Type" in df7.columns) else None

        top_pt = None
        bottom_pt = None
        if "agg7" in locals() and not agg7.empty:
            top = agg7.iloc[0]
            bot = agg7.iloc[-1]
            top_pt = (str(top["Product Type"]), float(top["COA_Rate"] * 100), int(top["Order_Count"]))
            bottom_pt = (str(bot["Product Type"]), float(bot["COA_Rate"] * 100), int(bot["Order_Count"]))

        definitions_md = """
**What this chart shows**
- **COA coverage rate** by **Product Type**.
- Coverage is based on **valid COA status** (With COA vs No COA).
"""
        metrics = [
            {"label": "Overall coverage", "value": _fmt_pct(overall_rate)},
            {"label": "Product types", "value": _fmt_num(pt_count)},
        ]
        if top_pt is not None:
            metrics.append({"label": "Highest coverage", "value": top_pt[0], "delta": f"{_fmt_pct(top_pt[1])} (n={top_pt[2]:,})"})
        if bottom_pt is not None:
            metrics.append({"label": "Lowest coverage", "value": bottom_pt[0], "delta": f"{_fmt_pct(bottom_pt[1])} (n={bottom_pt[2]:,})"})

        recs_md = """
**Recommendations**
- If a product type has low coverage but high volume, prioritize **COA workflow improvements** there first.
- If low coverage types are niche/low volume, consider “**COA optional under $X**”.
- Track coverage over time to confirm process changes are improving adoption.
"""
        render_dir_expander_metrics("COA Coverage by Product Type", definitions_md, metrics, recs_md)

# ======================
# TAB: Stats (MAIN TAB) — tables + dynamic insights (no chart/visual changes) 
# ======================
if page == 'Stats':
    st.subheader("Stats")

    df = f.copy()

    # ---- metric setup ----
    metric = metric_col
    metric_name = metric_label if "metric_label" in globals() else metric

    if metric not in df.columns:
        st.error(f"Metric column '{metric}' not found in the uploaded file.")
        st.stop()

    # ---- make sure core cols exist ----
    for col in ["Country", "Channel"]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].astype(str).fillna("Unknown")

    # ---- lag column (shipping) ----
    if "Days to Ship" in df.columns:
        lag_col = "Days to Ship"
        df[lag_col] = pd.to_numeric(df[lag_col], errors="coerce")
    elif "Days_to_Ship" in df.columns:
        lag_col = "Days_to_Ship"
        df[lag_col] = pd.to_numeric(df[lag_col], errors="coerce")
    elif ("Date" in df.columns) and ("Shipped Date" in df.columns):
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Shipped Date"] = pd.to_datetime(df["Shipped Date"], errors="coerce")
        df["Days_to_Ship"] = (df["Shipped Date"] - df["Date"]).dt.days
        lag_col = "Days_to_Ship"
    else:
        lag_col = None

    # SciPy (safe)
    try:
        from scipy import stats
    except Exception:
        stats = None

    # ---- helpers (safe) ----
    if "rank_df" not in globals():
        def rank_df(dfin: pd.DataFrame) -> pd.DataFrame:
            out = dfin.reset_index(drop=True).copy()
            out.insert(0, "#", range(1, len(out) + 1))
            return out

    if "pkey" not in globals():
        from itertools import count as _count
        _local_key_counter = _count()
        def pkey(prefix="k"):
            return f"{prefix}_{next(_local_key_counter)}"

    def _p_fmt(v):
        try:
            v = float(v)
        except Exception:
            return "—"
        if not np.isfinite(v):
            return "—"
        if v < 1e-4:
            return "<0.0001"
        return f"{v:.4f}"

    def download_csv(df_out: pd.DataFrame, filename: str, label: str):
        try:
            st.download_button(
                label=label,
                data=df_out.to_csv(index=False).encode("utf-8"),
                file_name=filename,
                mime="text/csv",
                key=pkey("dl_csv"),
            )
        except Exception:
            pass

    def insights_expander(title: str, insights_md: str, why_md: str, recs_md: str):
        with st.expander(f"Insights - {title}", expanded=False):
            st.markdown(f"**Insights:**\n{insights_md if insights_md.strip() else '-'}")
            st.markdown(f"\n**Why it helps:**\n{why_md if why_md.strip() else '-'}")
            st.markdown(f"\n**Recommendations:**\n{recs_md if recs_md.strip() else '-'}")

    # ---- numeric metric column (safe) ----
    df_stat = df.copy()
    df_stat[metric] = pd.to_numeric(df_stat[metric], errors="coerce")

    total_metric = float(df_stat[metric].sum(skipna=True)) if metric in df_stat.columns else 0.0
    channel_totals = df_stat.groupby("Channel")[metric].sum(min_count=1).sort_values(ascending=False)
    country_totals = df_stat.groupby("Country")[metric].sum(min_count=1).sort_values(ascending=False)

    top_channel = str(channel_totals.index[0]) if len(channel_totals) else "—"
    top_country = str(country_totals.index[0]) if len(country_totals) else "—"
    top_channel_share = float(channel_totals.iloc[0] / total_metric) if len(channel_totals) and total_metric > 0 else np.nan
    top_country_share = float(country_totals.iloc[0] / total_metric) if len(country_totals) and total_metric > 0 else np.nan

    # Use a consistent "order count" column if present
    order_col = "Sale ID" if "Sale ID" in df_stat.columns else metric

    # -----------------------------
    # 1) Channel value differences (Kruskal) + TABLE
    # -----------------------------
    st.markdown("### 1) Do channels differ on order value?")

    # Table: channel summary
    ch_base = df_stat.dropna(subset=["Channel"]).copy()
    ch_base[metric] = pd.to_numeric(ch_base[metric], errors="coerce")

    ch_tbl = (
        ch_base.dropna(subset=[metric])
        .groupby("Channel", as_index=False)
        .agg(
            orders=(order_col, "count"),
            total=(metric, "sum"),
            avg=(metric, "mean"),
            median=(metric, "median"),
        )
    )

    if ch_tbl.empty:
        st.info("No channel data available under current filters.")
        p1 = np.nan
    else:
        ch_tbl["share"] = np.where(total_metric > 0, ch_tbl["total"] / total_metric, np.nan)
        ch_tbl = ch_tbl.sort_values("total", ascending=False).copy()

        # Formatting (keep numeric; Streamlit will render)
        ch_tbl["total"] = ch_tbl["total"].round(0)
        ch_tbl["avg"] = ch_tbl["avg"].round(2)
        ch_tbl["median"] = ch_tbl["median"].round(2)
        ch_tbl["share"] = ch_tbl["share"].round(4)

        st.dataframe(
            rank_df(ch_tbl).set_index("#")[["Channel", "orders", "total", "share", "avg", "median"]],
            use_container_width=True,
        )
        download_csv(ch_tbl, "stats_01_channel_summary.csv", "Download table (CSV)")

    # Test: Kruskal
    p1 = np.nan
    H1 = np.nan

    if stats is None:
        st.info("SciPy not available in this environment (stats tests disabled).")
    else:
        clean = df_stat.dropna(subset=["Channel", metric]).copy()
        clean = clean[clean["Channel"].astype(str).str.strip().ne("")]

        grp = clean.groupby("Channel")[metric].apply(lambda x: pd.to_numeric(x, errors="coerce").dropna().values)
        grp = grp[grp.apply(lambda a: len(a) >= 2)]

        if len(grp) >= 2:
            H1, p1 = stats.kruskal(*grp.tolist())
            st.write(
                f"p-value: **{_p_fmt(p1)}** → "
                + ("**Yes**, typical values differ across channels." if p1 < 0.05 else "**No strong evidence** of a difference.")
            )
        else:
            st.write("Not enough data for this test with current filters.")

    insights_md = "\n".join([
        f"- Total ({metric_name}): **{total_metric:,.0f}**",
        f"- Top channel: **{top_channel}**" + (f" (**{top_channel_share*100:.1f}%** share)" if np.isfinite(top_channel_share) else ""),
        f"- Channels in file: **{df_stat['Channel'].nunique()}**",
        f"- Kruskal test p-value: **{_p_fmt(p1)}**" if np.isfinite(p1) else "- Kruskal test p-value: **—** (not available)",
    ])
    why_md = "\n".join([
        "- Confirms whether channel differences are likely real, not random.",
        "- Helps you decide if you need channel-specific strategy."
    ])
    recs_md = "\n".join([
        "- If p < 0.05: treat channels differently (pricing/promo/inventory per channel).",
        "- If p ≥ 0.05: focus more on market mix or operational drivers instead of channel differences.",
        f"- If one channel dominates (like **{top_channel}**), test growth plans for the #2 channel to reduce dependency."
    ])
    insights_expander("Channel Differences", insights_md, why_md, recs_md)
    st.divider()

    # -----------------------------
    # 2) Channel mix different by country? (Chi-square on COUNTS) + TABLE
    # -----------------------------
    st.markdown("### 2) Is channel mix different by country?")

    top_n_countries = st.slider("Top N countries for mix test", 3, 30, 10, key="stats_top_n_mix")

    tmp = df_stat.copy()
    tmp = tmp.dropna(subset=["Country", "Channel"])
    tmp = tmp[tmp["Country"].astype(str).str.strip().ne("")]
    tmp = tmp[tmp["Channel"].astype(str).str.strip().ne("")]

    # restrict to top countries by total metric for stability
    top_for_test = country_totals.head(min(top_n_countries, len(country_totals))).index
    tmp = tmp[tmp["Country"].isin(top_for_test)].copy()

    # Contingency table (counts)
    cont = pd.crosstab(tmp["Country"], tmp["Channel"])

    if cont.empty:
        st.info("Not enough data to build a Country × Channel mix table under current filters.")
        p2 = np.nan
    else:
        # show contingency with totals
        cont_show = cont.copy()
        cont_show["Row Total"] = cont_show.sum(axis=1)
        total_row = cont_show.sum(axis=0).to_frame().T
        total_row.index = ["Column Total"]
        cont_show = pd.concat([cont_show, total_row], axis=0)

        st.dataframe(cont_show, use_container_width=True)
        download_csv(cont.reset_index().rename(columns={"Country": "Country"}), "stats_02_country_channel_counts.csv", "Download counts table (CSV)")

    # Chi-square test
    p2 = np.nan
    chi2 = np.nan

    if stats is None:
        st.info("SciPy not available in this environment (stats tests disabled).")
    else:
        if cont.shape[0] >= 2 and cont.shape[1] >= 2:
            chi2, p2, _, _ = stats.chi2_contingency(cont.values)
            st.write(
                f"p-value: **{_p_fmt(p2)}** → "
                + ("**Yes**, channel mix differs by country." if p2 < 0.05 else "**No strong evidence** of a country-level mix difference.")
            )
        else:
            st.write("Not enough countries/channels for this test under current filters.")

    insights_md = "\n".join([
        f"- Top country: **{top_country}**" + (f" (**{top_country_share*100:.1f}%** share)" if np.isfinite(top_country_share) else ""),
        f"- Countries included: **{tmp['Country'].nunique()}** (top {top_n_countries} by total)",
        f"- Channels included: **{tmp['Channel'].nunique()}**",
        f"- Chi-square test p-value: **{_p_fmt(p2)}**" if np.isfinite(p2) else "- Chi-square test p-value: **—** (not available)",
    ])
    why_md = "\n".join([
        "- If mix differs by country, a single global channel strategy will underperform.",
        "- Helps you pick the best channel focus per market."
    ])
    recs_md = "\n".join([
        "- If p < 0.05: set **country-specific** channel targets (1–2 primary channels per top country).",
        "- If p ≥ 0.05: mix looks consistent → standardize the playbook, then optimize execution.",
        "- Re-run after applying filters (time period / region) to spot where behavior changes."
    ])
    insights_expander("Country × Channel Mix", insights_md, why_md, recs_md)
    st.divider()

    # -----------------------------
    # 3) Shipping lag relationship (Spearman) + TABLES
    # -----------------------------
    st.markdown("### 3) Is shipping lag related to performance?")

    r3 = np.nan
    p3 = np.nan
    neg_lag_rows = 0

    if lag_col is None or lag_col not in df_stat.columns:
        st.write("Shipping lag not available (need Days to Ship or Date + Shipped Date).")
        insights_md = "- Shipping lag: **—** (not available in this file)"
        why_md = "Shipping lag helps diagnose ops issues, but this file doesn’t contain the needed columns."
        recs_md = "\n".join([
            "- Add **Days to Ship** (or **Date** + **Shipped Date**) to enable lag analysis.",
            "- Once included, use lag tables to find hotspots by country/channel."
        ])
        insights_expander("Shipping Lag Relationship", insights_md, why_md, recs_md)
    else:
        neg_lag_rows = int((pd.to_numeric(df_stat[lag_col], errors="coerce") < 0).sum())
        clean_neg = st.toggle("Treat negative lag rows as missing", value=True, key="stats_lag_clean_neg")

        lag_df = df_stat.copy()
        lag_df["Ship Lag (days)"] = pd.to_numeric(lag_df[lag_col], errors="coerce")
        lag_df[metric] = pd.to_numeric(lag_df[metric], errors="coerce")
        lag_df = lag_df.dropna(subset=["Ship Lag (days)"])

        if clean_neg:
            lag_df = lag_df[lag_df["Ship Lag (days)"] >= 0]

        if lag_df.empty:
            st.info("No usable shipping lag values after filters.")
        else:
            # --- TABLE A: Lag by Channel ---
            by_ch = (
                lag_df.groupby("Channel", as_index=False)
                .agg(
                    orders=(order_col, "count"),
                    avg_lag=("Ship Lag (days)", "mean"),
                    med_lag=("Ship Lag (days)", "median"),
                    total_metric=(metric, "sum"),
                )
                .sort_values(["avg_lag", "orders"], ascending=[False, False])
            )
            by_ch["avg_lag"] = by_ch["avg_lag"].round(1)
            by_ch["med_lag"] = by_ch["med_lag"].round(1)
            by_ch["total_metric"] = by_ch["total_metric"].round(0)

            st.markdown("**Shipping lag by Channel**")
            st.dataframe(rank_df(by_ch).set_index("#")[["Channel", "orders", "avg_lag", "med_lag", "total_metric"]], use_container_width=True)
            download_csv(by_ch, "stats_03_lag_by_channel.csv", "Download lag-by-channel (CSV)")

            # --- TABLE B: Lag by Country ---
            by_cty = (
                lag_df.groupby("Country", as_index=False)
                .agg(
                    orders=(order_col, "count"),
                    avg_lag=("Ship Lag (days)", "mean"),
                    med_lag=("Ship Lag (days)", "median"),
                    total_metric=(metric, "sum"),
                )
                .sort_values(["avg_lag", "orders"], ascending=[False, False])
                .head(25)
            )
            by_cty["avg_lag"] = by_cty["avg_lag"].round(1)
            by_cty["med_lag"] = by_cty["med_lag"].round(1)
            by_cty["total_metric"] = by_cty["total_metric"].round(0)

            st.markdown("**Shipping lag by Country (Top 25 by worst avg lag)**")
            st.dataframe(rank_df(by_cty).set_index("#")[["Country", "orders", "avg_lag", "med_lag", "total_metric"]], use_container_width=True)
            download_csv(by_cty, "stats_04_lag_by_country.csv", "Download lag-by-country (CSV)")

            # --- TABLE C: Worst lanes (Country × Channel) ---
            min_orders = st.slider("Minimum orders per Country×Channel (lag table)", 2, 25, 5, key="stats_lane_min_orders")
            lanes = (
                lag_df.groupby(["Country", "Channel"], as_index=False)
                .agg(
                    orders=(order_col, "count"),
                    avg_lag=("Ship Lag (days)", "mean"),
                    med_lag=("Ship Lag (days)", "median"),
                    total_metric=(metric, "sum"),
                )
            )
            lanes = lanes[lanes["orders"] >= min_orders].copy()
            lanes = lanes.sort_values(["avg_lag", "orders"], ascending=[False, False]).head(30)
            lanes["avg_lag"] = lanes["avg_lag"].round(1)
            lanes["med_lag"] = lanes["med_lag"].round(1)
            lanes["total_metric"] = lanes["total_metric"].round(0)

            st.markdown("**Worst shipping lag lanes (Country × Channel)**")
            if lanes.empty:
                st.info("No lanes meet the minimum order threshold under current filters.")
            else:
                st.dataframe(rank_df(lanes).set_index("#")[["Country", "Channel", "orders", "avg_lag", "med_lag", "total_metric"]], use_container_width=True)
                download_csv(lanes, "stats_05_lag_worst_lanes.csv", "Download worst-lanes (CSV)")

            # --- Spearman correlation (Metric vs Lag) ---
            st.markdown("**Correlation (Metric vs Ship Lag)**")
            corr_df = lag_df[[metric, "Ship Lag (days)"]].dropna().copy()
            if len(corr_df) < 10:
                st.write("Not enough data for correlation stats under current filters.")
            else:
                if stats is None:
                    st.info("SciPy not available in this environment (correlation test disabled).")
                else:
                    r3, p3 = stats.spearmanr(corr_df[metric].values, corr_df["Ship Lag (days)"].values)
                    st.write(f"Spearman r: **{r3:.3f}** | p-value: **{_p_fmt(p3)}**")

        insights_md = "\n".join([
            f"- Shipping lag column used: **{lag_col}**",
            f"- Negative lag rows detected: **{neg_lag_rows}**" if neg_lag_rows else "- Negative lag rows detected: **0**",
            f"- Spearman correlation: **r={r3:.3f}**, p=**{_p_fmt(p3)}**" if np.isfinite(r3) else "- Spearman correlation: **—** (not available)",
        ])
        why_md = "\n".join([
            "- Shows which channels/countries/lanes are slowest, so you know exactly where to fix ops first.",
            "- Correlation checks whether lag is actually linked to performance in your data."
        ])
        recs_md = "\n".join([
            "- Fix the worst lag lanes first (high avg lag + meaningful orders).",
            "- Clean negative lag rows so lag KPIs are reliable.",
            "- If correlation is significant (p < 0.05), shipping speed is likely affecting results—prioritize ops improvements."
        ])
        insights_expander("Shipping Lag Relationship", insights_md, why_md, recs_md)

    st.divider()

# -----------------------------
# TAB: All Data
# -----------------------------
if page == 'All Data':
    st.subheader("All Filtered Data")
    st.markdown("Full dataset after applying filters. Download for extra analysis if you need.")

    subset = f.copy()
    subset = subset.loc[:, ~subset.columns.duplicated()]
    st.dataframe(subset.head(max_rows), use_container_width=True)

    st.download_button(
        "Download filtered dataset (CSV)",
        data=subset.to_csv(index=False).encode("utf-8"),
        file_name="ammolite_filtered_full.csv",
        mime="text/csv",
        key="dl_all",
    )
