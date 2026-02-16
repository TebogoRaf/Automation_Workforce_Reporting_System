# database.py
import sqlite3
import bcrypt
import pandas as pd
from datetime import datetime

DB_NAME = "workforce.db"

# ----------------------------0
# DATABASE CONNECTION
# ----------------------------
def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ----------------------------
# TABLE CREATION
# ----------------------------
def create_tables():
    conn = get_connection()
    c = conn.cursor()
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            status TEXT DEFAULT 'Active',
            last_login TEXT,
            created_by TEXT
        )
    """)
    # Reports table
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
    # Audit log
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            performed_by TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

# ----------------------------
# AUDIT LOG
# ----------------------------
def log_action(action, user):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO audit_log (action, performed_by, timestamp) VALUES (?,?,?)",
              (action, user, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ----------------------------
# USERS
# ----------------------------
def create_user(username, password, role, created_by=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role, created_by) VALUES (?,?,?,?)",
                  (username, hash_password(password), role, created_by))
        conn.commit()
        if created_by:
            log_action(f"Created {role}: {username}", created_by)
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_password(password)))
    result = c.fetchone()
    conn.close()
    return result

def update_last_login(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET last_login=? WHERE username=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
    conn.commit()
    log_action("Logged in", username)
    conn.close()

def reset_password(username, new_password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    if c.fetchone():
        c.execute("UPDATE users SET password=? WHERE username=?", (hash_password(new_password), username))
        conn.commit()
        log_action("Password reset", username)
        conn.close()
        return True
    conn.close()
    return False

def get_admins():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username, status, last_login FROM users WHERE role='Admin'")
    admins = c.fetchall()
    conn.close()
    return admins

def remove_admin(admin_username, manager_username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM reports WHERE username=?", (admin_username,))
    if c.fetchone():
        conn.close()
        return False
    c.execute("DELETE FROM users WHERE username=?", (admin_username,))
    conn.commit()
    log_action(f"Removed Admin: {admin_username}", manager_username)
    conn.close()
    return True

def get_reports():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM reports", conn)
    conn.close()
    return df

def save_report(username, answered, dropped, aht):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO reports (username, upload_date, answered, dropped, aht) VALUES (?,?,?,?,?)",
              (username, datetime.now().strftime("%Y-%m-%d"), answered, dropped, aht))
    conn.commit()
    conn.close()