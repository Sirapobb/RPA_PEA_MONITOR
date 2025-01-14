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
}
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(st.secrets["GOOGLE_SHEETS"]["google_sheet_key"])

# Fetch data from "Logdata" sheet
logdata_sheet = sh.worksheet("Daily")
logdata_data = logdata_sheet.get_all_records()
df_logdata = pd.DataFrame(logdata_data)

# Ensure 'Created' is a valid datetime column
df_logdata['Created'] = pd.to_datetime(df_logdata['Created'], errors='coerce')
if df_logdata['Created'].isna().any():
    st.error("Some 'Created' column values could not be parsed as datetime.")
else:
    df_logdata['Date'] = df_logdata['Created'].dt.date
    df_logdata['TimeInterval'] = df_logdata['Created'].dt.floor('30T')

# Debugging: Check the DataFrame
st.write("Debug: Data after processing", df_logdata.head())

# Get all unique dates in the dataset
available_dates = df_logdata['Date'].sort_values().unique()

# Default to the latest day in the dataset
default_date = max(available_dates)

# Sidebar input for start and end date selection
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(default_date, default_date),  # Default to the latest day
    min_value=min(available_dates),  # Earliest available date in the dataset
    max_value=max(available_dates)  # Latest available date in the dataset
)

# Filter data based on the selected date range
filtered_data = df_logdata[(df_logdata['Date'] >= start_date) & (df_logdata['Date'] <= end_date)]

# Handle empty DataFrame
if filtered_data.empty:
    st.warning("No data available for the selected date range.")
else:
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

    # Time Series Line Chart: Count of Cases Over Time (all day data)
    time_series_data = df_logdata.groupby('TimeInterval').size().reset_index(name='Count')
    st.write("Debug: Time Series Data", time_series_data.head())

    line_fig = px.line(
        time_series_data,
        x='TimeInterval',
        y='Count',
        labels={'TimeInterval': 'Time Interval', 'Count': 'Number of Cases'},
        title="Time Series: Number of Cases Over Time (All Day)"
    )

    # Update line color to golden yellow
    line_fig.update_traces(mode="lines+markers", line_color="#8902a0")

    # Customize layout
    line_fig.update_layout(
        xaxis_title="Time Interval",
        yaxis_title="Number of Cases"
    )

    # Display the line chart
    st.plotly_chart(line_fig, use_container_width=True)
