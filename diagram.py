import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time
import re
import openpyxl

st.set_page_config(page_title="Data Visualization Dashboard", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        z-index: 1000;
        background-color: #00ffff;
        padding: 10px 0 10px 0;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stApp {
        padding-top: 50px;
    }
    </style>
    <div class="fixed-header">
        <h1 style='color:white; text-align:center; font-family:Arial, sans-serif; margin-bottom:0;'>
            <b>📊 Energy Data Visualization Dashboard</b>
        </h1>
    </div>
    """,
    unsafe_allow_html=True
)

@st.cache_data
def load_data(upload_file, sheet_name=None):
    if upload_file is not None:
        file_name = upload_file.name.lower()
        if file_name.endswith('.csv'):
            if sheet_name is None:
                csv = pd.read_csv(upload_file)
                return csv
            else:
                return pd.read_csv(upload_file, sheet_name=sheet_name)
        elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            if sheet_name is not None:
                xls = pd.read_excel(upload_file)
                return xls
            else:
                return pd.read_excel(upload_file, sheet_name=sheet_name)
        else:
            st.error("Unsupported file format. Please upload a CSV or Excel file.")
            return None
    return None
st.sidebar.markdown(
    "<h2 style='color:#b24dff; font-family:Arial, sans-serif; font-weight: bold; text-align: center;'>Data Upload</h2>", unsafe_allow_html=True
)

upload_file = st.sidebar.file_uploader(
    "Upload your data file (Excel or CSV only)",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=False,
    key="file_uploader"
)

# Sidebar navigation for two pages
page = st.sidebar.selectbox(
    "Select Page",
    ["📊 Data Visualization", "📋 Data Preview"],
    key="sidebar_page_select"
)
# Select sheet if Excel file
data = None
sheet_name = None
if upload_file is not None:
    if upload_file.name.lower().endswith(('.xlsx', '.xls', '.csv')):
        sheet_names = load_data(upload_file)
        sheet_name = st.selectbox("Select a sheet", sheet_names)
        data = load_data(upload_file, sheet_name = sheet_name)
    else:
        data = load_data(upload_file)

if data is not None:
    st.session_state.data = data
    with st.spinner("Loading data..."):
        time.sleep(1)  # Simulate loading time
    msg_placeholder = st.empty()
    msg_placeholder.success("Data loaded successfully!")
    time.sleep(3)
    msg_placeholder.empty()
    # Show data only on Data Preview page
if page == "📋 Data Preview":
    st.subheader("Data Preview Table")
    st.dataframe(data)

def select_columns(df, key_prefix=""):
    st.sidebar.markdown(
        "<h2 style='color:#b24dff; font-family:Arial, sans-serif; font-weight: bold; text-align: center;'>Select Columns</h2>", unsafe_allow_html=True
    )
    month_cols = []
    for col in df.columns:
        try:
            dt_col = pd.to_datetime(col)
            month_cols.append(dt_col.strftime('%b-%y'))
        except (ValueError, TypeError):
            month_cols.append(col)
    df.columns = month_cols
    month_pattern = r'^[A-Za-z]{3}-\d{2}$'
    month_cols = df.filter(regex=month_pattern, axis=1).columns.tolist()
    year_cols = [col for col in df.columns if isinstance(col, str) and col.startswith('FY')]
    month_cols.extend(year_cols)
    other_cols = [col for col in df.columns if col not in month_cols]
    source_col = st.sidebar.selectbox("Select Source Column",other_cols , index=other_cols.index('Source') if 'Source' in other_cols else 0, key=f"{key_prefix}_source_col")
    target_col = st.sidebar.selectbox("Select Target Column",other_cols , index=other_cols.index('Target') if 'Target' in other_cols else 1, key=f"{key_prefix}_target_col")
    value_col = st.sidebar.selectbox("Select Value Column", month_cols, index=month_cols.index('FY26') if 'FY26' in month_cols else 2, key=f"{key_prefix}_value_col")
    return source_col, target_col, value_col

def plot_sankey_full(df,value_col='FY26',source_col='Source',target_col='Target', key_prefix="",height=1200):

    source_col, target_col, value_col = select_columns(df, key_prefix=key_prefix)
    nodes = list(set(df[source_col]).union(set(df[target_col])))
    nodes_dict = {node: i for i, node in enumerate(nodes)}

    colors = px.colors.qualitative.Plotly
    node_color = [colors[i % len(colors)] for i in range(len(nodes))]

    node_values = {node: 0 for node in nodes}
    for _, row in df.iterrows():
        node_values[row[source_col]] += row[value_col]/100000
        node_values[row[target_col]] += row[value_col]/100000
    node_values = {node: round(val, 3) for node, val in node_values.items()}
    node_lab = [f"{node}<br>{val} MT" for node, val in zip(nodes, node_values.values())]

    # Create Sankey diagram
    fig = make_subplots(rows=1, cols=1, specs=[[{"type": "sankey"}]])
    fig.add_trace(
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=node_lab,
                color=node_color,
            ),
            link=dict(
                source=df[source_col].map(nodes_dict),
                target=df[target_col].map(nodes_dict),
                value=df[value_col],
                color = node_color
            )
        ),
        row=1, col=1
    )
    fig.update_layout(title_text="Sankey Diagram for Energy", font=dict(size=12, color="black", family="Arial, sans-serif"),height = height, showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    st.plotly_chart(fig, use_container_width=True)

def plant_list(df):
    plants = df['Plant'].unique().tolist()
    plants.sort()
    return plants

def plant_sankey(df,plant):
    plant_df = df[df['Plant'] == plant]
    
    plot_sankey_full(plant_df, key_prefix=f"{plant}_sankey", height=600)

def material_list(df):
    materials = df['Material'].unique().tolist()
    materials.sort()
    return materials

def material_sankey(df,material):
    material_df = df[df['Material'] == material]
    
    plot_sankey_full(material_df, key_prefix=f"{material}_sankey", height=600)


# Data Visualization page with three diagrams
if page == "📊 Data Visualization":
    st.subheader("Sankey Diagram")
    if data is not None:
        # Sankey diagram (full width)
        plot_sankey_full(data)

        # Two charts below in two columns
        col1, col2 = st.columns(2)
        with col1:
            select_plant = st.selectbox("Select Plant for Sankey Diagram", plant_list(data))
            st.subheader(f"Sankey Diagram for {select_plant}")
            plant_sankey(data, select_plant)
        with col2:
            select_material = st.selectbox("Select Material for Sankey Diagram", material_list(data))
            st.subheader(f"Sankey Diagram for {select_material}")
            material_sankey(data, select_material)
    else:
        st.info("Please upload a file to view the diagrams.")
