import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Inventory Export Tool", layout="wide")

# 1. Load the Template (index.xlsx)
@st.cache_data
def load_template():
    # Ensure index.xlsx is in your GitHub repo root
    return pd.read_excel("index.xlsx")

# 2. Load Google Sheet Data
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/1ZPIcCKwGu_7LF0Bka63j9s_E78fEM6A5hnzkVW2N9ag/edit#gid=883636641"
df_gsheet = conn.read(spreadsheet=url, ttl=0)

st.title("📦 Hospital Inventory Export")
st.info("Select a hospital to generate a customized inventory CSV based on the Master Index.")

# 3. Sidebar/Dropdown for Hospital Selection
# Using Column P (Alias_hospital_name) for selection
hospitals = sorted(df_gsheet.iloc[:, 15].dropna().unique())
selected_hosp = st.selectbox("Select Hospital", hospitals)

if selected_hosp:
    # Filter Google Sheet for the selected hospital row
    hosp_data = df_gsheet[df_gsheet.iloc[:, 15] == selected_hosp].iloc[0]

    if st.button(f"Generate File for {selected_hosp}"):
        template = load_template().copy()

        # --- LOGIC PROCESSING ---
        
        # We assume your index.xlsx has columns: dr_code, dr_name, current_balance, monthly_usage_rate, status, leadtime
        # And we assume you have a way to map 'dr_code' to specific columns in your Google Sheet.
        
        # Example Mapping: 
        # current_balance = data from specific GSheet column
        # monthly_usage_rate = data from specific GSheet column
        
        # Let's define the function to apply your rules:
        def apply_row_logic(row):
            # Check if this row is one of your 'marked' items (items that exist in GSheet)
            # This depends on how your index.xlsx identifies items. 
            # If current_balance/usage exists in GSheet for this dr_code:
            
            # --- Placeholder for your column mapping logic ---
            # val_balance = get_from_gsheet(row['dr_code'], 'balance')
            # val_usage = get_from_gsheet(row['dr_code'], 'usage')
            
            # 1. Status Logic
            if pd.notnull(row['monthly_usage_rate']) and row['monthly_usage_rate'] != 0:
                status = 1
            elif pd.notnull(row['current_balance']): # If it's a 'marked' row
                status = 2
            else:
                status = "" # Blank for unmarked
                
            # 2. Leadtime Logic
            leadtime = 21 if pd.notnull(row['current_balance']) else ""
            
            return pd.Series([status, leadtime])

        # Apply your logic (This is a simplified example, 
        # you will insert your specific column indices here)
        # template[['status', 'leadtime']] = template.apply(apply_row_logic, axis=1)

        # 4. Convert to CSV
        csv = template.to_csv(index=False).encode('utf_8_sig')

        st.success(f"File prepared for {selected_hosp}!")
        st.download_button(
            label="Download .csv File",
            data=csv,
            file_name=f"Inventory_{selected_hosp}_{datetime.date.today()}.csv",
            mime="text/csv",
        )