import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import re
import time
import openpyxl

# ============================================================
# ✅ Page Configuration
# ============================================================
st.set_page_config(page_title="Energy Data Visualization Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        z-index: 1000;
        background-color: #00ffff;
        padding: 6px 0;
        border-radius: 0 0 10px 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stApp { padding-top: 40px; }
    </style>
    <div class="fixed-header">
        <h1 style='color:black; text-align:center; font-family:Arial, sans-serif; margin-bottom:0;'>
            <b>📊 Energy Data Visualization Dashboard</b>
        </h1>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# ✅ Load File Function (Efficient & Cached)
# ============================================================
@st.cache_data(show_spinner=False)
def load_data(upload_file, sheet_name=None):
    """Loads CSV or Excel sheet efficiently."""
    if upload_file is None:
        return None
    file_name = upload_file.name.lower()
    try:
        if file_name.endswith(".csv"):
            return pd.read_csv(upload_file)
        elif file_name.endswith((".xlsx", ".xls")):
            if sheet_name is None:
                return pd.ExcelFile(upload_file, engine="openpyxl").sheet_names
            else:
                return pd.read_excel(upload_file, sheet_name=sheet_name, engine="openpyxl")
        else:
            st.error("❌ Unsupported file format. Please upload CSV or Excel.")
            return None
    except Exception as e:
        st.error(f"⚠️ Error reading file: {e}")
        return None


# ============================================================
# ✅ Sidebar File Upload
# ============================================================
st.sidebar.markdown(
    "<h2 style='color:#b24dff; text-align:center;'>📁 Upload Data</h2>",
    unsafe_allow_html=True
)

upload_file = st.sidebar.file_uploader("Upload Excel or CSV file", type=["csv", "xlsx", "xls"])

page = st.sidebar.selectbox("Select Page", ["📋 Data Preview", "📊 Data Visualization"])

data = None

# ============================================================
# ✅ File and Sheet Handling
# ============================================================
if upload_file:
    file_name = upload_file.name.lower()
    if file_name.endswith(".csv"):
        data = load_data(upload_file)
    elif file_name.endswith((".xlsx", ".xls")):
        sheet_names = load_data(upload_file)
        if sheet_names:
            selected_sheet = st.sidebar.selectbox("Select Sheet", sheet_names)
            data = load_data(upload_file, sheet_name=selected_sheet)

    if data is not None:
        st.session_state["data"] = data
        with st.spinner("Loading data..."):
            time.sleep(0.5)
        st.sidebar.success("✅ Data Loaded Successfully!")

# ============================================================
# ✅ Helper Functions
# ============================================================
def detect_month_cols(df):
    """Detects month or FY columns."""
    month_cols = []
    for col in df.columns:
        try:
            dt_col = pd.to_datetime(col)
            month_cols.append(dt_col.strftime('%b-%y'))
        except (ValueError, TypeError):
            month_cols.append(col)
    df.columns = month_cols
    month_pattern = r'^[A-Za-z]{3}-\d{2,4}$'
    month_cols = df.filter(regex=month_pattern, axis=1).columns.tolist()
    fy_cols = [c for c in df.columns if isinstance(c, str) and c.upper().startswith("FY")]
    month_cols.extend(fy_cols)
    return month_cols

def select_columns(df):
    """Column selectors shown only once."""
    st.sidebar.markdown("<h3 style='color:#b24dff;text-align:center;'>Select Columns</h3>", unsafe_allow_html=True)
    time_cols = detect_month_cols(df)
    other_cols = [c for c in df.columns if c not in time_cols]

    source_col = st.sidebar.selectbox("Source Column", other_cols, index=other_cols.index("Source") if "Source" in other_cols else 0)
    target_col = st.sidebar.selectbox("Target Column", other_cols, index=other_cols.index("Target") if "Target" in other_cols else 1)
    value_col = st.sidebar.selectbox("Value Column", time_cols, index=0 if len(time_cols) > 0 else None)
    return source_col, target_col, value_col


def plot_sankey(df, source_col, target_col, value_col, unit_col=None, show_unit = False, title = "Sankey Diagram", height=600):
    """Plot single Sankey chart."""
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
    nodes = list(set(df[source_col]).union(df[target_col]))
    mapping = {node: i for i, node in enumerate(nodes)}

    node_colors = [px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i in range(len(nodes))]
    node_values = {node: 0 for node in nodes}
    for _, row in df.iterrows():
        val = row[value_col]
        node_values[row[source_col]] += val
        node_values[row[target_col]] += val

    # Round node values
    node_values = {node: round(val, 3) for node, val in node_values.items()}
    
    # Prepare node labels
    if unit_col and unit_col in df.columns:
        node_labels = [f"{node}<br>{node_values.get(node,0)} {df[unit_col].iloc[0]}" for node in nodes]
    else:
        node_labels = [f"{node}<br>{node_values.get(node,0)}" for node in nodes]

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15, thickness=20,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=node_colors
        ),
        link=dict(
            source=df[source_col].map(mapping),
            target=df[target_col].map(mapping),
            value=df[value_col],
            color = node_colors
        )
    ))
    fig.update_layout(title_text=title, font=dict(size=12, family="Arial"), height=height, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# ✅ Page 1: Data Preview
# ============================================================
if page == "📋 Data Preview":
    st.subheader("📋 Data Preview")
    if data is not None:
        st.dataframe(data.head(500))
    else:
        st.info("Upload a file to preview data.")


# ============================================================
# ✅ Page 2: Data Visualization
# ============================================================
if page == "📊 Data Visualization":
    st.subheader("📊 Sankey Diagram Visualization")
    if data is not None:
        # ---- Column Selection (once only)
        source_col, target_col, value_col = select_columns(data)

        # ---- Main Sankey
        plot_sankey(data, source_col, target_col, value_col, "Overall Sankey Diagram", height=800)

        # ---- Plant & Material Sankey
        col1, col2 = st.columns(2)
        with col1:
            if "Plant" in data.columns:
                selected_plant = st.selectbox("Select Plant", sorted(data["Plant"].dropna().unique()))
                plant_df = data[data["Plant"] == selected_plant]
                plot_sankey(plant_df, source_col, target_col, value_col, f"Sankey for Plant: {selected_plant}", height=500)

        with col2:
            if "Material" in data.columns:
                selected_material = st.selectbox("Select Material", sorted(data["Material"].dropna().unique()))
                material_df = data[data["Material"] == selected_material]
                plot_sankey(material_df, source_col, target_col, value_col, f"Sankey for Material: {selected_material}", height=500)
    else:
        st.info("Please upload a file to view Sankey diagrams.")




