import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime

# Helper to convert Excel letters (A, B, C...) to 0-based index
def excel_col_to_num(col_str):
    num = 0
    for char in str(col_str).upper().strip():
        if 'A' <= char <= 'Z':
            num = num * 26 + (ord(char) - ord('A') + 1)
    return num - 1 if num > 0 else -1

st.title("📦 Hospital Inventory Export")

# 1. Load Template
@st.cache_data
def load_template():
    df = pd.read_excel("index.xlsx", engine='openpyxl')
    # Force ensure these columns exist in the dataframe structure
    required_cols = ['current_balance', 'monthly_usage_rate', 'status', 'leadtime']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
    return df

# 2. Connection
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
# We read with header=None first to accurately count columns by letter
df_gsheet = conn.read(spreadsheet=url, ttl=0, header=None)

hospitals = sorted(df_gsheet.iloc[1:, 15].dropna().unique()) # Skip header row for list
selected_hosp = st.selectbox("Select Hospital", hospitals)

if selected_hosp:
    # Find the specific row for the hospital
    hosp_row = df_gsheet[df_gsheet.iloc[:, 15] == selected_hosp].iloc[0]

    if st.button(f"Generate File"):
        template = load_template().copy()

        def process_row(row):
            # Column C (index 2) = Balance Mark, Column D (index 3) = Usage Mark
            mark_bal = str(row.iloc[2]).strip() if pd.notnull(row.iloc[2]) else ""
            mark_use = str(row.iloc[3]).strip() if pd.notnull(row.iloc[3]) else ""

            bal_val = ""
            use_val = ""
            status = ""
            leadtime = ""

            # Mapping Balance
            idx_bal = excel_col_to_num(mark_bal)
            if idx_bal >= 0 and idx_bal < len(hosp_row):
                bal_val = hosp_row.iloc[idx_bal]
            
            # Mapping Usage
            idx_use = excel_col_to_num(mark_use)
            if idx_use >= 0 and idx_use < len(hosp_row):
                use_val = hosp_row.iloc[idx_use]

            # Logic for Status/Leadtime
            if mark_bal != "" or mark_use != "":
                leadtime = 21
                try:
                    num_use = float(str(use_val).replace(',', '')) if use_val not in ["", None] else 0
                    status = 1 if num_use > 0 else 2
                except:
                    status = 2
            
            return pd.Series([bal_val, use_val, status, leadtime])

        # Apply to the correct column names
        template[['current_balance', 'monthly_usage_rate', 'status', 'leadtime']] = template.apply(process_row, axis=1)

        # 3. Clean up: Drop the 'Mark' columns (C and D) so they don't appear in CSV
        # We keep dr_code, dr_name, and the 4 new data columns
        cols_to_keep = ['dr_code', 'dr_name', 'current_balance', 'monthly_usage_rate', 'status', 'leadtime']
        final_df = template[cols_to_keep]

        csv = final_df.to_csv(index=False).encode('utf_8_sig')
        
        st.success("Process Complete")
        st.download_button("Download CSV", csv, f"{selected_hosp}.csv", "text/csv")