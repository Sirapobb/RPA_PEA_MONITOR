import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
from datetime import datetime, timedelta

# --- Simple login ---
st.sidebar.title("🔐 Login")
USERNAME = "admin"
PASSWORD = "1234"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    username_input = st.sidebar.text_input("Username")
    password_input = st.sidebar.text_input("Password", type="password")
    login_btn = st.sidebar.button("Login")

    if login_btn:
        if username_input == USERNAME and password_input == PASSWORD:
            st.session_state.logged_in = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")
    st.stop()

# Set Streamlit page configuration
st.set_page_config(
    page_title="Bot Performance Report",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("### Bot Performance Report")

# Authenticate and connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = {
    "type": st.secrets["GOOGLE_SHEETS"]["type"],
    "project_id": st.secrets["GOOGLE_SHEETS"]["project_id"],
    "private_key_id": st.secrets["GOOGLE_SHEETS"]["private_key_id"],
    "private_key": st.secrets["GOOGLE_SHEETS"]["private_key"].replace("\\n", "\n"),
    "client_email": st.secrets["GOOGLE_SHEETS"]["client_email"],
    "client_id": st.secrets["GOOGLE_SHEETS"]["client_id"],
    "auth_uri": st.secrets["GOOGLE_SHEETS"]["auth_uri"],
    "token_uri": st.secrets["GOOGLE_SHEETS"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["GOOGLE_SHEETS"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["GOOGLE_SHEETS"]["client_x509_cert_url"]
}
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
gc = gspread.authorize(credentials)

# Open the Google Sheet
sh = gc.open_by_key(st.secrets["GOOGLE_SHEETS"]["google_sheet_key"])
logdata_sheet = sh.worksheet("Daily")
logdata_data = logdata_sheet.get_all_records()
df_logdata = pd.DataFrame(logdata_data)

# Process data
df_logdata['Created'] = pd.to_datetime(df_logdata['Created'], format='%d/%m/%Y %H:%M:%S')
df_logdata['Date'] = df_logdata['Created'].dt.date
df_logdata['15 Minute Interval'] = df_logdata['Created'].dt.floor('15T').dt.strftime('%H:%M')

# Generate all 15-minute intervals
full_intervals = pd.date_range("00:00", "23:59", freq="15T").strftime('%H:%M').tolist()

# Sidebar filter for date selection
start_date = st.sidebar.date_input(
    "Start Date",
    value=df_logdata['Date'].max() - timedelta(days=10),
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

# Create list of dates in the selected range
selected_date_range = pd.date_range(start=start_date, end=end_date).date

# Sidebar input to exclude specific dates
exclude_dates = st.sidebar.multiselect(
    "Exclude Specific Dates",
    options=selected_date_range,
    format_func=lambda x: x.strftime("%A %d-%b-%Y"),
    default=[]
)

# Sidebar input to exclude weekdays (0=Mon, ..., 6=Sun)
exclude_days = st.sidebar.multiselect(
    "Exclude Weekdays",
    options=list(range(7)),
    format_func=lambda x: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][x],
    default=[]
)

# Add weekday column to filter by weekday
df_logdata['Weekday'] = pd.to_datetime(df_logdata['Date']).dt.weekday

# Filter data based on all conditions
filtered_data = df_logdata[
    (df_logdata['Date'] >= start_date) &
    (df_logdata['Date'] <= end_date)
]

if exclude_dates:
    filtered_data = filtered_data[~filtered_data['Date'].isin(exclude_dates)]
if exclude_days:
    filtered_data = filtered_data[~filtered_data['Weekday'].isin(exclude_days)]

# Summarize data by 15-minute intervals
interval_grouped = filtered_data.groupby(['Date', '15 Minute Interval', 'Response']).size().unstack(fill_value=0)
interval_grouped['Total Case'] = interval_grouped.sum(axis=1)
interval_grouped['Bot Working Case'] = interval_grouped.get('Bot', 0)
interval_grouped['Supervisor Working Case'] = interval_grouped.get('Supervisor', 0)
interval_grouped['% Bot Working'] = (
    interval_grouped['Bot Working Case'] / interval_grouped['Total Case'] * 100
).fillna(0).apply(lambda x: f"{x:.2f}")

interval_grouped = interval_grouped.reset_index()

# Merge with all periods to ensure no missing intervals
all_periods = pd.DataFrame(
    [(date, interval) for date in pd.date_range(start_date, end_date).date for interval in full_intervals],
    columns=['Date', '15 Minute Interval']
)
summary_report = pd.merge(
    all_periods, interval_grouped,
    on=['Date', '15 Minute Interval'],
    how='left'
).fillna(0)

# Function to create Excel download
def create_excel_download(summary_report):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        summary_data = summary_report.groupby('Date').agg(
            Total_Case=('Total Case', 'sum'),
            Bot_Working_Case=('Bot Working Case', 'sum'),
            Supervisor_Working_Case=('Supervisor Working Case', 'sum'),
        ).reset_index()
        summary_data['Date'] = pd.to_datetime(summary_data['Date']).dt.strftime('%d-%b-%y')
        summary_data['% Bot Working'] = summary_data.apply(
            lambda row: f"{(row['Bot_Working_Case'] / row['Total_Case'] * 100):.2f}"
            if row['Total_Case'] > 0 else "0.00", axis=1
        )
        total_row = summary_data.select_dtypes(include=['number']).sum()
        total_row['Date'] = 'Total'
        total_row['% Bot Working'] = f"{(total_row['Bot_Working_Case'] / total_row['Total_Case'] * 100):.2f}" \
            if total_row['Total_Case'] > 0 else "0.00"
        total_row = pd.DataFrame(total_row).T
        summary_with_total = pd.concat([summary_data, total_row], ignore_index=True)
        summary_with_total.to_excel(writer, index=False, sheet_name="Summary")

        workbook = writer.book
        summary_worksheet = writer.sheets["Summary"]

        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#8064A1', 'font_color': 'white', 'border': 1
        })
        cell_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'bg_color': '#E3DFED', 'border': 1
        })
        total_row_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#3B3838', 'font_color': 'white', 'border': 1
        })

        for col_num, column_name in enumerate(summary_with_total.columns):
            col_width = max(len(column_name), 15)
            summary_worksheet.set_column(col_num, col_num, col_width)
            summary_worksheet.write(0, col_num, column_name, header_format)

        for row_num, row_data in enumerate(summary_with_total.values, start=1):
            row_format = total_row_format if row_num == len(summary_with_total) else cell_format
            for col_num, cell_value in enumerate(row_data):
                summary_worksheet.write(row_num, col_num, cell_value, row_format)

        for date, data in summary_report.groupby("Date"):
            data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%d-%b-%y')
            data['% Bot Working'] = data.apply(
                lambda row: f"{(row['Bot Working Case'] / row['Total Case'] * 100):.2f}"
                if row['Total Case'] > 0 else "0.00", axis=1
            )
            total_row = data.select_dtypes(include=['number']).sum()
            total_row['Date'] = 'Total'
            total_row['15 Minute Interval'] = ''
            total_row['% Bot Working'] = f"{(total_row['Bot Working Case'] / total_row['Total Case'] * 100):.2f}" \
                if total_row['Total Case'] > 0 else "0.00"
            total_row = pd.DataFrame(total_row).T
            data_with_total = pd.concat([data, total_row], ignore_index=True)
            sheet_name = pd.to_datetime(date).strftime('%d-%b-%y')
            data_with_total.to_excel(writer, index=False, sheet_name=sheet_name)

            worksheet = writer.sheets[sheet_name]
            for col_num, column_name in enumerate(data_with_total.columns):
                col_width = max(len(column_name), 15)
                worksheet.set_column(col_num, col_num, col_width)
                worksheet.write(0, col_num, column_name, header_format)

            for row_num, row_data in enumerate(data_with_total.values, start=1):
                row_format = total_row_format if row_num == len(data_with_total) else cell_format
                for col_num, cell_value in enumerate(row_data):
                    worksheet.write(row_num, col_num, cell_value, row_format)
    output.seek(0)
    return output

excel_data = create_excel_download(summary_report)
st.download_button(
    label="📅 Download Report Format Excel File",
    data=excel_data,
    file_name="Daily_Report_With_Summary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="You can select start - end date before download"
)

def display_excel_in_streamlit(excel_data):
    excel_data.seek(0)
    excel_sheets = pd.read_excel(excel_data, sheet_name=None)
    for sheet_name, df in excel_sheets.items():
        st.write(sheet_name)
        st.dataframe(df)

st.write("### Generated Excel Data Preview")
display_excel_in_streamlit(excel_data)
