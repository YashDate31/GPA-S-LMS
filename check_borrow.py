import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
if 'sslmode' not in DATABASE_URL:
    sep = '&' if '?' in DATABASE_URL else '?'
    DATABASE_URL += f"{sep}sslmode=require"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT * FROM borrow_records WHERE enrollment_no='24210270242'")
print("borrow_records:", cur.fetchall())
