import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if 'sslmode' not in DATABASE_URL:
    sep = '&' if '?' in DATABASE_URL else '?'
    DATABASE_URL += f"{sep}sslmode=require"

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

# Missing Library Tables
pg_sql_statements = [
    '''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            enrollment_no TEXT NOT NULL,
            book_id TEXT NOT NULL,
            borrow_date DATE NOT NULL,
            due_date DATE NOT NULL,
            return_date DATE,
            fine INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (enrollment_no) REFERENCES students(enrollment_no),
            FOREIGN KEY (book_id) REFERENCES books(book_id)
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS promotion_history (
            id SERIAL PRIMARY KEY,
            enrollment_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            old_year TEXT NOT NULL,
            new_year TEXT NOT NULL,
            letter_number TEXT,
            academic_year TEXT,
            promotion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (enrollment_no) REFERENCES students (enrollment_no) ON DELETE RESTRICT ON UPDATE CASCADE
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS academic_years (
            id SERIAL PRIMARY KEY,
            year_name TEXT UNIQUE NOT NULL,
            start_date DATE,
            end_date DATE,
            is_active INTEGER DEFAULT 0,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''
]

for stmt in pg_sql_statements:
    cursor.execute(stmt)

# Add missing updated_at columns
for table in ['students', 'books', 'borrow_records', 'admin_activity', 'system_settings', 'transactions']:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except Exception as e:
        pass  # Already exists
        
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN synced_remote INTEGER DEFAULT 0")
    except Exception as e:
        pass

# Fix sync_deletions
try:
    cursor.execute("ALTER TABLE sync_deletions ADD COLUMN source TEXT DEFAULT 'desktop'")
except Exception:
    pass

try:
    cursor.execute("ALTER TABLE sync_deletions ADD COLUMN pk_value TEXT")
    cursor.execute("UPDATE sync_deletions SET pk_value = record_id WHERE pk_value IS NULL")
except Exception:
    pass

conn.commit()
conn.close()
print("Missing library tables created successfully in Postgres.")
