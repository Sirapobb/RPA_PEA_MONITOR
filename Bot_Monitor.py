import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# ตั้งค่า Streamlit Page
st.set_page_config(
    page_title="Notification Viewer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ใช้ Secrets โดยตรงจาก Streamlit
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]  # ไม่ต้องใช้ json.loads
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
gc = gspread.authorize(credentials)

# เปิด Google Sheet ด้วย Key
sh = gc.open_by_key('1T6tk1QDilil7QTLaTBiHq0yNLdQT3xQhqMQgZAlZCXs')
worksheet = sh.worksheet("Notification")

# ดึงข้อมูลจาก Google Sheets
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# แสดงข้อมูลล่าสุด
if not df.empty:
    last_record = df.iloc[-1]
    notification = last_record.get('Notification', 'No notification available')

    st.markdown("### Latest Notification")
    st.markdown(f"```\n{notification}\n```")
else:
    st.warning("No data available in the Notification sheet.")
