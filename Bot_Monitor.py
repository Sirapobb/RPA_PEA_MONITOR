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
credentials_dict = {
    "type": st.secrets["GOOGLE_SHEETS"]["type"],
    "project_id": st.secrets["GOOGLE_SHEETS"]["project_id"],
    "private_key_id": st.secrets["GOOGLE_SHEETS"]["private_key_id"],
    "private_key": st.secrets["GOOGLE_SHEETS"]["private_key"],
    "client_email": st.secrets["GOOGLE_SHEETS"]["client_email"],
    "client_id": st.secrets["GOOGLE_SHEETS"]["client_id"],
    "auth_uri": st.secrets["GOOGLE_SHEETS"]["auth_uri"],
    "token_uri": st.secrets["GOOGLE_SHEETS"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["GOOGLE_SHEETS"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["GOOGLE_SHEETS"]["client_x509_cert_url"]
}  # ไม่ต้องใช้ json.loads
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
