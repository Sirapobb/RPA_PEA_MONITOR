import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import json

# Set Streamlit page configuration
st.set_page_config(
    page_title="Notification Viewer",  # Title of the app
    layout="wide",  # Use wide layout
    initial_sidebar_state="expanded"  # Sidebar starts expanded
)

# Authenticate and connect to Google Sheets using Streamlit Secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
gc = gspread.authorize(credentials)

# Open the Google Sheet by key
sh = gc.open_by_key('1T6tk1QDilil7QTLaTBiHq0yNLdQT3xQhqMQgZAlZCXs')  # Replace with your Google Sheet key
worksheet = sh.worksheet("Notification")

# Fetch data from Google Sheets
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# Display the DataFrame for verification
# st.dataframe(df)

# Display the latest notification
if not df.empty:
    last_record = df.iloc[-1]  # Get the last row of the DataFrame
    notification = last_record.get('Notification', 'No notification available')  # Replace 'Notification' with the actual column name

    # Display the notification
    st.markdown("### Latest Notification")
    st.markdown(f"```\n{notification}\n```")
else:
    st.warning("No data available in the Notification sheet.")
