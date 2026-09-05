import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
if 'sslmode' not in DATABASE_URL:
    sep = '&' if '?' in DATABASE_URL else '?'
    DATABASE_URL += f"{sep}sslmode=require"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("INSERT INTO borrow_records (enrollment_no, book_id, borrow_date, due_date, return_date, status, fine, accession_no) VALUES ('24210270242', '1581-1585', '2026-04-01', '2026-04-08', NULL, 'borrowed', 0, '1581')")
    conn.commit()
    print("Insert success")
except Exception as e:
    print("Insert failed:", e)
