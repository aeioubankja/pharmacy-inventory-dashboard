import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime

st.set_page_config(page_title="Inventory Export Tool", layout="wide")

# Helper function to convert Excel Column Letters (FG, AP) to Index Numbers
def excel_col_to_num(col_str):
    exp = 0
    num = 0
    for char in reversed(col_str.upper()):
        num += (ord(char) - ord('A') + 1) * (26 ** exp)
        exp += 1
    return num - 1

# 1. Load Template
@st.cache_data
def load_template():
    return pd.read_excel("index.xlsx", engine='openpyxl')

# 2. Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
# We read the raw data
df_gsheet = conn.read(spreadsheet=url, ttl=0)

st.title("📦 Hospital Inventory Export")

# 3. Hospital Selection (Column P is index 15)
hospitals = sorted(df_gsheet.iloc[:, 15].dropna().unique())
selected_hosp = st.selectbox("Select Hospital for Export", hospitals)

if selected_hosp:
    # Get the data row for the selected hospital
    hosp_row = df_gsheet[df_gsheet.iloc[:, 15] == selected_hosp].iloc[0]

    if st.button(f"Generate CSV for {selected_hosp}"):
        template = load_template().copy()

        def process_row(row):
            # Column C/D in template contains the LETTERS (e.g., 'FG', 'GV')
            col_letter_balance = str(row.iloc[2]).strip().upper() if pd.notnull(row.iloc[2]) else ""
            col_letter_usage = str(row.iloc[3]).strip().upper() if pd.notnull(row.iloc[3]) else ""

            balance_val = ""
            usage_val = ""
            status = ""
            leadtime = ""

            is_marked = False

            # Convert 'FG' to index and pull data
            if col_letter_balance and col_letter_balance.isalpha():
                idx_bal = excel_col_to_num(col_letter_balance)
                if idx_bal < len(hosp_row):
                    balance_val = hosp_row.iloc[idx_bal]
                    is_marked = True
            
            if col_letter_usage and col_letter_usage.isalpha():
                idx_use = excel_col_to_num(col_letter_usage)
                if idx_use < len(hosp_row):
                    usage_val = hosp_row.iloc[idx_use]
                    is_marked = True

            # --- Logic for Status and Leadtime ---
            if is_marked:
                leadtime = 21
                try:
                    # Clean and check numeric usage
                    val_str = str(usage_val).replace(',', '').strip()
                    numeric_usage = float(val_str) if val_str not in ["", "None", "nan"] else 0
                    status = 1 if numeric_usage > 0 else 2
                except:
                    status = 2
            else:
                # Keep unmarked rows empty
                balance_val = usage_val = status = leadtime = ""

            return pd.Series([balance_val, usage_val, status, leadtime])

        # Fill the new columns
        template[['current_balance', 'monthly_usage_rate', 'status', 'leadtime']] = template.apply(process_row, axis=1)

        # Drop the original 'Mark' columns (Column C & D) so the final CSV is clean
        final_df = template.drop(template.columns[[2, 3]], axis=1)

        csv_data = final_df.to_csv(index=False).encode('utf_8_sig')

        st.success(f"CSV generated for {selected_hosp}")
        st.download_button(
            label="💾 Download CSV",
            data=csv_data,
            file_name=f"Inventory_{selected_hosp}_{datetime.date.today()}.csv",
            mime="text/csv"
        )