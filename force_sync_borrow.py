import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
if 'sslmode' not in DATABASE_URL:
    DATABASE_URL += "&sslmode=require" if "?" in DATABASE_URL else "?sslmode=require"

conn_pg = psycopg2.connect(DATABASE_URL)
cur_pg = conn_pg.cursor()

conn_sl = sqlite3.connect('LibraryApp/library.db')
conn_sl.row_factory = sqlite3.Row
cur_sl = conn_sl.cursor()

cur_sl.execute("SELECT * FROM borrow_records WHERE enrollment_no='24210270242'")
rows = cur_sl.fetchall()

for row in rows:
    data = dict(row)
    # Remove 'id'
    data.pop('id', None)
    
    # Normalize book_id
    if data.get('book_id'):
        data['book_id'] = str(data['book_id']).replace(' ', '')
        
    cols = list(data.keys())
    vals = list(data.values())
    
    placeholders = ', '.join(['%s'] * len(cols))
    cols_str = ', '.join(cols)
    
    query = f"""
        INSERT INTO borrow_records ({cols_str}) 
        VALUES ({placeholders}) 
        ON CONFLICT (enrollment_no, accession_no, borrow_date) 
        DO UPDATE SET 
            status = EXCLUDED.status, 
            return_date = EXCLUDED.return_date, 
            fine = EXCLUDED.fine,
            fine_paid = EXCLUDED.fine_paid,
            fine_paid_at = EXCLUDED.fine_paid_at,
            fine_waived = EXCLUDED.fine_waived,
            renewal_count = EXCLUDED.renewal_count
    """
    try:
        cur_pg.execute(query, vals)
        conn_pg.commit()
        print("Successfully forced borrow record into Postgres!")
    except Exception as e:
        print("Failed to insert:", e)

conn_pg.close()
conn_sl.close()

# Also reset sync_log.json so next sync doesn't skip
import json
log_path = 'LibraryApp/sync_log.json'
try:
    with open(log_path, 'w') as f:
        json.dump({'last_successful_sync': '2000-01-01 00:00:00', 'last_sync': '2000-01-01 00:00:00', 'status': 'completed'}, f)
    print("Reset sync_log.json to 2000-01-01")
except Exception as e:
    print("Error resetting sync log:", e)
