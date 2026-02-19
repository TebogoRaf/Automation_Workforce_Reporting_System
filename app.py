import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

from database import (
    init_db,
    create_user,
    login_user,
    get_admins,
    suspend_admin,
    activate_admin,
    delete_admin,
    reset_password,
    log_action,
    save_report,
    get_reports
)

from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet

# ----------------------------
# INIT
# ----------------------------
st.set_page_config(page_title="Workforce Dashboard", layout="wide")
init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""

# ----------------------------
# LOGIN
# ----------------------------
if not st.session_state.logged_in:

    st.title("🔐 Workforce Analytics Platform")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = user[1]
            st.session_state.role = user[3]
            st.rerun()
        else:
            st.error("Invalid credentials or suspended account.")

# ----------------------------
# AFTER LOGIN
# ----------------------------
else:

    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    st.sidebar.write(f"Role: {st.session_state.role}")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ============================
    # ADMIN PANEL
    # ============================
    if st.session_state.role == "Admin":

        st.header("📊 Upload Raw Data Excel (with 3 sheets: Dispositions, Inbound Productivity, Disconnections)")

        uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])

        if uploaded_file:
            xls = pd.ExcelFile(uploaded_file)
            dispositions_df = pd.read_excel(xls, "Dispositions")
            productivity_df = pd.read_excel(xls, "Inbound Productivity")
            disconnections_df = pd.read_excel(xls, "Disconnections")

            tab1, tab2, tab3 = st.tabs(["📊 Dispositions Usage", "📈 Inbound Productivity", "🔌 Disconnection Rates"])

            # ----------------------------
            # TAB 1: Dispositions Usage
            # ----------------------------
            with tab1:
                st.subheader("Dispositioned vs No Disposition (Daily)")
                daily_stats = dispositions_df.groupby("Date")["Status"].value_counts(normalize=True).unstack().fillna(0)
                st.dataframe(daily_stats)

                fig, ax = plt.subplots()
                daily_stats.plot(kind="line", ax=ax)
                ax.set_title("Daily Disposition Trends")
                st.pyplot(fig)

                st.subheader("Hourly Distribution")
                hourly_stats = dispositions_df.groupby("Time")["Status"].value_counts(normalize=True).unstack().fillna(0)
                st.dataframe(hourly_stats)

                fig2, ax2 = plt.subplots()
                hourly_stats.plot(kind="bar", stacked=True, ax=ax2)
                ax2.set_title("Hourly Disposition Distribution")
                st.pyplot(fig2)

                st.subheader("Management View (Disposition Codes)")
                code_stats = dispositions_df.groupby("Disposition Code")["Status"].value_counts(normalize=True).unstack().fillna(0)
                st.dataframe(code_stats)

                # Export Excel/PDF
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    daily_stats.to_excel(writer, sheet_name="Daily Stats")
                    hourly_stats.to_excel(writer, sheet_name="Hourly Stats")
                    code_stats.to_excel(writer, sheet_name="Disposition Codes")
                st.download_button("Download Dispositions (Excel)", excel_buffer.getvalue(), "dispositions.xlsx")

                pdf_buffer = BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
                styles = getSampleStyleSheet()
                elements = [Paragraph("Dispositions Report", styles['Heading1']), Table(daily_stats.reset_index().values.tolist())]
                doc.build(elements)
                st.download_button("Download Dispositions (PDF)", pdf_buffer.getvalue(), "dispositions.pdf")

            # ----------------------------
            # TAB 2: Inbound Productivity
            # ----------------------------
            with tab2:
                st.subheader("Calls Offered vs Answered")
                st.dataframe(productivity_df)

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Calls Offered", productivity_df["Calls Offered"].sum())
                col2.metric("Total Calls Answered", productivity_df["Calls Answered"].sum())
                col3.metric("Answer %", round(productivity_df["Calls Answered"].sum() / productivity_df["Calls Offered"].sum() * 100, 2))

                fig3, ax3 = plt.subplots()
                productivity_df.plot(x="Date", y=["Calls Offered", "Calls Answered"], ax=ax3)
                ax3.set_title("Daily Calls Offered vs Answered")
                st.pyplot(fig3)

                st.subheader("Hourly AWT & AHT")
                st.dataframe(productivity_df[["Date", "Avg Wait Time", "Avg Handle Time"]])

                # Export Excel/PDF
                excel_buffer2 = BytesIO()
                with pd.ExcelWriter(excel_buffer2, engine="openpyxl") as writer:
                    productivity_df.to_excel(writer, sheet_name="Productivity")
                st.download_button("Download Productivity (Excel)", excel_buffer2.getvalue(), "productivity.xlsx")

                pdf_buffer2 = BytesIO()
                doc2 = SimpleDocTemplate(pdf_buffer2, pagesize=letter)
                elements2 = [Paragraph("Inbound Productivity Report", styles['Heading1']), Table(productivity_df.head().values.tolist())]
                doc2.build(elements2)
                st.download_button("Download Productivity (PDF)", pdf_buffer2.getvalue(), "productivity.pdf")

            # ----------------------------
            # TAB 3: Disconnection Rates
            # ----------------------------
            with tab3:
                st.subheader("Daily Disconnection Trends")
                daily_disc = disconnections_df.groupby("Date")["Disconnection By"].value_counts(normalize=True).unstack().fillna(0)
                st.dataframe(daily_disc)

                fig4, ax4 = plt.subplots()
                daily_disc.plot(kind="line", ax=ax4)
                ax4.set_title("Daily Disconnection Rates")
                st.pyplot(fig4)

                st.subheader("Hourly Distribution")
                hourly_disc = disconnections_df.groupby("Time")["Disconnection By"].value_counts(normalize=True).unstack().fillna(0)
                st.dataframe(hourly_disc)

                fig5, ax5 = plt.subplots()
                hourly_disc.plot(kind="bar", stacked=True, ax=ax5)
                ax5.set_title("Hourly Disconnection Distribution")
                st.pyplot(fig5)

                st.subheader("Agent View")
                agent_disc = disconnections_df.groupby("Agent")["Disconnection By"].value_counts(normalize=True).unstack().fillna(0)
                st.dataframe(agent_disc)

                # Export Excel/PDF
                excel_buffer3 = BytesIO()
                with pd.ExcelWriter(excel_buffer3, engine="openpyxl") as writer:
                    daily_disc.to_excel(writer, sheet_name="Daily Disconnections")
                    hourly_disc.to_excel(writer, sheet_name="Hourly Disconnections")
                    agent_disc.to_excel(writer, sheet_name="Agent Disconnections")
                st.download_button("Download Disconnections (Excel)", excel_buffer3.getvalue(), "disconnections.xlsx")

                pdf_buffer3 = BytesIO()
                doc3 = SimpleDocTemplate(pdf_buffer3, pagesize=letter)
                elements3 = [Paragraph("Disconnection Report", styles['Heading1']), Table(daily_disc.reset_index().values.tolist())]
                doc3.build(elements3)
                st.download_button("Download Disconnections (PDF)", pdf_buffer3.getvalue(), "disconnections.pdf")

    # ============================
    # MANAGER PANEL
    # ============================
    elif st.session_state.role == "Manager":

        tab1, tab2 = st.tabs(["📊 Reports", "👥 Manage Admins"])

        with tab1:
            reports = get_reports()
            if reports:
                df = pd.DataFrame(reports, columns=["ID", "Username", "Upload Date", "Answered", "Dropped", "AHT"])
                st.dataframe(df)

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Reports", df.shape[0])
                col2.metric("Total Answered", df["Answered"].sum())
                col3.metric("Overall Avg AHT", round(df["AHT"].mean(), 2))

                st.subheader("AHT Trend")
                fig, ax = plt.subplots()
                ax.plot(df["AHT"])
                ax.set_title("AHT Over Time")
                st.pyplot(fig)

                buf = BytesIO()
                fig.savefig(buf, format="png")
                st.download_button("Download AHT Trend", buf.getvalue(), "aht_trend.png")

                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Manager Summary")

                st.download_button(
                    label="Download Summary Report (Excel)",
                    data=excel_buffer.getvalue(),
                    file_name="manager_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No reports uploaded yet.")

        # -------- ADMIN MANAGEMENT --------
        with tab2:
            admins = get_admins()
            for admin in admins:
                st.write(f"{admin[1]} | Status: {admin[6]}")
                col1, col2, col3 = st.columns(3)
                if col1.button(f"Suspend {admin[1]}", key=f"s{admin[0]}"):
                    suspend_admin(admin[0])
                    st.rerun()
                if col2.button(f"Activate {admin[1]}", key=f"a{admin[0]}"):
                    activate_admin(admin[0])
                    st.rerun()
                if col3.button(f"Delete {admin[1]}", key=f"d{admin[0]}"):
                    delete_admin(admin[0])
                    st.rerun()

            st.markdown("---")
            new_user = st.text_input("New Admin Username")
            new_pass = st.text_input("New Admin Password", type="password")

            if st.button("Create Admin"):
                if create_user(new_user, new_pass, "Admin", st.session_state.username):
                    st.success("Admin created successfully.")
                    st.rerun()
                else:
                    st.error("Admin already exists or could not be created.")
