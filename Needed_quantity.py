import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
import datetime

# ฟังก์ชันแปลงชื่อคอลัมน์ Excel (เช่น Q, BF, AP) เป็น Index ตัวเลข (0, 1, 2...)
def excel_col_to_num(col_str):
    num = 0
    for char in str(col_str).upper().strip():
        if 'A' <= char <= 'Z':
            num = num * 26 + (ord(char) - ord('A') + 1)
    return num - 1 if num > 0 else -1

st.set_page_config(page_title="Medicine Purchase Planner", layout="wide")

# 1. โหลดข้อมูลจาก index3.xlsx (ต้องมีไฟล์นี้อยู่ในโฟลเดอร์เดียวกับสคริปต์)
@st.cache_data
def load_index():
    # ใช้ engine='openpyxl' เพื่ออ่านไฟล์ .xlsx
    return pd.read_excel("index3.xlsx", engine='openpyxl')

# 2. เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
# อ่านแบบ header=None เพื่อให้ตำแหน่งคอลัมน์ (Index) ตรงกับตัวอักษร Excel เป๊ะๆ
df_gsheet = conn.read(spreadsheet=url, ttl=0, header=None)

st.title("💊 ระบบวางแผนการจัดซื้อยารายรายการ")
st.info("คำนวณจากยอดคงเหลือและอัตราการใช้จริง อ้างอิงตำแหน่งคอลัมน์จาก index3.xlsx")

# ส่วนรับข้อมูล
index_df = load_index()

col1, col2 = st.columns(2)
with col1:
    # 1. Dropdown เลือกยา (เรียงตาม dr_name)
    selected_med_name = st.selectbox(
        "เลือกรายการยา", 
        options=sorted(index_df['dr_name'].unique())
    )

with col2:
    # 2. เลือกวันที่สิ้นสุดการใช้ยา
    target_date = st.date_input("เลือกวันที่ต้องการให้ยามีใช้ถึง", value=date(2026, 9, 30))

# คำนวณจำนวนเดือนที่เหลือจากวันนี้ถึงวันที่เลือก
today = date.today()
days_diff = (target_date - today).days
months_to_use = days_diff / 30.0

if selected_med_name and months_to_use > 0:
    # ดึงตัวอักษรคอลัมน์ (เช่น Q, BF) จากไฟล์ index
    med_info = index_df[index_df['dr_name'] == selected_med_name].iloc[0]
    col_letter_stock = str(med_info['ยอดคงเหลือ']).strip()
    col_letter_usage = str(med_info['ยอดใช้ต่อเดือน']).strip()
    
    # แปลงตัวอักษรเป็นตัวเลข Index
    idx_stock = excel_col_to_num(col_letter_stock)
    idx_usage = excel_col_to_num(col_letter_usage)

    # ดึงรายชื่อโรงพยาบาล (คอลัมน์ P / Index 15) ตั้งแต่แถวที่ 2 เป็นต้นไป
    hosp_aliases = df_gsheet.iloc[1:, 15].values
    
    table_data = []
    for i, alias in enumerate(hosp_aliases):
        row_idx = i + 1 # แถวข้อมูลใน Google Sheet
        
        # ดึงค่าจาก Google Sheet ตาม Index คอลัมน์ที่คำนวณได้
        val_stock = df_gsheet.iloc[row_idx, idx_stock] if idx_stock >= 0 else 0
        val_usage = df_gsheet.iloc[row_idx, idx_usage] if idx_usage >= 0 else 0
        
        # แปลงเป็นตัวเลข (จัดการเครื่องหมายคอมมา)
        try:
            stock = float(str(val_stock).replace(',', '')) if pd.notnull(val_stock) else 0.0
            usage = float(str(val_usage).replace(',', '')) if pd.notnull(val_usage) else 0.0
        except:
            stock, usage = 0.0, 0.0

        # สูตร: [ (เดือนที่เหลือ * ยอดใช้ต่อเดือน) - ยอดคงเหลือ ]
        needed = (months_to_use * usage) - stock
        needed = max(0, needed) # ถ้าคำนวณแล้วติดลบ (ยาพอ) ให้แสดงเป็น 0

        table_data.append({
            "Hospital Name": alias,
            "ยอดใช้ต่อเดือน": usage,
            "ยอดคงเหลือ": stock,
            "ยอดที่ต้องจัดซื้อเพิ่มเติม": round(needed, 2)
        })

    # สร้าง DataFrame สำหรับแสดงผล
    df_result = pd.DataFrame(table_data)

    # คำนวณแถวสรุปผลรวม (TOTAL)
    summary = pd.DataFrame([{
        "Hospital Name": "TOTAL (รวมทุกแห่ง)",
        "ยอดใช้ต่อเดือน": df_result["ยอดใช้ต่อเดือน"].sum(),
        "ยอดคงเหลือ": df_result["ยอดคงเหลือ"].sum(),
        "ยอดที่ต้องจัดซื้อเพิ่มเติม": df_result["ยอดที่ต้องจัดซื้อเพิ่มเติม"].sum()
    }])

    # รวมข้อมูลกับแถวสรุป
    final_display = pd.concat([df_result, summary], ignore_index=True)

    # แสดงผลตาราง
    st.subheader(f"📊 รายงานแผนจัดซื้อ: {selected_med_name}")
    st.caption(f"จำนวนเดือนที่ต้องสำรองยา: {months_to_use:.2f} เดือน | วันที่ปัจจุบัน: {today.strftime('%d/%m/%Y')}")
    
    st.dataframe(
        final_display.style.format({
            "ยอดใช้ต่อเดือน": "{:,.2f}",
            "ยอดคงเหลือ": "{:,.2f}",
            "ยอดที่ต้องจัดซื้อเพิ่มเติม": "{:,.2f}"
        }).apply(lambda x: ['background-color: #1a4d2e; color: white; font-weight: bold' 
                           if x.name == len(final_display)-1 else '' for i in x], axis=1),
        use_container_width=True,
        hide_index=True
    )
elif months_to_use <= 0:
    st.warning("⚠️ กรุณาเลือกวันที่สิ้นสุดการใช้ยาในอนาคต (หลังจากวันนี้)")