#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_cloud_borrow_records.py
===========================
Run ONCE to fix the Supabase cloud borrow_records table so that the web
portal (Render) shows correct borrowed / returned / overdue data.

What this script does:
  1. Adds the `accession_no` column to borrow_records on Supabase (if missing)
  2. Backfills accession_no from book_id (extract first number of range,
     e.g. "5-14" -> "5", "12" -> "12")
  3. Deduplicates borrow_records keeping the most recent (highest id) per
     (enrollment_no, accession_no, borrow_date)
  4. Drops the old UNIQUE constraint on (enrollment_no, book_id, borrow_date)
     if it exists, and adds a new one on (enrollment_no, accession_no, borrow_date)
     — this is what sync_manager.py uses for ON CONFLICT.
  5. Also ensures borrow_records.status values are correct (not empty/NULL).

Safe to run multiple times (idempotent).
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    # Try .env in same dir, parent dir, and grandparent dir
    for _rel in ['.', '..', '../..']:
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), _rel, '.env')
        if os.path.exists(_p):
            load_dotenv(_p)
            break
    else:
        load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("DATABASE_URL not set in environment or .env file")
    sys.exit(1)

print(f"Connecting to Supabase...")
try:
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=20, sslmode='require')
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected.\n")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)


def step(num, desc, sql_or_fn, args=None):
    print(f"--- Step {num}: {desc}")
    try:
        if callable(sql_or_fn):
            sql_or_fn()
        else:
            if args:
                cur.execute(sql_or_fn, args)
            else:
                cur.execute(sql_or_fn)
        conn.commit()
        rc = cur.rowcount
        print(f"    Done. rows={rc}\n")
        return True
    except Exception as e:
        conn.rollback()
        err = str(e).lower()
        if 'already exists' in err or 'duplicate' in err or 'does not exist' in err:
            print(f"    Skipped (already applied or not applicable): {e}\n")
            return True
        print(f"    WARNING (non-fatal): {e}\n")
        return False


# ── Step 1: Show current state ────────────────────────────────────────────────
print("=== Current state ===")
try:
    cur.execute("SELECT COUNT(*) as total FROM borrow_records")
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as borrowed FROM borrow_records WHERE status = 'borrowed'")
    borrowed = cur.fetchone()['borrowed']
    cur.execute("SELECT COUNT(*) as returned FROM borrow_records WHERE status = 'returned'")
    returned = cur.fetchone()['returned']
    conn.rollback()
    print(f"  borrow_records: {total} total, {borrowed} borrowed, {returned} returned")
except Exception as e:
    conn.rollback()
    print(f"  Could not read borrow_records: {e}")

# Check if accession_no column exists
try:
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'borrow_records' AND column_name = 'accession_no'
    """)
    has_accession_no = cur.fetchone() is not None
    conn.rollback()
    print(f"  accession_no column exists: {has_accession_no}")
except Exception as e:
    conn.rollback()
    has_accession_no = False
    print(f"  Could not check accession_no: {e}")

# Check existing constraints
try:
    cur.execute("""
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'borrow_records'::regclass AND contype = 'u'
    """)
    constraints = [r['conname'] for r in cur.fetchall()]
    conn.rollback()
    print(f"  Existing UNIQUE constraints: {constraints}")
except Exception as e:
    conn.rollback()
    constraints = []
    print(f"  Could not read constraints: {e}")
print()


# ── Step 2: Add accession_no column ──────────────────────────────────────────
if not has_accession_no:
    step(2, "Add accession_no column to borrow_records",
         "ALTER TABLE borrow_records ADD COLUMN accession_no TEXT")
else:
    print("--- Step 2: accession_no column already exists — skipped.\n")


# ── Step 3: Backfill accession_no from book_id ────────────────────────────────
step(3, "Backfill accession_no from book_id for rows where it is NULL or empty",
     """
     UPDATE borrow_records
     SET accession_no = CASE
         WHEN STRPOS(book_id, '-') > 0
             THEN SPLIT_PART(book_id, '-', 1)
         ELSE book_id
     END
     WHERE accession_no IS NULL OR accession_no = ''
     """)


# ── Step 4: Fix NULL/empty status values ──────────────────────────────────────
step(4, "Fix NULL/empty status — default to 'borrowed'",
     "UPDATE borrow_records SET status = 'borrowed' WHERE status IS NULL OR status = ''")


# ── Step 5: Show duplicate counts before cleanup ──────────────────────────────
print("=== Duplicate counts (before dedup) ===")
try:
    cur.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT (enrollment_no, accession_no, borrow_date))
        AS dupes FROM borrow_records
    """)
    dupes = cur.fetchone()['dupes']
    conn.rollback()
    emoji = "🔴" if dupes > 0 else "🟢"
    print(f"  {emoji} borrow_records duplicates (by enrollment_no+accession_no+borrow_date): {dupes}")
except Exception as e:
    conn.rollback()
    print(f"  Could not count duplicates: {e}")
print()


# ── Step 6: Deduplicate borrow_records (keep highest id = most recent) ────────
step(6, "Deduplicate borrow_records — keep highest id per (enrollment_no, accession_no, borrow_date)",
     """
     DELETE FROM borrow_records
     WHERE id NOT IN (
         SELECT MAX(id)
         FROM borrow_records
         GROUP BY enrollment_no, accession_no, borrow_date
     )
     """)


# ── Step 7: Drop old UNIQUE constraint on (enrollment_no, book_id, borrow_date) ──
# (This was added by the previous run_supabase_migration.py and conflicts with new key)
old_constraints_to_drop = [
    'borrow_records_unique_entry',         # name from run_supabase_migration.py
    'borrow_records_enrollment_book_date', # alternative name
]
for cname in old_constraints_to_drop:
    if cname in constraints:
        step(7, f"Drop old UNIQUE constraint '{cname}'",
             f"ALTER TABLE borrow_records DROP CONSTRAINT IF EXISTS {cname}")


# ── Step 8: Add correct UNIQUE constraint ──────────────────────────────────────
step(8, "Add UNIQUE constraint on borrow_records(enrollment_no, accession_no, borrow_date)",
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


# ── Step 9: Ensure updated_at column exists (needed for delta sync) ────────────
step(9, "Ensure updated_at column exists on borrow_records",
     """
     DO $$
     BEGIN
         IF NOT EXISTS (
             SELECT 1 FROM information_schema.columns
             WHERE table_name = 'borrow_records' AND column_name = 'updated_at'
         ) THEN
             ALTER TABLE borrow_records ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
             UPDATE borrow_records SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;
         END IF;
     END $$;
     """)


# ── Step 10: Ensure books table has updated_at (for delta sync) ───────────────
step(10, "Ensure updated_at column exists on books",
     """
     DO $$
     BEGIN
         IF NOT EXISTS (
             SELECT 1 FROM information_schema.columns
             WHERE table_name = 'books' AND column_name = 'updated_at'
         ) THEN
             ALTER TABLE books ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
             UPDATE books SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;
         END IF;
     END $$;
     """)


# ── Step 11: Reset sync_log so next desktop sync does a full push ──────────────
print("--- Step 11: Reset local sync_log.json so next app startup does a full re-sync")
try:
    import json, datetime
    # Find sync_log.json — same dir as this script
    sync_log_candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync_log.json'),
    ]
    for slp in sync_log_candidates:
        if os.path.exists(slp):
            with open(slp, 'w') as f:
                json.dump({
                    'last_sync': '2000-01-01 00:00:00',
                    'last_successful_sync': '2000-01-01 00:00:00',
                    'status': 'reset_by_migration',
                    'reset_at': datetime.datetime.now().isoformat(),
                }, f, indent=4)
            print(f"    Reset: {slp}\n")
            break
    else:
        print("    sync_log.json not found — no reset needed (first-run state)\n")
except Exception as e:
    print(f"    Could not reset sync_log.json (non-fatal): {e}\n")


# ── Final: Show counts ────────────────────────────────────────────────────────
print("=== Final state ===")
try:
    cur.execute("SELECT COUNT(*) as total FROM borrow_records")
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as borrowed FROM borrow_records WHERE status = 'borrowed'")
    borrowed = cur.fetchone()['borrowed']
    cur.execute("SELECT COUNT(*) as returned FROM borrow_records WHERE status = 'returned'")
    returned = cur.fetchone()['returned']
    cur.execute("SELECT COUNT(*) as null_acc FROM borrow_records WHERE accession_no IS NULL OR accession_no = ''")
    null_acc = cur.fetchone()['null_acc']
    conn.commit()
    print(f"  borrow_records: {total} total, {borrowed} borrowed, {returned} returned")
    print(f"  Rows with NULL/empty accession_no: {null_acc} (should be 0)")
except Exception as e:
    conn.rollback()
    print(f"  Could not read final counts: {e}")

print("\nMigration complete!")
print("\nNEXT STEPS:")
print("  1. Restart the desktop app (main.py) — it will do a full re-push to Supabase")
print("  2. Or manually trigger: Admin > Sync > Force Full Sync")
print("  3. Wait ~30 seconds for sync to complete, then check the web portal")

cur.close()
conn.close()
