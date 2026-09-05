import os
import psycopg2
import sqlite3
from dotenv import load_dotenv

load_dotenv()
en_no = '24210270242'

# Check Postgres
try:
    DATABASE_URL = os.getenv('DATABASE_URL')
    if 'sslmode' not in DATABASE_URL:
        sep = '&' if '?' in DATABASE_URL else '?'
        DATABASE_URL += f"{sep}sslmode=require"
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT enrollment_no, name FROM students WHERE enrollment_no=%s", (en_no,))
    print(f"POSTGRES students: {cur.fetchall()}")
    
    cur.execute("SELECT enrollment_no, is_first_login FROM student_auth WHERE enrollment_no=%s", (en_no,))
    print(f"POSTGRES student_auth: {cur.fetchall()}")
    conn.close()
except Exception as e:
    print(f"POSTGRES ERROR: {e}")

# Check SQLite
try:
    conn = sqlite3.connect('LibraryApp/library.db')
    cur = conn.cursor()
    cur.execute("SELECT enrollment_no, name FROM students WHERE enrollment_no=?", (en_no,))
    print(f"SQLITE library.db students: {cur.fetchall()}")
    conn.close()
except Exception as e:
    print(f"SQLITE ERROR: {e}")
