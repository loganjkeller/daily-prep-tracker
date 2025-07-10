import streamlit as st
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")


# === CONFIG ===
FILE = "inventory_log.csv"
PRODUCTS = ["Bombolone chocolate", "Bombolone Pistachio", "Bombolone strawberry", "Bombolone Chantilli creme", "Brownie",
            "Croissant Chocolate", "Croissant Pistachio", "Croissant Plain","Apple turn over","Multigrain Muffin","Chocolate chip Muffin","Caprese sandwich",
            "Egg salad Sandwich","Prosciutto Arugula Sandwich","Chicken Cutlet Sandwich","Maritozzo","Mix Berry Tart","Pizza","Prosciutto Cheese Sandwich", "Ham Cheese Sandwich",
            "Zucchini Pesto Sandwich","Tiramisu",]

# === LOAD CSV ===
@st.cache_data
def load_data():
    try:
        return pd.read_csv(FILE)
    except:
        return pd.DataFrame(columns=["Date", "Item", "Prepared", "Remanence", "Waste"])

df = load_data()

# === EMAIL FUNCTION ===
def send_email(entry, daily_summary):
    msg = EmailMessage()
    msg["Subject"] = f"New Inventory Entry - {entry['Date']}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    sold = entry['Prepared'] - (entry['Remanence'] + entry['Waste'])
    body = f"""New inventory entry submitted:

Item: {entry['Item']}
Date: {entry['Date']}
Prepared: {entry['Prepared']}
Remaining: {entry['Remanence']}
Waste: {entry['Waste']}
Sold: {sold}

--- DAILY TOTALS for {entry['Date']} ---
"""

    for row in daily_summary.itertuples():
        body += f"\n{row.Item}: Sold {row.Sold}, Waste {row.Waste}, Remaining {row.Remanence}"

    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print("Email failed:", e)

# === STREAMLIT UI ===
st.title("🍞 Daily Prep & Waste Tracker")

# --- Data Entry ---
st.subheader("🔄 Record Today's Data")
with st.form("entry_form"):
    col1, col2 = st.columns(2)
    with col1:
        entry_date = st.date_input("Date", value=date.today())
        item = st.selectbox("Item", PRODUCTS)
    with col2:
        prepared = st.number_input("Prepared (morning)", min_value=0.0, step=1.0)
        remanence = st.number_input("Remaining (night)", min_value=0.0, step=1.0)
        waste = st.number_input("Thrown Out", min_value=0.0, step=1.0)

    submitted = st.form_submit_button("✅ Save Entry")

    if submitted:
        new_entry = {
            "Date": str(entry_date),
            "Item": item,
            "Prepared": prepared,
            "Remanence": remanence,
            "Waste": waste
        }
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(FILE, index=False)

        # Prepare and send email summary
        df["Sold"] = df["Prepared"] - (df["Remanence"] + df["Waste"])
        daily_summary = df[df["Date"] == str(entry_date)].groupby("Item").agg({
            "Prepared": "sum",
            "Remanence": "sum",
            "Waste": "sum",
            "Sold": "sum"
        }).reset_index()

        send_email(new_entry, daily_summary)
        st.success("Entry saved and email sent!")

# --- Dashboard ---
st.subheader("📊 Dashboard")
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
    st.info("No entries yet.")
