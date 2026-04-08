import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import datetime

# --- ฟังก์ชันช่วยแปลงชื่อคอลัมน์ Excel (เช่น Q, BF) เป็นเลข Index ---
def excel_col_to_num(col_str):
    num = 0
    for char in str(col_str).upper().strip():
        if 'A' <= char <= 'Z':
            num = num * 26 + (ord(char) - ord('A') + 1)
    return num - 1 if num > 0 else -1

# --- ตั้งค่าหน้ากระดาษ ---
st.set_page_config(page_title="Medicine Purchase Planner", layout="wide")

# --- 1. โหลดข้อมูลจาก index3.xlsx ---
@st.cache_data
def load_index():
    # อ่านไฟล์ Excel โดยตรง
    return pd.read_excel("index3.xlsx", engine='openpyxl')

# --- 2. เชื่อมต่อ Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
# อ่านแบบ header=None เพื่อให้ Index คอลัมน์ตรงกับมาตรฐาน Excel (A=0, B=1...)
df_gsheet = conn.read(spreadsheet=url, ttl=0, header=None)

st.title("💊 ระบบวางแผนการจัดซื้อยารายรายการ")
st.markdown("---")

# --- 3. ส่วนรับข้อมูลจากผู้ใช้ ---
index_df = load_index()

col1, col2 = st.columns(2)
with col1:
    selected_med_name = st.selectbox(
        "1. เลือกรายการยา (Medicine)", 
        options=sorted(index_df['dr_name'].unique())
    )

with col2:
    target_date = st.date_input(
        "2. เลือกวันที่ต้องการให้ยามีใช้ถึง", 
        value=date(2026, 9, 30)
    )

# คำนวณจำนวนเดือนคงเหลือ
today = date.today()
days_diff = (target_date - today).days
months_to_use = days_diff / 30.0

if selected_med_name and months_to_use > 0:
    # ดึงข้อมูลตำแหน่งคอลัมน์จากไฟล์ index3.xlsx
    med_info = index_df[index_df['dr_name'] == selected_med_name].iloc[0]
    col_letter_stock = str(med_info['ยอดคงเหลือ']).strip()
    col_letter_usage = str(med_info['ยอดใช้ต่อเดือน']).strip()
    
    idx_stock = excel_col_to_num(col_letter_stock)
    idx_usage = excel_col_to_num(col_letter_usage)

    # ดึงรายชื่อโรงพยาบาลจากคอลัมน์ P (Index 15)
    hosp_aliases = df_gsheet.iloc[1:, 15].values
    
    table_data = []
    for i, alias in enumerate(hosp_aliases):
        row_idx = i + 1 # แถวข้อมูลเริ่มที่ Index 1
        
        # ดึงค่า Stock และ Usage ตามพิกัดคอลัมน์
        raw_stock = df_gsheet.iloc[row_idx, idx_stock] if idx_stock >= 0 else 0
        raw_usage = df_gsheet.iloc[row_idx, idx_usage] if idx_usage >= 0 else 0
        
        try:
            stock = float(str(raw_stock).replace(',', '')) if pd.notnull(raw_stock) else 0.0
            usage = float(str(raw_usage).replace(',', '')) if pd.notnull(raw_usage) else 0.0
        except:
            stock, usage = 0.0, 0.0

        # สูตรคำนวณยอดจัดซื้อเพิ่ม
        needed = (months_to_use * usage) - stock
        needed = max(0, needed)

        table_data.append({
            "Hospital Alias Name": alias,
            "ยอดใช้ต่อเดือน": usage,
            "ยอดคงเหลือ": stock,
            "ยอดที่ต้องจัดซื้อเพิ่มเติม": round(needed, 2)
        })

    # สร้าง DataFrame
    df_result = pd.DataFrame(table_data)

    # สร้างแถวสรุปผลรวม (Total Row)
    summary = pd.DataFrame([{
        "Hospital Alias Name": "TOTAL (รวมทุกแห่ง)",
        "ยอดใช้ต่อเดือน": df_result["ยอดใช้ต่อเดือน"].sum(),
        "ยอดคงเหลือ": df_result["ยอดคงเหลือ"].sum(),
        "ยอดที่ต้องจัดซื้อเพิ่มเติม": df_result["ยอดที่ต้องจัดซื้อเพิ่มเติม"].sum()
    }])

    # รวมตารางหลักกับแถวสรุป
    final_display = pd.concat([df_result, summary], ignore_index=True)

    # --- ส่วนการแสดงผลตารางแบบยาว (วิธีที่ 1) ---
    st.subheader(f"📊 รายงานแผนจัดซื้อ: {selected_med_name}")
    st.write(f"ระยะเวลาที่ต้องรองรับ: **{months_to_use:.2f} เดือน**")

    # คำนวณความสูง: (จำนวนแถวรวมสรุป * 35px) + ส่วนหัว 45px
    dynamic_height = (len(final_display) * 35) + 45

    st.dataframe(
        final_display.style.format({
            "ยอดใช้ต่อเดือน": "{:,.2f}",
            "ยอดคงเหลือ": "{:,.2f}",
            "ยอดที่ต้องจัดซื้อเพิ่มเติม": "{:,.2f}"
        }).apply(lambda x: [
            'background-color: #1a4d2e; color: white; font-weight: bold' 
            if x.name == len(final_display)-1 else '' for i in x
        ], axis=1),
        use_container_width=True,
        hide_index=True,
        height=dynamic_height # กำหนดความสูงให้พอดีกับข้อมูลจริง
    )

    # แสดง Metric สรุปภาพรวม
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("รวมยอดใช้ต่อเดือน", f"{df_result['ยอดใช้ต่อเดือน'].sum():,.2f}")
    m2.metric("รวมยอดคงเหลือ", f"{df_result['ยอดคงเหลือ'].sum():,.2f}")
    m3.metric("รวมยอดต้องซื้อเพิ่ม", f"{df_result['ยอดที่ต้องจัดซื้อเพิ่มเติม'].sum():,.2f}")

elif months_to_use <= 0:
    st.warning("⚠️ กรุณาเลือกวันที่ในอนาคตเพื่อคำนวณยอดจัดซื้อ")