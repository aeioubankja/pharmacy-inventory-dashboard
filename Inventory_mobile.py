import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import datetime

# 1. Page Configuration
st.set_page_config(
    page_title="Thai Psychiatric Pharmacy Group", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for alignment and mobile optimization
st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 300px; max-width: 350px; background-color: #111111; }
    .main-header { 
        font-size: clamp(1.3rem, 4vw, 2.0rem); 
        font-weight: bold; 
        color: white; 
        line-height: 1.1; 
        margin-bottom: 2px;
    }
    .sub-header { font-size: clamp(0.9rem, 2.5vw, 1.2rem); color: #fdfae5; line-height: 1.1; }
    .dev-credit { font-size: 0.75rem; color: #888888; font-style: italic; }
    .risk-text { color: #FF4B4B; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. Header Section
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    st.image("Logo.jpg", use_container_width=True)

with header_col2:
    st.markdown(f"""
        <div style="padding-top: 10px;">
            <div class="main-header">Strategic Medicine Stock & Budget Dashboard</div>
            <div class="sub-header">Thai Psychiatric Pharmacy Group</div>
            <div class="dev-credit">Developed by Siriwat Suwattanapreeda</div>
            <div style="font-size: 0.7rem; color: #666;">Refreshed: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# 3. Data Connection (Restored URL to fix Table/Sidebar disappearance)
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
df_raw = conn.read(spreadsheet=url, ttl=0)

df = df_raw.iloc[:, 2:9].copy()
df.columns = ["Pharmacist_name", "Hospital", "Inventory_Value", "Avg_Usage", "Remaining_Budget", "Announcement", "Port_Status"]

for col in ["Inventory_Value", "Avg_Usage", "Remaining_Budget"]:
    # 1. Convert to string to ensure .str methods work
    # 2. Replace ',' with ''
    # 3. Convert to numeric
    df[col] = df[col].astype(str).str.replace(',', '')
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df['Months_of_Stock'] = (df['Inventory_Value'] / df['Avg_Usage']).fillna(0).round(2)
df['Total_Support_Months'] = ((df['Remaining_Budget'] + df['Inventory_Value']) / df['Avg_Usage']).fillna(0).round(2)

# 4. Sidebar Navigation (Restored Options)
st.sidebar.header("Strategic Navigation")
show_analytics = st.sidebar.checkbox("Show Analytics Charts", value=True)
show_table = st.sidebar.checkbox("Show Detailed Table", value=True)
st.sidebar.divider()
st.sidebar.subheader("Select Institutes")

selected_hospitals = []
for hosp in sorted(df['Hospital'].unique()):
    if st.sidebar.checkbox(hosp, value=True, key=f"f_{hosp}"):
        selected_hospitals.append(hosp)

df_filtered = df[df['Hospital'].isin(selected_hospitals)]

# 5. Executive Summary
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Inventory", f"{df_filtered['Inventory_Value'].sum():,.0f} ฿")
m2.metric("Total Monthly Usage", f"{df_filtered['Avg_Usage'].sum():,.0f} ฿")
m3.metric("Total Budget Available", f"{df_filtered['Remaining_Budget'].sum():,.0f} ฿")
m4.metric("Avg. Monthly Stock", f"{df_filtered['Months_of_Stock'].mean():.2f} Mo")

st.divider()

# 6. FIXED CHART LAYOUT
if show_analytics:
    # ROW 1: Months of Stock (L) | Announcement Frequency (R)
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        st.subheader("Months of Stock")
        fig1 = px.bar(df_filtered.sort_values('Months_of_Stock'), x='Months_of_Stock', y='Hospital', 
                         orientation='h', color='Months_of_Stock', range_color=[0, 3], 
                         color_continuous_scale=['#FF4B4B', '#00CC96'])
        fig1.update_layout(dragmode=False, margin=dict(l=0,r=0,t=30,b=0), height=400)
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

    with r1c2:
        st.subheader("Announcement Frequency")
        order = ["ยังไม่มีประกาศ", "ไม่เกิน 1 เดือน", "ไม่เกิน 2 เดือน", "ไม่เกิน 3 เดือน"]
        df_filtered['Announcement'] = pd.Categorical(df_filtered['Announcement'], categories=order, ordered=True)
        ann_counts = df_filtered['Announcement'].value_counts().reindex(order).reset_index()
        fig2 = px.bar(ann_counts, x='Announcement', y='count', color='Announcement')
        fig2.update_layout(dragmode=False, showlegend=False, margin=dict(l=0,r=0,t=30,b=0), height=400)
        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    # ROW 2: Heatmap (L) | Below 7m Target (R)
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.subheader("Budget Support Heatmap")
        df_heat = df_filtered.sort_values('Hospital')
        vals, names = df_heat['Total_Support_Months'].tolist(), df_heat['Hospital'].tolist()
        grid_v = [vals[i:i + 4] for i in range(0, len(vals), 4)]
        grid_n = [names[i:i + 4] for i in range(0, len(names), 4)]
        fig3 = go.Figure(data=go.Heatmap(
            z=grid_v, text=[[f"{n}: {v} Mo" for n, v in zip(rn, rv)] for rn, rv in zip(grid_n, grid_v)],
            hoverinfo="text", colorscale=[[0, '#FF4B4B'], [0.8, '#FFFF00'], [1, '#00CC96']], zmin=0, zmax=7
        ))
        fig3.update_layout(dragmode=False, height=350, xaxis={'showticklabels':False}, yaxis={'showticklabels':False})
        st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
        
    with r2c2:
        st.subheader("⚠️ Below 7-Month Target")
        at_risk = df_filtered[df_filtered['Total_Support_Months'] < 7].sort_values('Total_Support_Months')
        if not at_risk.empty:
            for _, row in at_risk.iterrows():
                st.markdown(f"- <span class='risk-text'>{row['Hospital']}</span>: **{row['Total_Support_Months']}** mo", unsafe_allow_html=True)
        else:
            st.success("All institutes meet target.")

    # ROW 3: Top 10 Trade (L) | Top 10 Generic (R)
    st.divider()
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        st.subheader("Top 10 Trade Name")
        st.info("Awaiting Database Connection...")
    with r3c2:
        st.subheader("Top 10 Generic Name")
        st.info("Awaiting Database Connection...")

    # ROW 4: Port Status (Centered Below Top 10)
    st.markdown("<h3 style='text-align: center;'>Port Status Distribution</h3>", unsafe_allow_html=True)
    _, mid_col, _ = st.columns([1, 2, 1])
    with mid_col:
        df_filtered['Clean_Status'] = df_filtered['Port_Status'].apply(lambda x: "ส่งออกได้แบบมีเงื่อนไข" if "เงื่อนไข" in str(x) else x)
        fig_pie = px.pie(df_filtered, names='Clean_Status', hole=0.4)
        # Fixed centered legend and layout
        fig_pie.update_layout(
            dragmode=False, 
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), 
            height=450,
            margin=dict(t=20, b=100, l=0, r=0)
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

# 7. Restored Data Table
if show_table:
    st.divider()
    st.subheader("Detailed Data View")
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)