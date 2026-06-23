import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('c:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/.env')
db_url = os.getenv('DATABASE_URL')

pg_schema = """
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    enrollment_no TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    department TEXT,
    year TEXT,
    date_registered DATE DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    book_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    isbn TEXT,
    category TEXT,
    total_copies INTEGER DEFAULT 1,
    available_copies INTEGER DEFAULT 1,
    date_added DATE DEFAULT CURRENT_DATE,
    barcode TEXT,
    price REAL DEFAULT 0,
    cover_url TEXT
);

CREATE TABLE IF NOT EXISTS borrow_records (
    id SERIAL PRIMARY KEY,
    enrollment_no TEXT NOT NULL REFERENCES students(enrollment_no) ON DELETE RESTRICT ON UPDATE CASCADE,
    book_id TEXT NOT NULL REFERENCES books(book_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    borrow_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    status TEXT DEFAULT 'borrowed',
    fine INTEGER DEFAULT 0,
    academic_year TEXT,
    fine_paid INTEGER DEFAULT 0,
    fine_paid_at TEXT,
    fine_waived INTEGER DEFAULT 0,
    renewal_count INTEGER DEFAULT 0,
    fine_rate_at_borrow INTEGER
);

CREATE TABLE IF NOT EXISTS admin_activity (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    admin_id TEXT,
    action TEXT,
    details TEXT
);

CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT
);

CREATE TABLE IF NOT EXISTS sync_deletions (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(pg_schema)
    print("Successfully created core tables in Postgres!")
except Exception as e:
    print(f"Error: {e}")
