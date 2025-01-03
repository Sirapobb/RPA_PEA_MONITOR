import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# Set Streamlit page configuration
st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
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

# Convert 'Created' to datetime and extract date
df_logdata['Created'] = pd.to_datetime(df_logdata['Created'], format='%d/%m/%Y %H:%M:%S')
df_logdata['Date'] = df_logdata['Created'].dt.date

# Get all unique dates in the dataset
available_dates = df_logdata['Date'].sort_values().unique()

# Default date: today - 1 day
default_date = (datetime.now() - timedelta(days=1)).date()
# default_date = (datetime.now()).date()
# Sidebar multi-select filter for date selection
selected_dates = st.sidebar.multiselect(
    "Select Dates",
    options=['All Dates'] + list(available_dates),  # Include 'All Dates' option
    default=[default_date] if default_date in available_dates else ['All Dates']
)
# Filter data based on the selected dates
if 'All Dates' in selected_dates:
    filtered_data = df_logdata
else:
    filtered_data = df_logdata[df_logdata['Date'].isin(selected_dates)]

# Calculate totals
total_all_cases = len(filtered_data)
total_success_cases = len(filtered_data[filtered_data['Response'] == 'Bot'])
total_not_success_cases = total_all_cases - total_success_cases

# Function to display a card
def display_card(title, value):
    html = f"""
    <div style="
        background-color: #F0F2F6;
        border-radius: 10px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        padding: 15px;
        text-align: center;
        margin: 10px;
    ">
        <p style='font-size: 20px; font-weight: bold; color: #000000; margin: 0;'>{title}</p>
        <p style='font-size: 30px; font-weight: bold; margin: 0; color: #a933dc;'>{value}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# Layout for Cards
col1, col2, col3 = st.columns(3)

with col1:
    display_card("Total Cases", total_all_cases)

with col2:
    display_card("Bot Working Cases", total_success_cases)

with col3:
    display_card("Supervisor Working Cases", total_not_success_cases)

filtered_data['TimeInterval'] = filtered_data['Created'].dt.floor('30T')
# Group by 'TimeInterval' and 'Response' to count cases for stacked bar chart
interval_data = filtered_data.groupby(['TimeInterval', 'Response']).size().reset_index(name='Count')

# Stacked Bar Chart
bar_fig = px.bar(
    interval_data,
    x='TimeInterval',
    y='Count',
    color='Response',
    barmode='stack',
    labels={'TimeInterval': 'Time Interval', 'Count': 'Case Count', 'Response': 'Handled By'},
    title="Case Distribution by 30-Minute Intervals",
    color_discrete_map={
        "Bot": "#a933dc",          # Purple for Bot
        "Supervisor": "#eed3ff"    # Light purple for Supervisor
    }
)

# Add tooltips and interactivity for stacked bar chart
bar_fig.update_traces(hoverinfo="all", hovertemplate="<b>Time Interval:</b> %{x}<br><b>Handled By:</b> %{customdata[0]}<br><b>Case Count:</b> %{y}")
bar_fig.update_layout(xaxis_title="Time Interval", yaxis_title="Count", legend_title="Handled By")

# Display the stacked bar chart
st.plotly_chart(bar_fig, use_container_width=True)

# Create a '30-minute' interval column
df_logdata['TimeInterval'] = df_logdata['Created'].dt.floor('30T')

# Time Series Line Chart: Count of Cases Over Time
time_series_data = df_logdata.groupby('TimeInterval').size().reset_index(name='Count')
line_fig = px.line(
    time_series_data,
    x='TimeInterval',
    y='Count',
    labels={'TimeInterval': 'Time Interval', 'Count': 'Number of Cases'},
    title="Time Series: Number of Cases Over Time"
)

# Update line color to golden yellow
line_fig.update_traces(mode="lines+markers", line_color="#8902a0")

# Customize layout
line_fig.update_layout(
    xaxis_title="Time Interval",
    yaxis_title="Number of Cases"
    #title_font=dict(size=20),  # Optional: Adjust title font size
)

# Display the line chart
st.plotly_chart(line_fig, use_container_width=True)
