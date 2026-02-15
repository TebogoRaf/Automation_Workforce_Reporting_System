import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import hashlib
from datetime import datetime
import sqlite3
from openpyxl.drawing.image import Image as XLImage
import random

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
# DATABASE
# ----------------------------
conn = sqlite3.connect("workforce.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    upload_date TEXT,
    answered INTEGER,
    dropped INTEGER,
    aht REAL
)
""")
conn.commit()

# ----------------------------
# AUTH FUNCTIONS
# ----------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username,password,role):
    try:
        c.execute("INSERT INTO users VALUES (?,?,?)",(username,hash_password(password),role))
        conn.commit()
        return True
    except:
        return False

def login_user(username,password):
    c.execute("SELECT * FROM users WHERE username=? AND password=?",(username,hash_password(password)))
    return c.fetchone()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ----------------------------
# LOGIN / SIGNUP
# ----------------------------
if not st.session_state.logged_in:
    st.title("🔐 Workforce Analytics Platform")
    menu = ["Login","Signup"]
    choice = st.sidebar.selectbox("Menu",menu)

    if choice=="Signup":
        user = st.text_input("Username")
        pwd = st.text_input("Password",type="password")
        role = st.selectbox("Role",["Admin","Manager"])
        if st.button("Signup"):
            if create_user(user,pwd,role):
                st.success("Account Created")
            else:
                st.error("User already exists")

    elif choice=="Login":
        user = st.text_input("Username")
        pwd = st.text_input("Password",type="password")
        if st.button("Login"):
            result = login_user(user,pwd)
            if result:
                st.session_state.logged_in = True
                st.session_state.username = result[0]
                st.session_state.role = result[2]
                st.rerun()
            else:
                st.error("Invalid credentials")

# ----------------------------
# DASHBOARD
# ----------------------------
if st.session_state.logged_in:
    st.title("📊 Workforce Executive Dashboard")
    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    st.sidebar.write(f"Role: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ----------------------------
    # Admin can upload
    # ----------------------------
    uploaded_file = None
    if st.session_state.role == "Admin":
        uploaded_file = st.file_uploader("Upload Excel Report", type=["xlsx"])

    # ----------------------------
    # Admin upload processing
    # ----------------------------
    if uploaded_file and st.session_state.role=="Admin":
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        if "date" not in df.columns or "status" not in df.columns:
            st.error("Excel must contain 'Date' and 'Status'")
            st.stop()

        df["date"] = pd.to_datetime(df["date"],errors="coerce")
        df = df.dropna(subset=["date"])

        # Detect AHT column
        aht_column = None
        for col in df.columns:
            if "aht" in col or "handle" in col:
                aht_column = col
                break

        answered = df[df["status"].str.lower()=="answered"].shape[0]
        dropped = df[df["status"].str.lower()=="unanswered"].shape[0]
        avg_aht = df[aht_column].mean() if aht_column else 0

        # Save to DB
        c.execute("""
        INSERT INTO reports (username, upload_date, answered, dropped, aht)
        VALUES (?,?,?,?,?)
        """,(st.session_state.username,datetime.now().strftime("%Y-%m-%d"),answered,dropped,avg_aht))
        conn.commit()
        st.success("Report processed and saved!")

    # ----------------------------
    # Fetch reports from DB for Admin or Manager
    # ----------------------------
    reports_df = pd.read_sql_query("SELECT * FROM reports", conn)
    if reports_df.empty:
        st.info("No reports available yet.")
    else:
        # Admin sees everything + select report to download
        if st.session_state.role=="Admin":
            st.subheader("Uploaded Reports (Admin View)")
            st.dataframe(reports_df)
            selected_id = st.selectbox("Select Report ID to view/download", reports_df["id"])
        else:
            # Manager view only
            st.subheader("Available Reports (Manager View)")
            st.dataframe(reports_df[["id","username","upload_date","answered","dropped","aht"]])
            selected_id = st.selectbox("Select Report ID to view/download", reports_df["id"])

        report = reports_df[reports_df["id"] == selected_id].iloc[0]

        st.markdown(f"**User:** {report['username']} | **Upload Date:** {report['upload_date']}")
        st.markdown(f"**Answered:** {report['answered']} | **Dropped:** {report['dropped']} | **AHT:** {report['aht']}")

        # KPI cards
        col1,col2,col3,col4 = st.columns(4)
        col1.markdown(f"<div class='kpi-card'><h3>Total Answered</h3><h2>{report['answered']}</h2></div>",unsafe_allow_html=True)
        col2.markdown(f"<div class='kpi-card'><h3>Total Dropped</h3><h2>{report['dropped']}</h2></div>",unsafe_allow_html=True)
        col3.markdown(f"<div class='kpi-card'><h3>Average AHT</h3><h2>{round(report['aht'],2)}</h2></div>",unsafe_allow_html=True)
        col4.markdown(f"<div class='kpi-card'><h3>Answer Rate</h3><h2>{round((report['answered']/(report['answered']+report['dropped']))*100,2) if (report['answered']+report['dropped'])>0 else 0}%</h2></div>",unsafe_allow_html=True)

        # Pie chart
        st.subheader("Call Status Distribution")
        pie_data = [report['answered'], report['dropped']]
        labels = ["Answered","Dropped"]
        colors = ['#16a34a','#dc2626']
        fig2, ax2 = plt.subplots()
        ax2.pie(pie_data, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
        ax2.axis('equal')
        st.pyplot(fig2)

        # Excel download
        summary_df = pd.DataFrame({"Metric":["Total Answered","Total Dropped","Average AHT"],
                                   "Value":[report['answered'],report['dropped'],report['aht']]})

        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="KPI Summary", index=False)
        excel_buffer.seek(0)
        st.download_button("📥 Download Excel Report", excel_buffer.getvalue(),
                           f"Executive_Workforce_Report_{report['username']}.xlsx")

        # PDF download
        def generate_pdf_report():
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width,height = letter
            y = height-40
            c.setFont("Helvetica-Bold",16)
            c.drawString(50,y,"Workforce Executive Report")
            y -= 30
            c.setFont("Helvetica",12)
            c.drawString(50,y,f"Total Answered: {report['answered']}")
            y -= 20
            c.drawString(50,y,f"Total Dropped: {report['dropped']}")
            y -= 20
            c.drawString(50,y,f"Average AHT: {round(report['aht'],2)}")
            y -= 40

            pie_img_pdf = BytesIO()
            fig2.savefig(pie_img_pdf, format='png')
            pie_img_pdf.seek(0)
            pil_img = Image.open(pie_img_pdf)

            c.drawInlineImage(pil_img,50,y-200,width=200,height=200)

            c.save()
            buffer.seek(0)
            return buffer

        st.download_button("📄 Download PDF Report", generate_pdf_report(),
                           f"Executive_Workforce_Report_{report['username']}.pdf",mime="application/pdf")