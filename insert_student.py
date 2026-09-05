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
cur.execute("INSERT INTO students (enrollment_no, name, email, phone, department, year, date_registered) VALUES ('24210270242', 'Ganesh Jadhav', 'ganesh@gamil.com', '7975256898', 'Computer Engineering', '3rd', '2026-06-23') ON CONFLICT DO NOTHING")
conn.commit()
print("Student manually added!")
