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
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'borrow_records'")
print("Columns:", cur.fetchall())
cur.execute("SELECT constraint_name, constraint_type FROM information_schema.table_constraints WHERE table_name = 'borrow_records'")
print("Constraints:", cur.fetchall())

try:
    cur.execute("SELECT indexdef FROM pg_indexes WHERE tablename = 'borrow_records'")
    print("Indexes:", cur.fetchall())
except:
    pass
