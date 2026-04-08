import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime # <--- Added this to fix your error

st.set_page_config(page_title="Inventory Export Tool", layout="wide")

# 1. Load Template (Keep index.xlsx in the same folder as this script)
@st.cache_data
def load_template():
    # Reading the CSV version you uploaded or index.xlsx
    try:
        return pd.read_csv("index.xlsx") 
    except:
        return pd.read_excel("index.xlsx")

# 2. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
df_gsheet = conn.read(spreadsheet=url, ttl=0)

st.title("📦 Hospital Inventory Export")

# 3. Hospital Selection
hospitals = sorted(df_gsheet.iloc[:, 15].dropna().unique())
selected_hosp = st.selectbox("Select Hospital for Export", hospitals)

if selected_hosp:
    # Get the specific row for this hospital from Google Sheets
    hosp_row = df_gsheet[df_gsheet.iloc[:, 15] == selected_hosp].iloc[0]

    if st.button(f"Generate CSV for {selected_hosp}"):
        # Load a fresh copy of the index
        template = load_template().copy()

        # 4. Processing the logic for each row in index.xlsx
        def process_row(row):
            # Check if columns C and D in the template contain GSheet coordinates (e.g., 'FG', 'GV')
            # Using the format from your uploaded index file: column 2 (C) and 3 (D)
            gsheet_col_balance = str(row.iloc[2]).strip() if pd.notnull(row.iloc[2]) else ""
            gsheet_col_usage = str(row.iloc[3]).strip() if pd.notnull(row.iloc[3]) else ""

            # Initialize values
            balance_val = ""
            usage_val = ""
            status = ""
            leadtime = ""

            # If there is a mapping coordinate, fetch the value from GSheet
            if gsheet_col_balance and gsheet_col_balance in df_gsheet.columns:
                balance_val = hosp_row[gsheet_col_balance]
                leadtime = 21 # Set leadtime if this is a "marked" row
            
            if gsheet_col_usage and gsheet_col_usage in df_gsheet.columns:
                usage_val = hosp_row[gsheet_col_usage]

            # --- Status Logic ---
            # 1: Usage is not blank and not 0
            # 2: Marked row but usage is 0/blank
            try:
                numeric_usage = float(str(usage_val).replace(',', '')) if usage_val != "" else 0
            except:
                numeric_usage = 0

            if numeric_usage > 0:
                status = 1
            elif gsheet_col_balance != "": # This row was marked for data
                status = 2

            return pd.Series([balance_val, usage_val, status, leadtime])

        # Apply the logic to update the template columns
        # current_balance, monthly_usage_rate, status, leadtime
        template[['current_balance', 'monthly_usage_rate', 'status', 'leadtime']] = template.apply(process_row, axis=1)

        # 5. Export to CSV (UTF-8-SIG for Thai characters)
        csv_data = template.to_csv(index=False).encode('utf_8_sig')

        st.success(f"Successfully generated data for {selected_hosp}")
        st.download_button(
            label="💾 Download CSV File",
            data=csv_data,
            file_name=f"Inventory_{selected_hosp}_{datetime.date.today()}.csv",
            mime="text/csv"
        )