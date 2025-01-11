import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# Set Streamlit page configuration
st.set_page_config(
    page_title="Bot Performance Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("### Bot Performance Dashboard")

# Example DataFrame for demonstration
data = {
    "Date": ["20-Dec-24"] * 16,
    "15_Minute_Interval": [
        "00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30", "01:45",
        "02:00", "02:15", "02:30", "02:45", "03:00", "03:15", "03:30", "03:45"
    ],
    "Bot": [0] * 16,
    "Supervisor": [0] * 16,
    "Total Case": [0] * 16,
    "Bot Working Case": [0] * 16,
    "Supervisor Working Case": [0] * 16,
    "% Bot Working": [0.0] * 16,
}
df = pd.DataFrame(data)

# Define alternating row styles and centered text
def style_dataframe(df):
    # Alternating row colors and header styles
    styles = [
        dict(selector="thead th", props=[("background-color", "#8064A1"), ("color", "white"), ("text-align", "center")]),
        dict(selector="tbody td", props=[("text-align", "center"), ("padding", "10px")]),
        dict(selector="tbody tr:nth-child(even)", props=[("background-color", "#E3DFED")]),
        dict(selector="tbody tr:nth-child(odd)", props=[("background-color", "white")]),
    ]
    return df.style.set_table_styles(styles).set_properties(**{
        'text-align': 'center',
        'padding': '10px'
    })

# Apply styling to the DataFrame
styled_df = style_dataframe(df)

# Render the styled DataFrame
st.markdown("### Styled Table")
st.write(
    styled_df.to_html(index=False), unsafe_allow_html=True
)

# Example Plotly chart
st.markdown("### Example Chart: Bot vs Supervisor Cases")
fig = px.bar(
    df,
    x="15_Minute_Interval",
    y=["Bot", "Supervisor"],
    title="Bot vs Supervisor Cases by 15-Minute Interval",
    labels={"value": "Cases", "variable": "Handled By"},
    barmode="stack",
)
st.plotly_chart(fig, use_container_width=True)

# Excel download functionality
def create_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    output.seek(0)
    return output

# Generate Excel download
excel_data = create_excel_download(df)

st.markdown("### Download Report")
st.download_button(
    label="📥 Download Report as Excel",
    data=excel_data,
    file_name="Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
