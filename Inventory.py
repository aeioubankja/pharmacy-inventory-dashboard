import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import datetime

# 1. Page Configuration
st.set_page_config(page_title="Thai Psychiatric Pharmacy Group", layout="wide")

# Custom CSS for Sidebar, Headers, and Risk Alerts
st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 380px; max-width: 380px; background-color: #111111; }
    [data-testid="stSidebar"] .stCheckbox label p { color: #fdfae5 !important; white-space: nowrap; }
    .main-header { font-size: 2.2rem; font-weight: bold; color: white; line-height: 1.1; }
    .sub-header { font-size: 1.4rem; color: #fdfae5; margin-top: 5px; }
    .dev-credit { font-size: 0.85rem; color: #888888; font-style: italic; }
    .risk-text { color: #FF4B4B; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. Header Section with Local Logo
# Uses logo.jpg from your local directory
# Column 1: Logo | Column 2: Main Title | Column 3: Group & Dev Credit
header_col1, header_col2, header_col3 = st.columns([0.6, 2.5, 2.2])

with header_col1:
    try:
        st.image("logo.jpg", width=90)
    except:
        st.error("logo.jpg not found")

with header_col2:
    st.markdown("""
        <div style="padding-top: 20px;">
            <div class="main-header">Strategic Medicine Stock & Budget Dashboard</div>
        </div>
    """, unsafe_allow_html=True)

with header_col3:
    st.markdown(f"""
        <div style="text-align: right; padding-top: 10px;">
            <div class="sub-header" style="margin-bottom: 0px; font-weight: bold;">Thai Psychiatric Pharmacy Group</div>
            <div class="dev-credit" style="margin-top: 2px;">developed dashboard by Siriwat Suwattanapreeda</div>
            <div style="font-size: 0.75rem; color: #555; margin-top: 2px;">
                Refreshed: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
            </div>
        </div>
    """, unsafe_allow_html=True)

st.markdown('<hr style="border: 0; border-top: 1px solid #444; margin-bottom: 30px;">', unsafe_allow_html=True)

# 3. Data Connection & Processing
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
df_raw = conn.read(spreadsheet=url, ttl=0)

# Map columns from the Google Sheet
df = df_raw.iloc[:, 2:9].copy()
df.columns = ["Pharmacist_name", "Hospital", "Inventory_Value", "Avg_Usage", "Remaining_Budget", "Announcement", "Port_Status"]

# Convert to numeric values for calculation
for col in ["Inventory_Value", "Avg_Usage", "Remaining_Budget"]:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Dashboard Logic: KPI Calculations
df['Months_of_Stock'] = (df['Inventory_Value'] / df['Avg_Usage']).fillna(0).round(2)
df['Total_Support_Months'] = ((df['Remaining_Budget'] + df['Inventory_Value']) / df['Avg_Usage']).fillna(0).round(2)

# 4. Sidebar Navigation
st.sidebar.header("Strategic Navigation")
show_analytics = st.sidebar.checkbox("Show Analytics Charts", value=True)
show_table = st.sidebar.checkbox("Show Detailed Table", value=True)
st.sidebar.divider()
st.sidebar.subheader("Select Institutes")

# Dynamic Hospital Filter
selected_hospitals = []
for hosp in sorted(df['Hospital'].unique()):
    if st.sidebar.checkbox(hosp, value=True, key=f"filter_{hosp}"):
        selected_hospitals.append(hosp)

df_filtered = df[df['Hospital'].isin(selected_hospitals)]

# 5. Executive Summary Metrics
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("Total Inventory", f"{df_filtered['Inventory_Value'].sum():,.0f} ฿")
with m2: st.metric("Total Monthly Usage", f"{df_filtered['Avg_Usage'].sum():,.0f} ฿")
with m3: st.metric("Total Budget Available", f"{df_filtered['Remaining_Budget'].sum():,.0f} ฿")
with m4: st.metric("Avg. Monthly Stock", f"{df_filtered['Months_of_Stock'].mean():.2f} Mo")

st.divider()

# 6. Analytics Visualizations
if show_analytics:
    # --- Row 1: Stock & Bubble ---
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        st.subheader("Months of Stock (Current)")
        fig_mos = px.bar(df_filtered.sort_values('Months_of_Stock'), x='Months_of_Stock', y='Hospital', 
                         orientation='h', color='Months_of_Stock', range_color=[0, 3], 
                         color_continuous_scale=['#FF4B4B', '#00CC96'])
        st.plotly_chart(fig_mos, use_container_width=True)
    with r1c2:
        st.subheader("Inventory vs. Usage (Bubble)")
        fig_bubble = px.scatter(df_filtered, x="Avg_Usage", y="Inventory_Value", size="Months_of_Stock", 
                                color="Hospital", size_max=40)
        st.plotly_chart(fig_bubble, use_container_width=True)

    # --- Row 2: Heatmap & Announcement ---
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.subheader("Budget Support Heatmap (Target = 7 Mo)")
        df_heat = df_filtered.sort_values('Hospital')
        vals = df_heat['Total_Support_Months'].tolist()
        names = df_heat['Hospital'].tolist()
        # Create grid for heatmap display
        grid_v = [vals[i:i + 5] for i in range(0, len(vals), 5)]
        grid_n = [names[i:i + 5] for i in range(0, len(names), 5)]
        
        fig_heat = go.Figure(data=go.Heatmap(
            z=grid_v, text=[[f"{n}: {v} Mo" for n, v in zip(rn, rv)] for rn, rv in zip(grid_n, grid_v)],
            hoverinfo="text", colorscale=[[0, '#FF4B4B'], [0.8, '#FFFF00'], [1, '#00CC96']], zmin=0, zmax=7
        ))
        fig_heat.update_layout(height=350, xaxis={'showticklabels':False}, yaxis={'showticklabels':False})
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with r2c2:
        st.subheader("Announcement Frequency")
        order = ["ยังไม่ประกาศ", "ไม่เกิน 1 เดือน", "ไม่เกิน 2 เดือน", "ไม่เกิน 3 เดือน"]
        df_filtered['Announcement'] = pd.Categorical(df_filtered['Announcement'], categories=order, ordered=True)
        ann_counts = df_filtered['Announcement'].value_counts().reindex(order).reset_index()
        fig_ann = px.bar(ann_counts, x='Announcement', y='count', color='Announcement')
        st.plotly_chart(fig_ann, use_container_width=True)

    # --- Row 3: Risk Alert & Port Status ---
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        st.subheader("⚠️ Institutes Below 7-Month Target")
        at_risk = df_filtered[df_filtered['Total_Support_Months'] < 7].sort_values('Total_Support_Months')
        if not at_risk.empty:
            for _, row in at_risk.iterrows():
                st.markdown(f"- <span class='risk-text'>{row['Hospital']}</span>: Support for **{row['Total_Support_Months']}** months", unsafe_allow_html=True)
        else:
            st.success("All selected institutes meet target.")

    with r3c2:
        st.subheader("Port Status Distribution")
        # Simplify labels for clarity in the pie chart
        df_filtered['Clean_Status'] = df_filtered['Port_Status'].apply(lambda x: "ส่งออกได้แบบมีเงื่อนไข" if "เงื่อนไข" in str(x) else x)
        fig_pie = px.pie(df_filtered, names='Clean_Status', hole=0.4)
        fig_pie.update_traces(textposition='inside', textinfo='label+percent')
        fig_pie.update_layout(showlegend=False, height=400, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

# 8. Row 4: Medicine Dispensation (Placeholders)
st.divider()
r4c1, r4c2 = st.columns(2)

with r4c1:
    st.subheader("Top 10 Dispensed Medicine by Value (Trade Name)")
    st.info("Waiting for connected with database from สำนักเทคโนโลยีดิจิตัล กรมสุขภาพจิต")
    # Placeholder for future chart:
    # fig_trade = px.bar(df_trade, x='Value', y='Trade_Name', orientation='h')
    # st.plotly_chart(fig_trade, use_container_width=True)

with r4c2:
    st.subheader("Top 10 Dispensed Medicine by Value (Generic Name)")
    st.info("Waiting for connected with database from สำนักเทคโนโลยีดิจิตัล กรมสุขภาพจิต")
    # Placeholder for future chart:
    # fig_generic = px.bar(df_generic, x='Value', y='Generic_Name', orientation='h')
    # st.plotly_chart(fig_generic, use_container_width=True)
    
# 7. Detailed Data Table
if show_table:
    st.divider()
    st.subheader("Detailed Data View")
    st.dataframe(df_filtered.drop(columns=['Clean_Status'], errors='ignore'), use_container_width=True, hide_index=True)

