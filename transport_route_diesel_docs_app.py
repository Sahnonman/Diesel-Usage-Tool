import streamlit as st
import pandas as pd
import math
import smtplib
from email.message import EmailMessage
from twilio.rest import Client

# Page configuration
st.set_page_config(page_title="Diesel & Vehicle Reminder System", page_icon="🚛")

# Title
st.title("⛽ Diesel Cost & Vehicle Document Reminder System")

# ----- Section 1: Diesel Cost Calculator -----
mode = st.radio(
    "Fuel consumption mode:", ["Calculate rate from usage", "Enter rate directly"], index=0
)
if mode == "Calculate rate from usage":
    with st.form("consumption_rate_form"):
        monthly_mileage = st.number_input("Monthly distance per truck (km)", min_value=0.0, value=1000.0)
        monthly_fuel = st.number_input("Monthly fuel used per truck (liters)", min_value=0.0, value=200.0)
        submit_rate = st.form_submit_button("Compute Consumption Rate")
    if submit_rate:
        if monthly_mileage > 0:
            cons_rate = monthly_fuel / monthly_mileage
            st.success(f"Consumption rate: {cons_rate:.3f} L/km per truck")
            st.session_state['cons_rate'] = cons_rate
            st.session_state['mileage'] = monthly_mileage
        else:
            st.error("Monthly mileage must be > 0.")
else:
    with st.form("diesel_cost_form"):
        monthly_mileage = st.number_input(
            "Monthly distance per truck (km)",
            min_value=0.0,
            value=st.session_state.get('mileage', 1000.0)
        )
        cons_rate = st.number_input(
            "Consumption rate (L/km)",
            min_value=0.0,
            value=st.session_state.get('cons_rate', 0.3)
        )
        fuel_price = st.number_input("Fuel price per liter (SAR)", min_value=0.0, value=2.50)
        weekly_limit = st.number_input("Weekly mileage limit per truck (km)", min_value=0.0, value=300.0)
        fleet_size = st.number_input("Number of trucks in fleet", min_value=1, value=10, step=1)
        submit_cost = st.form_submit_button("Calculate Monthly Diesel Cost")
    if submit_cost:
        cost_per_truck = monthly_mileage * cons_rate * fuel_price
        total_cost = cost_per_truck * fleet_size
        st.success(f"Monthly diesel cost per truck: SAR {cost_per_truck:,.2f}")
        st.success(f"Monthly diesel cost for fleet: SAR {total_cost:,.2f}")
        avg_weekly = monthly_mileage / 4
        if avg_weekly > weekly_limit:
            st.warning(f"⚠️ Avg weekly mileage {avg_weekly:.1f} km exceeds limit {weekly_limit} km.")
        else:
            st.info(f"✅ Avg weekly mileage {avg_weekly:.1f} km within limit per truck.")

# ----- Section 2: Vehicle Document Expiry Reminders -----
st.header("📅 Document Expiry Reminders")

# Contact method selection
channel = st.selectbox("Reminder channel:", ["Email", "SMS", "WhatsApp"])

# Email settings
otp_email = {
    "smtp_server": st.text_input("SMTP Server", value="smtp.example.com"),
    "smtp_port": st.number_input("SMTP Port", value=587),
    "user": st.text_input("SMTP User", value="your_email@example.com"),
    "password": st.text_input("SMTP Password", type="password"),
    "recipient": st.text_input("Email Recipient", value="fleet.manager@example.com")
}

# Twilio settings for SMS/WhatsApp
otp_twilio = {
    "sid": st.text_input("Twilio Account SID", value=""),
    "token": st.text_input("Twilio Auth Token", type="password"),
    "from_phone": st.text_input("Twilio From Number", value="+1234567890"),
    "to_phone": st.text_input("Recipient Phone Number", value="+9665XXXXXXX")
}

uploaded = st.file_uploader("Upload Excel (sheet 'Documents')", type=["xlsx"])
if uploaded:
    df = pd.read_excel(uploaded, sheet_name="Documents")
    st.dataframe(df)
    client = Client(otp_twilio['sid'], otp_twilio['token']) if channel in ["SMS", "WhatsApp"] else None
    sent = []
    for _, row in df.iterrows():
        vid = row['Vehicle_ID']
        for doc, col in [("Inspection", "Inspection_Expiry"), ("Registration", "Registration_Expiry"), ("Operating Card", "Operating_Card_Expiry")]:
            expiry = pd.to_datetime(row[col])
            remind_date = expiry - pd.DateOffset(months=1)
            if pd.Timestamp.now().normalize() >= remind_date.normalize():
                message = f"Reminder: {doc} for {vid} expires on {expiry.date()}"
                if channel == "Email":
                    msg = EmailMessage()
                    msg['Subject'] = message
                    msg['From'] = otp_email['user']
                    msg['To'] = otp_email['recipient']
                    msg.set_content(message)
                    with smtplib.SMTP(otp_email['smtp_server'], otp_email['smtp_port']) as smtp:
                        smtp.starttls()
                        smtp.login(otp_email['user'], otp_email['password'])
                        smtp.send_message(msg)
                else:
                    from_prefix = 'whatsapp:' + otp_twilio['from_phone'] if channel == 'WhatsApp' else otp_twilio['from_phone']
                    to_prefix = 'whatsapp:' + otp_twilio['to_phone'] if channel == 'WhatsApp' else otp_twilio['to_phone']
                    client.messages.create(
                        from_=from_prefix,
                        to=to_prefix,
                        body=message
                    )
                sent.append((vid, doc, channel))
    if sent:
        st.success(f"Sent reminders via {channel} for: {sent}")
    else:
        st.info("No reminders to send today.")
else:
    st.info("Please upload 'Documents' Excel to schedule reminders.")
