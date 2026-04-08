import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime

st.set_page_config(page_title="Inventory Export Tool", layout="wide")

# 1. Load Template (Now strictly .xlsx)
@st.cache_data
def load_template():
    # 'engine' parameter ensures we use openpyxl
    return pd.read_excel("index.xlsx", engine='openpyxl')

# 2. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
df_gsheet = conn.read(spreadsheet=url, ttl=0)

st.title("📦 Hospital Inventory Export")

hospitals = sorted(df_gsheet.iloc[:, 15].dropna().unique())
selected_hosp = st.selectbox("Select Hospital for Export", hospitals)

if selected_hosp:
    hosp_row = df_gsheet[df_gsheet.iloc[:, 15] == selected_hosp].iloc[0]

    if st.button(f"Generate CSV for {selected_hosp}"):
        # Load the original .xlsx structure
        template = load_template().copy()

        def process_row(row):
            # Mapping based on your screenshot:
            # Column C (index 2) is the mark for Balance (e.g., 'FG')
            # Column D (index 3) is the mark for Usage (e.g., 'GV')
            gsheet_col_balance = str(row.iloc[2]).strip() if pd.notnull(row.iloc[2]) else ""
            gsheet_col_usage = str(row.iloc[3]).strip() if pd.notnull(row.iloc[3]) else ""

            balance_val = ""
            usage_val = ""
            status = ""
            leadtime = ""

            # Check if marks exist in Google Sheet columns
            is_marked_row = False
            
            if gsheet_col_balance in df_gsheet.columns and gsheet_col_balance != "":
                balance_val = hosp_row[gsheet_col_balance]
                is_marked_row = True
            
            if gsheet_col_usage in df_gsheet.columns and gsheet_col_usage != "":
                usage_val = hosp_row[gsheet_col_usage]
                is_marked_row = True

            # --- Status & Leadtime Logic ---
            try:
                # Convert to number to check if usage is 0
                numeric_usage = float(str(usage_val).replace(',', '')) if usage_val != "" else 0
            except:
                numeric_usage = 0

            if is_marked_row:
                leadtime = 21 # Always 21 for marked rows
                if numeric_usage > 0:
                    status = 1
                else:
                    status = 2
            else:
                # For rows without a mark, keep everything blank
                balance_val = ""
                usage_val = ""
                status = ""
                leadtime = ""

            return pd.Series([balance_val, usage_val, status, leadtime])

        # Overwrite the template columns with calculated data
        template[['current_balance', 'monthly_usage_rate', 'status', 'leadtime']] = template.apply(process_row, axis=1)

        # Convert the modified dataframe to CSV for download
        csv_data = template.to_csv(index=False).encode('utf_8_sig')

        st.success(f"Successfully processed {selected_hosp}")
        st.download_button(
            label="💾 Download CSV",
            data=csv_data,
            file_name=f"Inventory_{selected_hosp}_{datetime.date.today()}.csv",
            mime="text/csv"
        )