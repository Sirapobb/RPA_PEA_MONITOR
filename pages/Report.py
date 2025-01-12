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
            'border': 1
        })
        total_row_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F4B084',
            'border': 1
        })

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
            
            # Format all `% Bot Working` values to 2 decimal places
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
