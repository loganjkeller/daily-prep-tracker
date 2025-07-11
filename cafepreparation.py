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
    creds_dict = dict(st.secrets["gcreds"])  # Convert from AttrDict to plain dict
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key("1XvHHGrzOdQcTNSFnb9cinckaP5AUZAAhYvoTgoBTQ2o")
    sheet = spreadsheet.worksheet("Sheet1")
except Exception as e:
    st.error(f"Failed to connect to Google Sheet: {e.__class__.__name__} - {e}")
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
    "Ham Cheese Sandwich", "Zucchini Pesto Sandwich", "Tiramisu", "Vegan Crostata",
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
    msg["Subject"] = f"New Inventory Entry - {entry_dict['date']}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    sold = entry_dict['prepared'] - (entry_dict['remanence'] + entry_dict['waste'])

    body = f"""New inventory entry submitted:

item: {entry_dict['item']}
date: {entry_dict['date']}
prepared: {entry_dict['prepared']}
remaining: {entry_dict['remanence']}
waste: {entry_dict['waste']}
sold: {sold}

--- DAILY TOTALS for {entry_dict['date']} ---
"""

    for row in daily_df.itertuples():
        body += f"\n{row.item}: sold {row.sold}, waste {row.waste}, remaining {row.remanence}"

    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        st.error(f"Email failed to send: {e}")

# === Streamlit App UI ===
st.title("Cafe Parioli - Daily Prep & Waste Tracker")
st.markdown(
    "<div style='text-align: center; font-size: 12px; color: gray; margin-top: 50px;'>"
    "DEVELOP BY WOLF BY LOGAN TECHNOLOGY ®"
    "</div>",
    unsafe_allow_html=True
)

st.subheader("🔄 Record Today's Data")
with st.form("entry_form"):
    col1, col2 = st.columns(2)
    with col1:
        entry_date = st.date_input("date", value=date.today())
        item = st.selectbox("item", PRODUCTS)
    with col2:
        prepared = st.number_input("prepared", min_value=0.0, step=1.0)
        remanence = st.number_input("remaining", min_value=0.0, step=1.0)
        waste = st.number_input("waste", min_value=0.0, step=1.0)

    submitted = st.form_submit_button("✅ Save Entry")

    if submitted:
        entry = [str(entry_date), item, prepared, remanence, waste]
        entry_dict = {
            "date": str(entry_date),
            "item": item,
            "prepared": prepared,
            "remanence": remanence,
            "waste": waste
        }

        save_entry_to_sheet(entry)
        df_today = load_data_from_sheet()
        df_today = df_today[df_today["date"] == str(entry_date)]
        df_today["sold"] = df_today["prepared"] - (df_today["remanence"] + df_today["waste"])

        send_email(entry_dict, df_today)
        st.success("Saved and email sent!")

st.subheader("📊 Cafe Parioli Tracking Dashboard")
df = load_data_from_sheet()
if not df.empty:
    df["sold"] = df["prepared"] - (df["remanence"] + df["waste"])
    summary = df.groupby(["date", "item"]).agg({
        "prepared": "sum",
        "remanence": "sum",
        "waste": "sum",
        "sold": "sum"
    }).reset_index()
    st.dataframe(summary)
else:
    st.info("No data yet.")