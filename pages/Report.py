import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
from datetime import datetime, timedelta

# Set Streamlit page configuration
st.set_page_config(
    page_title="Bot Performance Dashboard",
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

# Fetch data from "Daily" sheet
logdata_sheet = sh.worksheet("Daily")
logdata_data = logdata_sheet.get_all_records()
df_logdata = pd.DataFrame(logdata_data)

# Process data
df_logdata['Created'] = pd.to_datetime(df_logdata['Created'], format='%d/%m/%Y %H:%M:%S')
df_logdata['Date'] = df_logdata['Created'].dt.date
df_logdata['15_Minute_Interval'] = df_logdata['Created'].dt.floor('15T').dt.strftime('%H:%M')

# Generate all 15-minute intervals
full_intervals = pd.date_range("00:00", "23:59", freq="15T").strftime('%H:%M').tolist()

# Sidebar filter for date selection
start_date = st.sidebar.date_input(
    "Start Date",
    value=df_logdata['Date'].max(),
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

# Summarize data by 15-minute intervals
interval_grouped = filtered_data.groupby(['Date', '15_Minute_Interval', 'Response']).size().unstack(fill_value=0)
interval_grouped['Total Case'] = interval_grouped.sum(axis=1)
interval_grouped['Bot Working Case'] = interval_grouped.get('Bot', 0)
interval_grouped['Supervisor Working Case'] = interval_grouped.get('Supervisor', 0)
interval_grouped['% Bot Working'] = (
    interval_grouped['Bot Working Case'] / interval_grouped['Total Case'] * 100
).fillna(0).round(2)

# Reset index to clean DataFrame
interval_grouped = interval_grouped.reset_index()

# Merge with all periods to ensure no missing intervals
all_periods = pd.DataFrame(
    [(date, interval) for date in pd.date_range(start_date, end_date).date for interval in full_intervals],
    columns=['Date', '15_Minute_Interval']
)
summary_report = pd.merge(
    all_periods, interval_grouped, 
    on=['Date', '15_Minute_Interval'], 
    how='left'
).fillna(0)

# Display summary report
#st.write("### Summary Report")
#st.dataframe(summary_report)

# Function to create Excel download
def create_excel_download(summary_report):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Create Summary sheet
        summary_data = summary_report.groupby('Date').agg(
            Total_Case=('Total Case', 'sum'),
            Bot_Working_Case=('Bot Working Case', 'sum'),
            Supervisor_Working_Case=('Supervisor Working Case', 'sum'),
        ).reset_index()

        # Calculate % Bot Working with 2 decimal places
        summary_data['% Bot Working'] = summary_data.apply(
            lambda row: round((row['Bot_Working_Case'] / row['Total_Case'] * 100), 2)
            if row['Total_Case'] > 0 else 0, axis=1
        )

        # Format the Date column
        summary_data['Date'] = pd.to_datetime(summary_data['Date']).dt.strftime('%d-%b-%y')

        # Add Total row to Summary sheet
        total_row = summary_data.select_dtypes(include=['number']).sum()
        total_row['Date'] = 'Total'
        total_row['% Bot Working'] = round(
            (total_row['Bot_Working_Case'] / total_row['Total_Case'] * 100)
            if total_row['Total_Case'] > 0 else 0, 2
        )
        total_row = pd.DataFrame(total_row).T
        summary_with_total = pd.concat([summary_data, total_row], ignore_index=True)

        # Write the Summary sheet to Excel
        summary_with_total.to_excel(writer, index=False, sheet_name="Summary")
        workbook = writer.book
        summary_worksheet = writer.sheets["Summary"]

        # Define formatting
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#8064A1',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#E3DFED',
            'border': 1
        })
        total_row_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#3B3838',
            'font_color': 'white',
            'border': 1
        })
        # Set column widths for the Summary sheet
        for col_num, column_name in enumerate(summary_with_total.columns):
            col_width = max(len(column_name), 15)  # Adjust the column width dynamically
            summary_worksheet.set_column(col_num, col_num, col_width)
        # Apply formatting to the Summary sheet
        for col_num, value in enumerate(summary_with_total.columns):
            summary_worksheet.write(0, col_num, value, header_format)
        for row_num, row_data in enumerate(summary_with_total.values, start=1):
            row_format = total_row_format if row_num == len(summary_with_total) else cell_format
            for col_num, cell_value in enumerate(row_data):
                summary_worksheet.write(row_num, col_num, cell_value, row_format)

        # Add individual sheets for each date
        for date, data in summary_report.groupby("Date"):
            # Ensure 'Date' column is in datetime format before formatting
            if not pd.api.types.is_datetime64_any_dtype(data['Date']):
                data['Date'] = pd.to_datetime(data['Date'])
            # Format 'Date' column as DD-MMM-YY
            data['Date'] = data['Date'].dt.strftime('%d-%b-%y')

            # Format the sheet name as DD-MMM-YY
            sheet_name = pd.to_datetime(date).strftime('%d-%b-%y')
            
            # Limit sheet name to 31 characters (Excel limitation)
            if len(sheet_name) > 31:
                sheet_name = sheet_name[:31]
            
            # Format all % Bot Working values to 2 decimal places
            data['% Bot Working'] = data.apply(
                lambda row: round((row['Bot Working Case'] / row['Total Case'] * 100), 2)
                if row['Total Case'] > 0 else 0, axis=1
            )

            # Calculate Total row
            total_row = data.select_dtypes(include=['number']).sum()
            total_row['Date'] = 'Total'
            total_row['15_Minute_Interval'] = ''
            # Calculate % Bot Working for Total with 2 decimal places
            total_row['% Bot Working'] = round(
                (total_row['Bot Working Case'] / total_row['Total Case'] * 100)
                if total_row['Total Case'] > 0 else 0, 2
            )
            total_row = pd.DataFrame(total_row).T
            data_with_total = pd.concat([data, total_row], ignore_index=True)

            # Write to Excel
            data_with_total.to_excel(writer, index=False, sheet_name=sheet_name)
            worksheet = writer.sheets[sheet_name]

            # Set column widths for individual sheets
            for col_num, column_name in enumerate(data_with_total.columns):
                col_width = max(len(column_name), 15)  # Adjust the column width dynamically
                worksheet.set_column(col_num, col_num, col_width)
                
            # Apply formatting to the individual sheets
            for col_num, value in enumerate(data.columns):
                worksheet.write(0, col_num, value, header_format)
            for row_num, row_data in enumerate(data_with_total.values, start=1):
                cell_format = workbook.add_format({
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#E3DFED',
                    'border': 1
                })
                if row_num == len(data_with_total):  # Format the "Total" row
                    cell_format.set_bold(True)
                    cell_format.set_bg_color('#3B3838')
                    cell_format.set_font_color('white')  # Corrected the method name
                for col_num, cell_value in enumerate(row_data):
                    worksheet.write(row_num, col_num, cell_value, cell_format)

    output.seek(0)
    return output

# Generate and download Excel report
excel_data = create_excel_download(summary_report)
st.download_button(
    label="📥 Download Report as Excel (With Summary)",
    data=excel_data,
    file_name="Daily_Report_With_Summary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

def display_excel_in_streamlit(excel_data):
    # Read the Excel file from BytesIO
    excel_data.seek(0)  # Reset pointer to the beginning of the BytesIO stream
    excel_sheets = pd.read_excel(excel_data, sheet_name=None)  # Read all sheets
    # Display each sheet
    for sheet_name, df in excel_sheets.items():
        st.write(f"### Sheet: {sheet_name}")
        st.dataframe(df)
# Generate and download Excel report
excel_data = create_excel_download(summary_report)
# Display the Excel data in Streamlit
st.write("## Generated Excel Data Preview")
display_excel_in_streamlit(excel_data)
