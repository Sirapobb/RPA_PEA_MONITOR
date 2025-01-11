import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# Set Streamlit page configuration
st.set_page_config(
    page_title="Report",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("### Bot Performance Dashboard")

# Authenticate and connect to Google Sheets
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
#sh = gc.open_by_key('--- google sheet key ---')  # Replace with your Google Sheet key
sh = gc.open_by_key(st.secrets["GOOGLE_SHEETS"]["google_sheet_key"])

# Fetch data from "Logdata" sheet
logdata_sheet = sh.worksheet("Daily")
logdata_data = logdata_sheet.get_all_records()
df_logdata = pd.DataFrame(logdata_data)

# Convert 'Created' to datetime
df_logdata['Created'] = pd.to_datetime(df_logdata['Created'], format='%d/%m/%Y %H:%M:%S')
df_logdata['Date'] = df_logdata['Created'].dt.date
df_logdata['15_Minute_Interval'] = df_logdata['Created'].dt.floor('15T').dt.strftime('%H:%M')

# Generate all 15-minute intervals from midnight to the end of the day
full_intervals = pd.date_range("00:00", "23:59", freq="15T").strftime('%H:%M').tolist()

# Sidebar filter for date selection
start_date = st.sidebar.date_input(
    "Start Date",
    value=df_logdata['Date'].min(),
    min_value=df_logdata['Date'].min(),
    max_value=df_logdata['Date'].max()
)
end_date = st.sidebar.date_input(
    "End Date",
    value=df_logdata['Date'].max(),
    min_value=df_logdata['Date'].min(),
    max_value=df_logdata['Date'].max()
)

if start_date > end_date:
    st.sidebar.error("Start Date must be before or the same as End Date.")

# Filter data for the selected date range
filtered_data = df_logdata[
    (df_logdata['Date'] >= start_date) & (df_logdata['Date'] <= end_date)
]

# Create a DataFrame with all intervals for each date
all_periods = pd.DataFrame(
    [(date, interval) for date in pd.date_range(start_date, end_date).date for interval in full_intervals],
    columns=['Date', '15_Minute_Interval']
)

# Summarize data by 15-minute intervals
interval_grouped = filtered_data.groupby(['Date', '15_Minute_Interval', 'Response']).size().unstack(fill_value=0)
interval_grouped['Total Case'] = interval_grouped.sum(axis=1)
interval_grouped['Bot Working Case'] = interval_grouped.get('Bot', 0)
interval_grouped['Supervisor Working Case'] = interval_grouped.get('Supervisor', 0)
interval_grouped['% Bot Working'] = (
    interval_grouped['Bot Working Case'] / interval_grouped['Total Case'] * 100
).fillna(0).round(2)

# Reset index to make it a clean DataFrame
interval_grouped = interval_grouped.reset_index()

# Merge with all periods to ensure no missing intervals
summary_report = pd.merge(
    all_periods, interval_grouped, 
    on=['Date', '15_Minute_Interval'], 
    how='left'
).fillna(0)

# Display summary report
st.write("### Summary Report")
st.dataframe(summary_report)

# Chart 1: Stacked Bar Chart (Bot vs Supervisor)
st.write("### Stacked Bar Chart: Bot vs Supervisor")
stacked_bar_fig = px.bar(
    summary_report,
    x='15_Minute_Interval',
    y=['Bot Working Case', 'Supervisor Working Case'],
    title="Bot vs Supervisor Working Cases by 15-Minute Interval",
    labels={'value': 'Cases', 'variable': 'Handled By'},
    barmode='stack'
)
st.plotly_chart(stacked_bar_fig, use_container_width=True)

# Chart 2: Line Chart (Total Cases Trend)
st.write("### Line Chart: Total Cases Trend")
line_chart_fig = px.line(
    summary_report,
    x='15_Minute_Interval',
    y='Total Case',
    title="Total Cases Trend by 15-Minute Interval",
    labels={'15_Minute_Interval': 'Time Interval', 'Total Case': 'Number of Cases'}
)
st.plotly_chart(line_chart_fig, use_container_width=True)

# Chart 3: Pie Chart (Bot vs Supervisor Proportion)
st.write("### Pie Chart: Proportion of Bot vs Supervisor")
pie_chart_fig = px.pie(
    summary_report,
    values='Total Case',
    names='15_Minute_Interval',
    title="Proportion of Total Cases Handled by Bot and Supervisor",
    hole=0.4
)
st.plotly_chart(pie_chart_fig, use_container_width=True)

# Chart 4: Heatmap (Density of Cases)
st.write("### Heatmap: Density of Cases")
heatmap_fig = px.density_heatmap(
    summary_report,
    x='15_Minute_Interval',
    y='Date',
    z='Total Case',
    title="Heatmap of Case Density",
    color_continuous_scale='Viridis'
)
st.plotly_chart(heatmap_fig, use_container_width=True)

# Split report into 1 sheet per day
def create_excel_download(summary_report):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for date, data in summary_report.groupby('Date'):
            data.to_excel(writer, index=False, sheet_name=str(date))
    output.seek(0)
    return output

# Create Excel file
excel_data = create_excel_download(summary_report)

# Add download button for Excel file
st.download_button(
    label="📥 Download Report as Excel (1 Day per Sheet)",
    data=excel_data,
    file_name="Daily_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
