"""Database connection"""
import datetime
import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host'    : 'localhost',
    'user'    : 'root',
    'password': '#miru*06',          # <- Enter your MySQL password here
    'database': 'library_db',
    'charset' : 'utf8mb4',
    'autocommit': True
}

def get_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    # Force the session timezone to IST so that NOW() returns correct IST time
    cur = conn.cursor()
    cur.execute("SET time_zone = '+05:30'")
    cur.close()
    return conn

def init_db():
    try:
        conn = get_connection()
        # Auto-create the student_feedback table if it doesn't exist
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_feedback (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                user_id      INT NOT NULL,
                category     ENUM('general','books','staff','facilities','suggestions') DEFAULT 'general',
                subject      VARCHAR(200) NOT NULL,
                message      TEXT NOT NULL,
                rating       TINYINT CHECK (rating BETWEEN 1 AND 5),
                is_read      TINYINT(1) DEFAULT 0,
                admin_reply  TEXT,
                replied_at   TIMESTAMP NULL DEFAULT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cur.close()
        conn.close()
        print("Database connected successfully")
        print("student_feedback table ready")
    except Error as e:
        print(f"Database connection failed: {e}")

def _serialize_row(row):
    """Convert datetime/date objects to MySQL-format strings.

    Root cause: Flask's default JSON encoder serialises Python datetime objects
    as RFC-822 strings like 'Fri, 17 Apr 2026 10:30:00 GMT'.  The frontend
    parseDateTime() cannot parse that format and falls back to new Date(s),
    which treats the 'GMT' suffix as UTC — showing times 5:30 h behind in IST.

    Fix: format datetimes as plain 'YYYY-MM-DD HH:MM:SS' strings so the
    existing frontend regex matches and interprets them as local (IST) time.
    """
    if not isinstance(row, dict):
        return row
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime.datetime):
            out[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(v, datetime.date):
            out[k] = v.strftime('%Y-%m-%d')
        else:
            out[k] = v
    return out

def query(sql, params=None, fetch=False, fetchone=False, lastrowid=False):
    conn = None
    cur  = None
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        if fetch:
            rows = cur.fetchall()
            return [_serialize_row(r) for r in rows]
        if fetchone:
            row = cur.fetchone()
            return _serialize_row(row) if row else row
        conn.commit()
        if lastrowid:
            return cur.lastrowid
        return cur.rowcount
    except Error as e:
        if conn: conn.rollback()
        raise
    finally:
        if cur:  cur.close()
        if conn: conn.close()
