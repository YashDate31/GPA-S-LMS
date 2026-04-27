#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supabase Migration Script - Run once before deploying the sync fix.

This script:
1. Removes existing duplicate rows in borrow_records, books, students
2. Adds UNIQUE constraints needed by the new ON CONFLICT syntax in sync_manager.py

Safe to run multiple times (IF NOT EXISTS / dedup is idempotent).
"""
import sys, io
# Force UTF-8 output on Windows so print() doesn't crash on non-cp1252 chars
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import sys
from urllib.parse import urlparse, unquote

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not set in .env")
    sys.exit(1)

print(f"🔗 Connecting to Supabase...")
try:
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=15, sslmode='require')
    conn.autocommit = False
    cur = conn.cursor()
    print("✅ Connected.\n")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

def run_step(step_num, description, sql):
    print(f"--- Step {step_num}: {description}")
    try:
        cur.execute(sql)
        affected = cur.rowcount
        conn.commit()
        if affected >= 0:
            print(f"    ✅ Done. Rows affected: {affected}\n")
        else:
            print(f"    ✅ Done.\n")
        return True
    except Exception as e:
        conn.rollback()
        # Ignore "already exists" constraint errors gracefully
        err_str = str(e).lower()
        if 'already exists' in err_str or 'duplicate' in err_str:
            print(f"    ℹ️  Skipped (already exists): {e}\n")
            return True
        print(f"    ⚠️  Error (non-fatal, continuing): {e}\n")
        return False

# ============================================================
# STEP 1: Count duplicates before cleanup
# ============================================================
print("=== Pre-migration duplicate counts ===")
checks = {
    'borrow_records': "SELECT COUNT(*) - COUNT(DISTINCT (enrollment_no, book_id, borrow_date)) FROM borrow_records",
    'books':          "SELECT COUNT(*) - COUNT(DISTINCT book_id) FROM books",
    'students':       "SELECT COUNT(*) - COUNT(DISTINCT enrollment_no) FROM students",
}
for table, query in checks.items():
    try:
        cur.execute(query)
        dupes = cur.fetchone()[0]
        conn.rollback()
        emoji = "🔴" if dupes > 0 else "🟢"
        print(f"  {emoji} {table}: {dupes} duplicate rows")
    except Exception as e:
        conn.rollback()
        print(f"  ⚠️  Could not check {table}: {e}")
print()

# ============================================================
# STEP 1b: Add accession_no column if missing
# (sync_manager.py uses (enrollment_no, accession_no, borrow_date) as natural key)
# ============================================================
run_step('1b', "Add accession_no column to borrow_records (if missing)",
"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'borrow_records' AND column_name = 'accession_no'
    ) THEN
        ALTER TABLE borrow_records ADD COLUMN accession_no TEXT;
    END IF;
END $$;
""")

# Backfill accession_no from book_id
run_step('1c', "Backfill accession_no from book_id (extract first number of range)",
"""
UPDATE borrow_records
SET accession_no = CASE
    WHEN STRPOS(book_id, '-') > 0
        THEN SPLIT_PART(book_id, '-', 1)
    ELSE book_id
END
WHERE accession_no IS NULL OR accession_no = ''
""")

# ============================================================
# STEP 2: Deduplicate borrow_records
# ============================================================
run_step(1, "Remove duplicate borrow_records (keep lowest id per enrollment_no+accession_no+borrow_date)",
"""
DELETE FROM borrow_records
WHERE id NOT IN (
    SELECT MIN(id)
    FROM borrow_records
    GROUP BY enrollment_no, accession_no, borrow_date
)
""")

# ============================================================
# STEP 3: Deduplicate books
# ============================================================
run_step(2, "Remove duplicate books (keep lowest id per book_id)",
"""
DELETE FROM books
WHERE id NOT IN (
    SELECT MIN(id)
    FROM books
    GROUP BY book_id
)
""")

# ============================================================
# STEP 4: Deduplicate students
# ============================================================
run_step(3, "Remove duplicate students (keep lowest id per enrollment_no)",
"""
DELETE FROM students
WHERE id NOT IN (
    SELECT MIN(id)
    FROM students
    GROUP BY enrollment_no
)
""")

# ============================================================
# STEP 5: Deduplicate promotion_history
# ============================================================
run_step(4, "Remove duplicate promotion_history rows",
"""
DELETE FROM promotion_history
WHERE id NOT IN (
    SELECT MIN(id)
    FROM promotion_history
    GROUP BY enrollment_no, old_year, new_year, promotion_date
)
""")

# ============================================================
# STEP 6: Add correct UNIQUE constraint on borrow_records
# sync_manager.py uses ON CONFLICT (enrollment_no, accession_no, borrow_date)
# ============================================================
run_step(5, "Drop old UNIQUE constraint (enrollment_no, book_id, borrow_date) if it exists",
"""
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'borrow_records'::regclass
          AND conname = 'borrow_records_unique_entry'
    ) THEN
        ALTER TABLE borrow_records DROP CONSTRAINT borrow_records_unique_entry;
    END IF;
END $$;
""")

run_step('5b', "Add correct UNIQUE constraint on borrow_records(enrollment_no, accession_no, borrow_date)",
"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'borrow_records'::regclass
          AND conname = 'borrow_records_unique_accession_entry'
    ) THEN
        ALTER TABLE borrow_records
        ADD CONSTRAINT borrow_records_unique_accession_entry
        UNIQUE (enrollment_no, accession_no, borrow_date);
    END IF;
END $$;
""")

# ============================================================
# STEP 7: Add UNIQUE constraint on promotion_history
# ============================================================
run_step(6, "Add UNIQUE constraint on promotion_history(enrollment_no, old_year, new_year, promotion_date)",
"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'promotion_history_unique_entry'
    ) THEN
        ALTER TABLE promotion_history
        ADD CONSTRAINT promotion_history_unique_entry
        UNIQUE (enrollment_no, old_year, new_year, promotion_date);
    END IF;
END $$;
""")

# ============================================================
# STEP 9: Add missing columns to borrow_records
# (Referenced by student_portal.py but never added to Supabase)
# ============================================================
for col_step, col_desc, col_sql in [
    ('9a', 'Add fine_paid to borrow_records',
     "ALTER TABLE borrow_records ADD COLUMN fine_paid INTEGER DEFAULT 0"),
    ('9b', 'Add fine_paid_at to borrow_records',
     "ALTER TABLE borrow_records ADD COLUMN fine_paid_at TEXT"),
    ('9c', 'Add fine_waived to borrow_records',
     "ALTER TABLE borrow_records ADD COLUMN fine_waived INTEGER DEFAULT 0"),
    ('9d', 'Add renewal_count to borrow_records',
     "ALTER TABLE borrow_records ADD COLUMN renewal_count INTEGER DEFAULT 0"),
    ('9e', 'Add fine_rate_at_borrow to borrow_records',
     "ALTER TABLE borrow_records ADD COLUMN fine_rate_at_borrow INTEGER"),
]:
    run_step(col_step, col_desc, f"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'borrow_records' AND column_name = '{col_sql.split('ADD COLUMN ')[1].split(' ')[0]}'
    ) THEN
        {col_sql};
    END IF;
END $$;
""")

# ============================================================
# STEP 10: Add missing columns to other tables
# ============================================================
for col_step, col_desc, tbl, col_name, col_def in [
    ('10a', 'Add notified_at to book_waitlist',
     'book_waitlist', 'notified_at', 'TEXT'),
    ('10b', 'Add approved_at to requests',
     'requests', 'approved_at', 'TEXT'),
    ('10c', 'Add drive_link to study_materials',
     'study_materials', 'drive_link', 'TEXT'),
]:
    run_step(col_step, col_desc, f"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = '{tbl}' AND column_name = '{col_name}'
    ) THEN
        ALTER TABLE {tbl} ADD COLUMN {col_name} {col_def};
    END IF;
END $$;
""")

# ============================================================
# STEP 11: Create failed_emails table
# (Used by student_portal.py for email failure retry tracking)
# ============================================================
run_step(11, "Create failed_emails table",
"""
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
""")

# ============================================================
# STEP 12: Create sync_conflicts table
# (Used by sync_manager.py for conflict visibility)
# ============================================================
run_step(12, "Create sync_conflicts table",
"""
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    natural_key TEXT NOT NULL,
    local_updated_at TEXT,
    remote_updated_at TEXT,
    direction TEXT DEFAULT 'remote_to_local',
    resolved TEXT DEFAULT 'local_wins',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ============================================================
# STEP 13: Post-migration duplicate counts
# ============================================================
print("=== Post-migration duplicate counts ===")
for table, query in checks.items():
    try:
        cur.execute(query)
        dupes = cur.fetchone()[0]
        conn.rollback()
        emoji = "🔴" if dupes > 0 else "🟢"
        print(f"  {emoji} {table}: {dupes} duplicate rows remaining")
    except Exception as e:
        conn.rollback()
        print(f"  ⚠️  Could not check {table}: {e}")

print("\n✅ Migration complete.")
cur.close()
conn.close()
