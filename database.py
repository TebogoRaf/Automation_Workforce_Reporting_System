import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "workforce.db"

# ----------------------------
# CONNECTION
# ----------------------------
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# ----------------------------
# INITIALIZE DATABASE
# ----------------------------
def init_db():
    create_tables()
    create_default_manager()

# ----------------------------
# CREATE TABLES
# ----------------------------
def create_tables():
    conn = get_connection()
    c = conn.cursor()

    # USERS
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            created_by TEXT,
            last_login TEXT,
            status TEXT
        )
    """)

    # REPORTS
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

    # LOGS
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

# ----------------------------
# PASSWORD HASHING
# ----------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ----------------------------
# DEFAULT MANAGER
# ----------------------------
def create_default_manager():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE role='Manager'")
    if not c.fetchone():
        c.execute("""
            INSERT INTO users (username, password, role, created_by, status, last_login)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "manager",
            hash_password("manager123"),
            "Manager",
            "System",
            "Active",
            None
        ))
        conn.commit()

    conn.close()

# ----------------------------
# CREATE USER
# ----------------------------
def create_user(username, password, role, created_by):
    conn = get_connection()
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO users (username, password, role, created_by, status, last_login)
            VALUES (?, ?, ?, ?, ?, ?)
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
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# ----------------------------
# LOGIN
# ----------------------------
def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()

    if user:
        id_, uname, db_password, role, created_by, last_login, status = user

        if status != "Active":
            conn.close()
            return None

        if db_password == hash_password(password):
            c.execute(
                "UPDATE users SET last_login=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_)
            )
            conn.commit()
            conn.close()
            return user

    conn.close()
    return None

# ----------------------------
# ADMIN MANAGEMENT
# ----------------------------
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
    c.execute("UPDATE users SET status='Suspended' WHERE id=?", (admin_id,))
    conn.commit()
    conn.close()

def activate_admin(admin_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET status='Active' WHERE id=?", (admin_id,))
    conn.commit()
    conn.close()

def delete_admin(admin_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (admin_id,))
    conn.commit()
    conn.close()
    return True

# ----------------------------
# RESET PASSWORD
# ----------------------------
def reset_password(username, new_password):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET password=? WHERE username=?",
        (hash_password(new_password), username)
    )
    conn.commit()
    conn.close()

# ----------------------------
# LOG ACTION
# ----------------------------
def log_action(username, action):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (username, action, timestamp)
        VALUES (?, ?, ?)
    """, (
        username,
        action,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

# ----------------------------
# REPORT FUNCTIONS
# ----------------------------
def save_report(username, answered, dropped, aht):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO reports (username, upload_date, answered, dropped, aht)
        VALUES (?, ?, ?, ?, ?)
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