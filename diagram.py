import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import re
import time
import openpyxl
import streamlit.components.v1 as components
import json

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
        padding: 10px 0;
        border-radius: 0 0 10px 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }

    .fixed-header h1 {
        color: black;
        font-family: Arial, sans-serif;
        font-weight: bold;
        margin: 0;
        font-size: clamp(1.2rem, 2vw, 1.8rem);
    }

    .stApp { padding-top: 40px; }

    section[data-testid="stSidebar"] {
        transform: none !important;
        visibility: visible !important;
        width: 18rem !important; /* fixed sidebar width */
        min-width: 250px !important;
        max-width: 18rem !important;
        position: fixed !important;
        left: 0 !important;
        top: 40px !important;
        height: calc(100vh - 40px) !important;
        z-index: 999 !important;
        overflow-y: auto !important;
        background-color: #f0f2f6 !important;
        box-shadow: 2px 0 5px rgba(0,0,0,0.1);
    }

    [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* --------- SHIFT MAIN CONTENT --------- */
    [data-testid="stAppViewContainer"] {
        margin-left: 18rem !important;
        transition: margin-left 0.3s ease-in-out;
        padding right: 1rem !important;
    }

    @media (max-width: 1024px) {
        section[data-testid="stSidebar"] {
            position: fixed !important;
            z-index: 999 !important;
            width: 16rem !important;
        }
        [data-testid="stAppViewContainer"] {
            margin-left: 16rem !important;
        }
    }

    @media (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 14rem !important;
        }
        [data-testid="stAppViewContainer"] {
            margin-left: 14rem !important;
        }
    }

    </style>
    <div class="fixed-header">
        <h1>📊 Energy Data Visualization Dashboard</h1>
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
        data = data.copy()
        data.columns = data.columns.map(str) # this line adds string conversion to all column headers
        st.session_state["data"] = data
        with st.spinner("Loading data..."):
            time.sleep(0.5)
        st.sidebar.success("✅ Data Loaded Successfully!")

# ============================================================
# ✅ Helper Functions
# ============================================================
def detect_month_cols(df):
    """
    Returns:
    1. display_to_real : dict (Apr-25 -> 2025-04-01 00:00:00)
    2. display_cols    : list for selectbox
    """
    display_to_real = {}

    for col in df.columns:
        try:
            dt = pd.to_datetime(col)
            display_name = dt.strftime('%b-%y')
            display_to_real[display_name] = str(col)
        except Exception:
            col_str = str(col)
            if col_str.upper().startswith("FY"):
                display_to_real[col_str] = col_str

    return display_to_real, list(display_to_real.keys())

def select_columns(df):
    st.sidebar.markdown(
        "<h3 style='color:#b24dff;text-align:center;'>Select Columns</h3>",
        unsafe_allow_html=True
    )

    month_map, time_cols = detect_month_cols(df)
    other_cols = [str(c) for c in df.columns if str(c) not in month_map.values()]

    source_col = st.sidebar.selectbox(
        "Source Column", other_cols,
        index=other_cols.index("Source") if "Source" in other_cols else 0
    )

    target_col = st.sidebar.selectbox(
        "Target Column", other_cols,
        index=other_cols.index("Target") if "Target" in other_cols else 1
    )

    display_value_col = st.sidebar.selectbox("Value Column", time_cols)

    # 🔥 REAL COLUMN NAME
    value_col = month_map[display_value_col]

    return source_col, target_col, value_col

def plot_sankey_d3(df, source_col, target_col, value_col, title="Sankey Diagram", height=600):

    df = df.copy()
    df.columns = df.columns.astype(str)
    if value_col not in df.columns:
        st.error(f"Value column '{value_col}' not found in data.")
        return
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
    df = df[df[value_col] > 0].copy()

    df = df[df[source_col] != df[target_col]].copy()

    if df.empty:
        st.warning("⚠️ No data available to plot the Sankey diagram.")
        return

    # --- Build nodes
    nodes = list(set(df[source_col]).union(set(df[target_col])))
    node_index = {n: i for i, n in enumerate(nodes)}

    # ---- calculate node totals
    node_values = {n: 0 for n in nodes}
    for _, row in df.iterrows():
        node_values[row[source_col]] += row[value_col]
        node_values[row[target_col]] += row[value_col]

    # --- Build links
    links = []
    for _, row in df.iterrows():
        links.append({
            "source": node_index[row[source_col]],
            "target": node_index[row[target_col]],
            "value": float(row[value_col])
        })

    sankey_data = {
        "nodes": [{"name": n, "value": round(node_values[n], 3)} for n in nodes],
        "links": links
    }

    sankey_html = f"""
    <html>
    <head>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
        <style>
            body {{ margin:0; }}
            text {{ font-family: Arial; font-size: 12px; }}
            .header{{
                
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background-color: #f0f2f6;
                    padding: 10px;
                    border-radius: 8px;
                
            }}
            .title {{
                margin: 0;
                font-size: 1.2em;
                }}
            .save-btn{{
                padding: 8px 18px;
                cursor: pointer;
                border-radius: 50px;
                background-color: #28a745;
                color: #fff;
                border: none;
                font-size: 0.9em;
                font-weight: bold;
                transition: background-color 0.3s ease;
            }}
            .save-btn:hover{{
                background-color:  #218838;
                transform: translateY(-1px);
            }}
            .save-btn:active{{
                transform: scale(0.95);
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h3 class="title">{title}</h3>
            <button class="save-btn" onclick="downloadSVG()">⬇ Save</button>
        </div>
        <svg width="100%" height="{height}"></svg>

        <script>
            const data = {json.dumps(sankey_data)};

            const svg = d3.select("svg");
            const width = svg.node().getBoundingClientRect().width;
            const height = +svg.attr("height");

            const sankey = d3.sankey()
                .nodeWidth(24)
                .nodePadding(30)
                .extent([[10, 10], [width - 10, height - 10]]);

            /* ✅ COLOR SCALE — MUST BE BEFORE USE */
            const color = d3.scaleOrdinal(d3.schemeCategory10);

            const graph = sankey(data);
            const nodes = graph.nodes;
            const links = graph.links;

            /* ---------- LINKS ---------- */
            svg.append("g")
                .selectAll("path")
                .data(links)
                .enter()
                .append("path")
                .attr("d", d3.sankeyLinkHorizontal())
                .attr("stroke", function(d) {{ return color(d.source.name); }})
                .attr("stroke-width", function(d) {{ return Math.max(1, d.width); }})
                .attr("fill", "none")
                .attr("opacity", 0.6);

            /* ---------- NODES ---------- */
            const node = svg.append("g")
                .selectAll("g")
                .data(nodes)
                .enter()
                .append("g");

            node.append("rect")
                .attr("x", function(d) {{ return d.x0; }})
                .attr("y", function(d) {{ return d.y0; }})
                .attr("height", function(d) {{ return d.y1 - d.y0; }})
                .attr("width", function(d) {{ return d.x1 - d.x0; }})
                .attr("fill", function(d) {{ return color(d.name); }});

            /* ---------- LABELS ---------- */
            node.append("text")
                .attr("x", function(d) {{ return d.x0 - 6; }})
                .attr("y", function(d) {{ return (d.y0 + d.y1) / 2; }})
                .attr("dy", "0.35em")
                .attr("text-anchor", "end")
                .text(function(d) {{
                    return d.name + " (" + (d.value || 0).toFixed(2) + ")";
                }})
                .filter(function(d) {{ return d.x0 < width / 2; }})
                .attr("x", function(d) {{ return d.x1 + 6; }})
                .attr("text-anchor", "start");

            /* ---------- DOWNLOAD ---------- */
            function downloadSVG() {{
                const serializer = new XMLSerializer();
                const svgStr = serializer.serializeToString(svg.node());

                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;

                const ctx = canvas.getContext("2d");
                const img = new Image();

                img.onload = function() {{
                    ctx.fillStyle = "white";
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0);
                    const a = document.createElement("a");
                    a.download = "{title}.png";
                    a.href = canvas.toDataURL("image/png");
                    a.click();
                }};

                img.src = "data:image/svg+xml;base64," +
                        btoa(unescape(encodeURIComponent(svgStr)));
            }}
        </script>

    </body>
    </html>
    """

    components.html(sankey_html, height = height+100, scrolling=True)

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
        plot_sankey_d3(data, source_col, target_col, value_col, "Overall Sankey Diagram", height=600)

        # ---- Optional Plant & Material Filters
        col1, col2 = st.columns(2)
        with col1:

            if "Plant" in data.columns:
                selected_plant = st.selectbox("Select Plant", sorted(data["Plant"].dropna().unique()))
                plant_df = data[data["Plant"] == selected_plant]
                plot_sankey_d3(plant_df, source_col, target_col, value_col, f"Sankey for Plant: {selected_plant}", height=500)
        with col2:
            if "Material" in data.columns:
                selected_material = st.selectbox("Select Material", sorted(data["Material"].dropna().unique()))
                material_df = data[data["Material"] == selected_material]
                plot_sankey_d3(material_df, source_col, target_col, value_col, f"Sankey for Material: {selected_material}", height=500)
    else:
        st.info("Please upload a file to view Sankey diagrams.")
