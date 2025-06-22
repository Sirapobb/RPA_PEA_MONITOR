import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.set_page_config(
    page_title="Bot Monitoring",
    page_icon="🤖",
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
#sh = gc.open_by_key('--- google sheet key ---')
sh = gc.open_by_key(st.secrets["GOOGLE_SHEETS"]["google_sheet_key"])
notification_sheet = sh.worksheet("Notification")
notification_data = notification_sheet.get_all_records()
df_notification = pd.DataFrame(notification_data)

# Fetch data from "Logdata" sheet
logdata_sheet = sh.worksheet("Logdata")
logdata_data = logdata_sheet.get_all_records()
df_logdata = pd.DataFrame(logdata_data)

def set_reason(row):
    if row['RPA_Delete'] == 'No':
        return 'ไม่เข้าเงื่อนไขที่ Bot ทำงาน ให้ Supervisor ตรวจสอบ'
    elif row['RPA_Delete'] == 'Yes':
        if row['RPA_SendSMS'] == 'No':
            return 'Bot ทำการลบรายการใน e-service แล้ว แต่ยังไม่ได้ดำเนินการในขั้นตอนส่ง SMS และ VOC'
        elif row['RPA_SendSMS'] == 'Yes':
            return 'Bot ทำการลบรายการและส่ง sms เรียบร้อย เหลือขั้นตอน SendVOC ที่ยังไม่ได้ดำเนินการ'
    return ''

def highlight_time(s,start):
    return ['background-color: rgb(234, 226, 73); color: #000000;' if s['RPA_Starttime'] == start else '' for _ in s]

def display_card(title, value):
    html = f"""
    <div style="
        background-color: #f5f5f5;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin-bottom: 10px;
    ">
        <div style="font-size: 16px; font-weight: bold; color: #000;">{title}</div>
        <div style="font-size: 28px; font-weight: bold; color: #a933dc;">{value}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# Display the latest notification
if not df_notification.empty:
    last_record = df_notification.iloc[-1]  # Get the last row of the Notification DataFrame
    notification = last_record.get('Notification', 'No notification available')  # Replace 'Notification' with the actual column name
    startdate = last_record.get('RPA_Startdate')
    starttime = last_record.get('RPA_Starttime')

    total_bot_cases = len(df_logdata[(df_logdata['RPA_Result'] == 'Yes') & (df_logdata['RPA_Startdate'] == startdate)])
    display_card("Today Bot Working Cases", total_bot_cases)
    #display_card("จำนวน Case ที่ Bot ทำงานในวันนี้", total_bot_cases)
    # Display the notification
    st.markdown("------------------------")
    st.markdown("##### 📢 Notification Lastest")
    #st.markdown("##### Notification Lastest")
    #st.markdown(f"```\n{notification}\n```")
    st.code(notification, language='text')
    st.write("------------------------")
    # Filter Logdata for relevant entries
    if not df_logdata.empty:
        # Example: Filter Logdata for rows matching a specific column value
        # Here, we're assuming the "Subject / Description" or another column in Logdata can be matched to the Notification
        relevant_logs = df_logdata[['Ticket No.','RPA_Delete','RPA_SendSMS','RPA_SendVOC',
                                               'RPA_Result','RPA_Startdate','RPA_Starttime']]
        relevant_logs = relevant_logs[(relevant_logs['RPA_Result'] == 'No') & 
                                      (relevant_logs['RPA_Startdate'] == startdate)]
        
        #relevant_logs = relevant_logs[(relevant_logs['RPA_Result'] == 'No') & 
        #                              (relevant_logs['RPA_Startdate'] == '2024-12-13 0:00:00') &
        #                              (relevant_logs['RPA_Starttime'] == '21:39')]
        relevant_logs['Reason'] =  relevant_logs.apply(set_reason, axis=1)
        relevant_logs = relevant_logs[['Ticket No.','RPA_Startdate','RPA_Starttime','Reason','RPA_Delete',
                                       'RPA_SendSMS','RPA_SendVOC','RPA_Result']]
        if not relevant_logs.empty:
            relevant_logs = relevant_logs.reset_index(drop=True)
            relevant_logs = relevant_logs[::-1] 
            styled_logs = relevant_logs.style.apply(highlight_time, axis=1, args=(starttime,))
            #styled_logs = relevant_logs.style.apply(highlight_time, axis=1)
            #st.markdown("### Relevant Logs from Logdata Sheet")
            #st.markdown("##### ⚠️ รายละเอียด Case ที่ Supervisor ต้องตรวจสอบ")
            st.markdown("<h4>⚠️ Case Detail for Supervisor Checking</h4>", unsafe_allow_html=True)
            #st.dataframe(relevant_logs.reset_index(drop=True)) 
            st.dataframe(styled_logs) 
        else:
            st.info("Bot ทำงานสำเร็จทุกเคสในรอบเวลานี้ ไม่มีรายการคงเหลือ")
else:
    st.warning("No data available in the Notification sheet.")
