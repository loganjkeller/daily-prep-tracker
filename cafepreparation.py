import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date
import pandas as pd
import smtplib
from email.message import EmailMessage
import json

# === Setup Google Sheets Client ===
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    creds_dict = json.loads(st.secrets["gcreds"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("Daily Prep Tracker")
    sheet = spreadsheet.worksheet("Sheet1")
except Exception as e:
    st.error(f"Failed to connect to Google Sheet: {e}")
    st.stop()

# === Email Credentials from Secrets ===
EMAIL_SENDER = st.secrets["EMAIL_SENDER"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
EMAIL_RECEIVER = st.secrets["EMAIL_RECEIVER"]

# === Product List ===
PRODUCTS = [
    "Bombolone chocolate", "Bombolone Pistachio", "Bombolone strawberry", "Bombolone Chantilli creme", "Brownie",
    "Croissant Chocolate", "Croissant Pistachio", "Croissant Plain", "Apple turn over", "Multigrain Muffin",
    "Chocolate chip Muffin", "Caprese sandwich", "Egg salad Sandwich", "Prosciutto Arugula Sandwich",
    "Chicken Cutlet Sandwich", "Maritozzo", "Mix Berry Tart", "Pizza", "Prosciutto Cheese Sandwich",
    "Ham Cheese Sandwich", "Zucchini Pesto Sandwich", "Tiramisu"
]

# === Google Sheets Helper Functions ===
def save_entry_to_sheet(entry):
    try:
        sheet.append_row(entry)
    except Exception as e:
        st.error(f"Failed to save entry to sheet: {e}")

def load_data_from_sheet():
    try:
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Failed to load data from sheet: {e}")
        return pd.DataFrame()

# === Email Sender Function ===
def send_email(entry_dict, daily_df):
    msg = EmailMessage()
    msg["Subject"] = f"New Inventory Entry - {entry_dict['Date']}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    sold = entry_dict['Prepared'] - (entry_dict['Remanence'] + entry_dict['Waste'])

    body = f"""New inventory entry submitted:

Item: {entry_dict['Item']}
Date: {entry_dict['Date']}
Prepared: {entry_dict['Prepared']}
Remaining: {entry_dict['Remanence']}
Waste: {entry_dict['Waste']}
Sold: {sold}

--- DAILY TOTALS for {entry_dict['Date']} ---
"""

    for row in daily_df.itertuples():
        body += f"\n{row.Item}: Sold {row.Sold}, Waste {row.Waste}, Remaining {row.Remanence}"

    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        st.error(f"Email failed to send: {e}")

# === Streamlit App UI ===
st.title("Cafe Parioli - Daily Prep & Waste Tracker")

st.subheader("🔄 Record Today's Data")
with st.form("entry_form"):
    col1, col2 = st.columns(2)
    with col1:
        entry_date = st.date_input("Date", value=date.today())
        item = st.selectbox("Item", PRODUCTS)
    with col2:
        prepared = st.number_input("Prepared", min_value=0.0, step=1.0)
        remanence = st.number_input("Remaining", min_value=0.0, step=1.0)
        waste = st.number_input("Waste", min_value=0.0, step=1.0)

    submitted = st.form_submit_button("✅ Save Entry")

    if submitted:
        entry = [str(entry_date), item, prepared, remanence, waste]
        entry_dict = {
            "Date": str(entry_date),
            "Item": item,
            "Prepared": prepared,
            "Remanence": remanence,
            "Waste": waste
        }

        save_entry_to_sheet(entry)
        df_today = load_data_from_sheet()
        df_today = df_today[df_today["Date"] == str(entry_date)]
        df_today["Sold"] = df_today["Prepared"] - (df_today["Remanence"] + df_today["Waste"])

        send_email(entry_dict, df_today)
        st.success("Saved and email sent!")

st.subheader("📊 Cafe Parioli Tracking Dashboard")
df = load_data_from_sheet()
if not df.empty:
    df["Sold"] = df["Prepared"] - (df["Remanence"] + df["Waste"])
    summary = df.groupby(["Date", "Item"]).agg({
        "Prepared": "sum",
        "Remanence": "sum",
        "Waste": "sum",
        "Sold": "sum"
    }).reset_index()
    st.dataframe(summary)
else:
    st.info("No data yet.")