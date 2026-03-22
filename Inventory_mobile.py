import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import datetime

# 1. Page Configuration - Force Wide but allow responsive wrapping
st.set_page_config(
    page_title="Thai Psychiatric Pharmacy Group", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Mobile Optimization
st.markdown("""
    <style>
    /* Adjust Sidebar width for smaller screens */
    [data-testid="stSidebar"] { min-width: 300px; max-width: 350px; background-color: #111111; }
    [data-testid="stSidebar"] .stCheckbox label p { color: #fdfae5 !important; }
    
    /* Responsive Header Text */
    .main-header { 
        font-size: clamp(1.5rem, 5vw, 2.2rem); 
        font-weight: bold; 
        color: white; 
        line-height: 1.2; 
    }
    .sub-header { font-size: clamp(1rem, 3vw, 1.4rem); color: #fdfae5; }
    .dev-credit { font-size: 0.75rem; color: #888888; font-style: italic; }
    .risk-text { color: #FF4B4B; font-weight: bold; }
    
    /* Reduce padding for mobile */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# 2. Header Section - Optimized for Mobile Stacking
# We use columns that Streamlit will automatically stack on narrow screens
header_col1, header_col2 = st.columns([1, 4])

with header_col1:
    try:
        # use_container_width=True is critical for mobile scaling
        st.image("Logo.jpg", use_container_width=True)
    except:
        st.error("Logo.jpg not found")

with header_col2:
    st.markdown(f"""
        <div class="main-header">Strategic Medicine Stock & Budget Dashboard</div>
        <div class="sub-header">Thai Psychiatric Pharmacy Group</div>
        <div class="dev-credit">Developed by Siriwat Suwattanapreeda</div>
        <div style="font-size: 0.7rem; color: #666;">Refreshed: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
    """, unsafe_allow_html=True)

st.divider()

# 3. Data Connection & Processing
conn = st.connection("gsheets", type=GSheetsConnection)
df_raw = conn.read(ttl=0)

df = df_raw.iloc[:, 2:9].copy()
df.columns = ["Pharmacist_name", "Hospital", "Inventory_Value", "Avg_Usage", "Remaining_Budget", "Announcement", "Port_Status"]

for col in ["Inventory_Value", "Avg_Usage", "Remaining_Budget"]:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df['Months_of_Stock'] = (df['Inventory_Value'] / df['Avg_Usage']).fillna(0).round(2)
df['Total_Support_Months'] = ((df['Remaining_Budget'] + df['Inventory_Value']) / df['Avg_Usage']).fillna(0).round(2)

# 4. Sidebar Navigation
st.sidebar.header("Strategic Navigation")
show_analytics = st.sidebar.checkbox("Show Analytics Charts", value=True)
show_table = st.sidebar.checkbox("Show Detailed Table", value=True)
st.sidebar.divider()
st.sidebar.subheader("Select Institutes")

selected_hospitals = []
for hosp in sorted(df['Hospital'].unique()):
    if st.sidebar.checkbox(hosp, value=True, key=f"filter_{hosp}"):
        selected_hospitals.append(hosp)

df_filtered = df[df['Hospital'].isin(selected_hospitals)]

# 5. Executive Summary Metrics - Automatic stacking on mobile
m1, m2, m3, m4 = st.columns([1,1,1,1])
m1.metric("Total Inventory", f"{df_filtered['Inventory_Value'].sum():,.0f} ฿")
m2.metric("Total Monthly Usage", f"{df_filtered['Avg_Usage'].sum():,.0f} ฿")
m3.metric("Total Budget Available", f"{df_filtered['Remaining_Budget'].sum():,.0f} ฿")
m4.metric("Avg. Monthly Stock", f"{df_filtered['Months_of_Stock'].mean():.2f} Mo")

st.divider()

# 6. Analytics Visualizations
if show_analytics:
    # --- Row 1: Stock & Bubble ---
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        st.subheader("Months of Stock")
        fig_mos = px.bar(df_filtered.sort_values('Months_of_Stock'), x='Months_of_Stock', y='Hospital', 
                         orientation='h', color='Months_of_Stock', range_color=[0, 3], 
                         color_continuous_scale=['#FF4B4B', '#00CC96'])
        fig_mos.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
        st.plotly_chart(fig_mos, use_container_width=True)
        
    with r1c2:
        st.subheader("Inventory vs. Usage")
        fig_bubble = px.scatter(df_filtered, x="Avg_Usage", y="Inventory_Value", size="Months_of_Stock", 
                                color="Hospital", size_max=30)
        # Move legend to bottom for mobile readability
        fig_bubble.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
            margin=dict(l=0, r=0, t=30, b=0),
            height=450
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

    # --- Row 2: Heatmap & Announcement ---
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.subheader("Budget Support Heatmap")
        df_heat = df_filtered.sort_values('Hospital')
        vals = df_heat['Total_Support_Months'].tolist()
        names = df_heat['Hospital'].tolist()
        
        # Simple dynamic grid logic
        cols_count = 3 if len(vals) < 10 else 5
        grid_v = [vals[i:i + cols_count] for i in range(0, len(vals), cols_count)]
        grid_n = [names[i:i + cols_count] for i in range(0, len(names), cols_count)]
        
        fig_heat = go.Figure(data=go.Heatmap(
            z=grid_v, text=[[f"{n}: {v} Mo" for n, v in zip(rn, rv)] for rn, rv in zip(grid_n, grid_v)],
            hoverinfo="text", colorscale=[[0, '#FF4B4B'], [0.8, '#FFFF00'], [1, '#00CC96']], zmin=0, zmax=7
        ))
        fig_heat.update_layout(height=300, xaxis={'showticklabels':False}, yaxis={'showticklabels':False}, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with r2c2:
        st.subheader("Announcement Frequency")
        order = ["ยังไม่มีประกาศ", "ไม่เกิน 1 เดือน", "ไม่เกิน 2 เดือน", "ไม่เกิน 3 เดือน"]
        df_filtered['Announcement'] = pd.Categorical(df_filtered['Announcement'], categories=order, ordered=True)
        ann_counts = df_filtered['Announcement'].value_counts().reindex(order).reset_index()
        fig_ann = px.bar(ann_counts, x='Announcement', y='count', color='Announcement')
        fig_ann.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0), height=350)
        st.plotly_chart(fig_ann, use_container_width=True)

    # --- Row 3: Risk Alert & Port Status ---
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        st.subheader("⚠️ Below 7-Month Target")
        at_risk = df_filtered[df_filtered['Total_Support_Months'] < 7].sort_values('Total_Support_Months')
        if not at_risk.empty:
            for _, row in at_risk.iterrows():
                st.markdown(f"- <span class='risk-text'>{row['Hospital']}</span>: **{row['Total_Support_Months']}** mo", unsafe_allow_html=True)
        else:
            st.success("All clear.")

    with r3c2:
        st.subheader("Port Status")
        df_filtered['Clean_Status'] = df_filtered['Port_Status'].apply(lambda x: "ส่งออกได้แบบมีเงื่อนไข" if "เงื่อนไข" in str(x) else x)
        fig_pie = px.pie(df_filtered, names='Clean_Status', hole=0.4)
        fig_pie.update_traces(textposition='inside', textinfo='percent')
        fig_pie.update_layout(legend=dict(orientation="h", y=-0.2), height=350, margin=dict(t=0, b=50, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

# 8. Row 4: Medicine Dispensation
st.divider()
r4c1, r4c2 = st.columns(2)
with r4c1:
    st.subheader("Top 10 Trade Name")
    st.info("Waiting for database connection...")
with r4c2:
    st.subheader("Top 10 Generic Name")
    st.info("Waiting for database connection...")
    
if show_table:
    st.divider()
    st.subheader("Detailed Data View")
    st.dataframe(df_filtered.drop(columns=['Clean_Status'], errors='ignore'), use_container_width=True, hide_index=True)