import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if 'sslmode' not in DATABASE_URL:
    sep = '&' if '?' in DATABASE_URL else '?'
    DATABASE_URL += f"{sep}sslmode=require"

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Portal tables
pg_sql_statements = [
    '''
        CREATE TABLE IF NOT EXISTS requests (
            req_id SERIAL PRIMARY KEY,
            enrollment_no TEXT,
            request_type TEXT,
            details TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS student_auth (
            enrollment_no TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            is_first_login INTEGER DEFAULT 1,
            last_changed TIMESTAMP
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS notices (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS deletion_requests (
            id SERIAL PRIMARY KEY,
            student_id TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(enrollment_no)
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS user_settings (
            enrollment_no TEXT PRIMARY KEY,
            email TEXT,
            library_alerts INTEGER DEFAULT 0,
            loan_reminders INTEGER DEFAULT 1,
            theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'English',
            data_consent INTEGER DEFAULT 1
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS user_notifications (
            id SERIAL PRIMARY KEY,
            enrollment_no TEXT,
            type TEXT,
            title TEXT,
            message TEXT,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS book_waitlist (
            id SERIAL PRIMARY KEY,
            enrollment_no TEXT NOT NULL,
            book_id TEXT NOT NULL,
            book_title TEXT,
            notified INTEGER DEFAULT 0,
            notified_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(enrollment_no, book_id)
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS access_logs (
            id SERIAL PRIMARY KEY,
            endpoint TEXT,
            method TEXT,
            status INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS study_materials (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            filename TEXT NOT NULL,
            original_filename TEXT,
            file_size INTEGER,
            branch TEXT DEFAULT 'Computer',
            year TEXT NOT NULL,
            category TEXT,
            uploaded_by TEXT DEFAULT 'Library Admin',
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            drive_link TEXT
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS book_wishlist (
            id SERIAL PRIMARY KEY,
            book_id TEXT NOT NULL,
            enrollment_no TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(book_id, enrollment_no)
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS book_ratings (
            id SERIAL PRIMARY KEY,
            book_id TEXT NOT NULL,
            enrollment_no TEXT NOT NULL,
            rating INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(book_id, enrollment_no)
        )
    ''',
    '''
        CREATE TABLE IF NOT EXISTS failed_emails (
            id SERIAL PRIMARY KEY,
            recipient TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            error_msg TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_retry_at TIMESTAMP
        )
    '''
]

for stmt in pg_sql_statements:
    cursor.execute(stmt)

# Waitlist migration (already included notified_at)
# Requests migration (add approved_at)
try:
    cursor.execute("ALTER TABLE requests ADD COLUMN approved_at TEXT")
except Exception:
    pass

conn.commit()
conn.close()
print("Portal tables created successfully in Postgres.")
