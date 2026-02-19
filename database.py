import psycopg2
import os
import hashlib
from datetime import datetime

# -----------------------------------
# DATABASE CONNECTION (PostgreSQL)
# -----------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)


# -----------------------------------
# INITIALIZE DATABASE
# -----------------------------------
def init_db():
    create_tables()
    create_default_users()


# -----------------------------------
# CREATE TABLES (PostgreSQL VERSION)
# -----------------------------------
def create_tables():
    conn = get_connection()
    c = conn.cursor()

    # USERS TABLE
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            created_by TEXT,
            last_login TEXT,
            status TEXT
        )
    """)

    # REPORTS TABLE
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            username TEXT,
            upload_date TEXT,
            answered INTEGER,
            dropped INTEGER,
            aht REAL
        )
    """)

    # LOGS TABLE
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            username TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------------
# PASSWORD HASHING
# -----------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# -----------------------------------
# CREATE DEFAULT USERS
# -----------------------------------
def create_default_users():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]

    if count == 0:
        # Manager
        c.execute("""
            INSERT INTO users (username, password, role, created_by, status, last_login)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            "manager",
            hash_password("manager123"),
            "Manager",
            "System",
            "Active",
            None
        ))

        # Admin
        c.execute("""
            INSERT INTO users (username, password, role, created_by, status, last_login)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            "admin",
            hash_password("admin123"),
            "Admin",
            "System",
            "Active",
            None
        ))

        conn.commit()

    conn.close()


# -----------------------------------
# CREATE USER
# -----------------------------------
def create_user(username, password, role, created_by):
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO users (username, password, role, created_by, status, last_login)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            username,
            hash_password(password),
            role,
            created_by,
            "Active",
            None
        ))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# -----------------------------------
# LOGIN
# -----------------------------------
def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = c.fetchone()

    if user:
        id_, uname, db_password, role, created_by, last_login, status = user

        if status != "Active":
            conn.close()
            return None

        if db_password == hash_password(password):
            c.execute(
                "UPDATE users SET last_login=%s WHERE id=%s",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_)
            )
            conn.commit()
            conn.close()
            return user

    conn.close()
    return None


# -----------------------------------
# ADMIN MANAGEMENT
# -----------------------------------
def get_admins():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role='Admin'")
    admins = c.fetchall()
    conn.close()
    return admins


def suspend_admin(admin_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status='Suspended' WHERE id=%s", (admin_id,))
    conn.commit()
    conn.close()


def activate_admin(admin_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status='Active' WHERE id=%s", (admin_id,))
    conn.commit()
    conn.close()


def delete_admin(admin_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=%s", (admin_id,))
    conn.commit()
    conn.close()
    return True


# -----------------------------------
# RESET PASSWORD
# -----------------------------------
def reset_password(username, new_password):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET password=%s WHERE username=%s",
        (hash_password(new_password), username)
    )
    conn.commit()
    conn.close()


# -----------------------------------
# LOG ACTION
# -----------------------------------
def log_action(username, action):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (username, action, timestamp)
        VALUES (%s, %s, %s)
    """, (
        username,
        action,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()


# -----------------------------------
# REPORT FUNCTIONS
# -----------------------------------
def save_report(username, answered, dropped, aht):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO reports (username, upload_date, answered, dropped, aht)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        username,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        answered,
        dropped,
        aht
    ))
    conn.commit()
    conn.close()


def get_reports():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM reports")
    reports = c.fetchall()
    conn.close()
    return reports