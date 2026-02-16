# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import random
from database import *

st.set_page_config(layout="wide", page_title="Workforce Analytics Dashboard")

# ----------------------------
# BACKGROUND SLIDESHOW
# ----------------------------
bg_images = [
    "https://images.unsplash.com/photo-1605902711622-cfb43c4430d8?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?auto=format&fit=crop&w=1600&q=80"
]
bg_url = random.choice(bg_images)
st.markdown(f"""
<style>
.stApp {{
background-image: url('{bg_url}');
background-size: cover;
background-repeat: no-repeat;
background-attachment: fixed;
}}
.block-container {{
background: rgba(15,23,42,0.75);
border-radius: 15px;
padding: 2rem;
}}
.kpi-card {{
background-color: #1f2937; padding:25px; border-radius:12px; text-align:center; color:white; box-shadow:0px 4px 15px rgba(0,0,0,0.4);
}}
.section-title {{color:white; margin-top:30px; margin-bottom:15px;}}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# INITIALIZE DATABASE
# ----------------------------
create_tables()

# ----------------------------
# SESSION STATE
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ----------------------------
# LOGIN / PASSWORD RESET
# ----------------------------
if not st.session_state.logged_in:
    st.title("🔐 Workforce Analytics Platform")
    menu = ["Login", "Forgot Password"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            result = login_user(user, pwd)
            if result:
                if result[3] != "Active":
                    st.error("Your account is suspended. Contact manager.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.username = result[0]
                    st.session_state.role = result[2]
                    update_last_login(result[0])
                    st.experimental_rerun()
            else:
                st.error("Invalid credentials")

    elif choice == "Forgot Password":
        user = st.text_input("Enter your username")
        new_pwd = st.text_input("New password", type="password")
        if st.button("Reset Password"):
            if reset_password(user, new_pwd):
                st.success("Password updated successfully")
            else:
                st.error("User not found")

# ----------------------------
# DASHBOARD
# ----------------------------
if st.session_state.logged_in:
    st.title("📊 Workforce Executive Dashboard")
    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    st.sidebar.write(f"Role: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    # ----------------------------
    # MANAGER: ADMIN MANAGEMENT
    # ----------------------------
    if st.session_state.role == "Manager":
        st.subheader("Manager Controls - Admin Management")
        st.markdown("### Add Admin")
        new_admin = st.text_input("Admin Username")
        new_pwd = st.text_input("Admin Password", type="password")
        if st.button("Create Admin"):
            if create_user(new_admin, new_pwd, "Admin", created_by=st.session_state.username):
                st.success(f"Admin {new_admin} created")
                st.experimental_rerun()
            else:
                st.error("Admin already exists")

        st.markdown("### Remove Admin")
        admins = get_admins()
        admin_usernames = [a[0] for a in admins]
        if admin_usernames:
            to_remove = st.selectbox("Select admin to remove", admin_usernames)
            if st.button("Remove Admin"):
                if remove_admin(to_remove, st.session_state.username):
                    st.success(f"Admin {to_remove} removed")
                    st.experimental_rerun()
                else:
                    st.error("Cannot remove Admin with reports uploaded")
        else:
            st.info("No admins found")

    # ----------------------------
    # ADMIN: REPORT UPLOAD
    # ----------------------------
    if st.session_state.role == "Admin":
        st.subheader("Upload Excel Report")
        uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            if "date" not in df.columns or "status" not in df.columns:
                st.error("Excel must contain 'Date' and 'Status'")
                st.stop()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            aht_column = None
            for col in df.columns:
                if "aht" in col or "handle" in col:
                    aht_column = col
                    break
            answered = df[df["status"].str.lower() == "answered"].shape[0]
            dropped = df[df["status"].str.lower() == "unanswered"].shape[0]
            avg_aht = df[aht_column].mean() if aht_column else 0

            # Save to DB
            save_report(st.session_state.username, answered, dropped, avg_aht)
            st.success("Report processed and saved!")

            # ----------------------------
            # KPI Cards
            # ----------------------------
            st.subheader("Report Summary")
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"<div class='kpi-card'><h3>Answered</h3><h2>{answered}</h2></div>", unsafe_allow_html=True)
            col2.markdown(f"<div class='kpi-card'><h3>Dropped</h3><h2>{dropped}</h2></div>", unsafe_allow_html=True)
            col3.markdown(f"<div class='kpi-card'><h3>Average AHT</h3><h2>{round(avg_aht,2)}</h2></div>", unsafe_allow_html=True)

            # Pie chart
            fig1, ax1 = plt.subplots()
            ax1.pie([answered, dropped], labels=["Answered","Dropped"], autopct="%1.1f%%", colors=['#16a34a','#dc2626'])
            ax1.axis("equal")
            st.pyplot(fig1)

            # Histogram
            st.subheader("Status Histogram")
            df['status'].value_counts().plot(kind='bar', color=['#16a34a','#dc2626'])
            st.pyplot(plt.gcf())

    # ----------------------------
    # VIEW REPORTS (All Roles)
    # ----------------------------
    st.subheader("Reports Overview")
    reports_df = get_reports()
    if reports_df.empty:
        st.info("No reports yet")
    else:
        if st.session_state.role == "Admin":
            st.dataframe(reports_df)
        else:
            st.dataframe(reports_df[["id","username","upload_date","answered","dropped","aht"]])