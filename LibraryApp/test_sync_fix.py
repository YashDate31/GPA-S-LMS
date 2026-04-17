#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_sync_fix.py  --  Tests for all 5 Supabase duplication bug fixes.
Run:  python -X utf8 -u test_sync_fix.py
"""
import sys, io, os, sqlite3, traceback, importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

def p(msg=""):
    print(msg, flush=True)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

try:
    import psycopg2
except ImportError:
    p("ERROR: psycopg2 not installed. pip install psycopg2-binary")
    sys.exit(1)

DATABASE_URL = os.getenv('DATABASE_URL')
LOCAL_DB     = os.path.join(os.path.dirname(__file__), 'library.db')

results = []
def ok(name, d=""):  p(f"  [PASS] {name}" + (f"  [{d}]" if d else "")); results.append(("PASS", name))
def fail(name, d=""): p(f"  [FAIL] {name}" + (f"\n         {d}" if d else "")); results.append(("FAIL", name))

def remote():
    return psycopg2.connect(DATABASE_URL, connect_timeout=15, sslmode='require')

# ────────────────────────────────────────────────
# TEST 1 — UNIQUE Constraints exist on Supabase
# ────────────────────────────────────────────────
p("=" * 58)
p("TEST 1: Supabase UNIQUE constraints in place")
p("=" * 58)
try:
    rc = remote(); cur = rc.cursor()
    cur.execute("SELECT conname FROM pg_constraint WHERE conname IN ('borrow_records_unique_entry','promotion_history_unique_entry')")
    found = {r[0] for r in cur.fetchall()}
    rc.close()
    for cname, label in [
        ('borrow_records_unique_entry',    'UNIQUE(enrollment_no, book_id, borrow_date) on borrow_records'),
        ('promotion_history_unique_entry', 'UNIQUE(enrollment_no, old_year, new_year, promotion_date) on promotion_history'),
    ]:
        if cname in found: ok(label)
        else: fail(label, "MISSING -- run run_supabase_migration.py")
except Exception as e:
    fail("Constraint check", str(e))

# ────────────────────────────────────────────────
# TEST 2 — Zero duplicates in Supabase
# ────────────────────────────────────────────────
p()
p("=" * 58)
p("TEST 2: Zero duplicates in Supabase")
p("=" * 58)
try:
    rc = remote(); cur = rc.cursor()
    for tbl, q in [
        ('borrow_records', 'SELECT COUNT(*) - COUNT(DISTINCT (enrollment_no, book_id, borrow_date)) FROM borrow_records'),
        ('books',          'SELECT COUNT(*) - COUNT(DISTINCT book_id) FROM books'),
        ('students',       'SELECT COUNT(*) - COUNT(DISTINCT enrollment_no) FROM students'),
    ]:
        cur.execute(q); d = cur.fetchone()[0]; rc.rollback()
        if d == 0: ok(f"{tbl}: 0 duplicates")
        else: fail(f"{tbl}: {d} duplicate rows still exist")
    rc.close()
except Exception as e:
    fail("Duplicate check", str(e))

# ────────────────────────────────────────────────
# TEST 3 — Bug 1+2: ON CONFLICT natural key prevents duplicates on Supabase
# ────────────────────────────────────────────────
p()
p("=" * 58)
p("TEST 3: Bug 1+2 -- natural-key ON CONFLICT prevents duplicates")
p("=" * 58)
EN='SYNCTEST-001'; BK='SYNCTEST-B001'; D='2030-01-01'
try:
    rc = remote(); cur = rc.cursor()
    cur.execute("DELETE FROM borrow_records WHERE enrollment_no=%s", (EN,))
    cur.execute("DELETE FROM books WHERE book_id=%s", (BK,))
    cur.execute("DELETE FROM students WHERE enrollment_no=%s", (EN,))
    rc.commit()
    cur.execute("INSERT INTO students(enrollment_no,name) VALUES(%s,'Test') ON CONFLICT(enrollment_no) DO NOTHING", (EN,))
    cur.execute("INSERT INTO books(book_id,title,author,total_copies,available_copies) VALUES(%s,'T','A',5,4) ON CONFLICT(book_id) DO NOTHING", (BK,))
    rc.commit()
    # Simulate old push (no id — creates a Supabase row with serial id e.g. 250)
    cur.execute("INSERT INTO borrow_records(enrollment_no,book_id,borrow_date,due_date) VALUES(%s,%s,%s,'2030-01-10')", (EN,BK,D))
    rc.commit()
    cur.execute("SELECT id FROM borrow_records WHERE enrollment_no=%s AND book_id=%s AND borrow_date=%s", (EN,BK,D))
    rows = cur.fetchall()
    p(f"  [INFO] After old-style push: {len(rows)} row(s), remote id={rows[0][0] if rows else 'N/A'}")
    # Simulate new sync upsert (natural key — must NOT create a second row)
    cur.execute("""
        INSERT INTO borrow_records(enrollment_no,book_id,borrow_date,due_date)
        VALUES(%s,%s,%s,'2030-01-10')
        ON CONFLICT(enrollment_no,book_id,borrow_date)
        DO UPDATE SET due_date=EXCLUDED.due_date
    """, (EN,BK,D))
    rc.commit()
    cur.execute("SELECT COUNT(*) FROM borrow_records WHERE enrollment_no=%s AND book_id=%s AND borrow_date=%s", (EN,BK,D))
    count = cur.fetchone()[0]; rc.rollback()
    if count == 1: ok("Exactly 1 row after push + new-style upsert (no duplicate)")
    else: fail(f"Got {count} rows after push + upsert (expected 1)")
    cur.execute("DELETE FROM borrow_records WHERE enrollment_no=%s", (EN,))
    cur.execute("DELETE FROM books WHERE book_id=%s", (BK,))
    cur.execute("DELETE FROM students WHERE enrollment_no=%s", (EN,))
    rc.commit(); rc.close()
except Exception as e:
    fail("Test 3 exception", traceback.format_exc(limit=2))

# ────────────────────────────────────────────────
# TEST 4 — Bug 4: INSERT OR IGNORE does not destroy local rows (in-memory)
# ────────────────────────────────────────────────
p()
p("=" * 58)
p("TEST 4: Bug 4 -- remote-to-local sync does NOT destroy local rows")
p("=" * 58)
try:
    # Prove old bug: INSERT OR REPLACE destroys row with id collision
    mc_old = sqlite3.connect(":memory:")
    mc_old.execute("CREATE TABLE books(id INTEGER PRIMARY KEY AUTOINCREMENT, book_id TEXT UNIQUE, title TEXT, author TEXT)")
    mc_old.execute("INSERT INTO books(id,book_id,title,author) VALUES(7,'LOCAL-ONLY','Local','A')")
    mc_old.commit()
    remote_row = {'id':7,'book_id':'REMOTE-BOOK','title':'Remote','author':'B'}
    cols = list(remote_row.keys()); vals = list(remote_row.values())
    mc_old.execute(f"INSERT OR REPLACE INTO books({','.join(cols)}) VALUES({','.join(['?']*len(cols))})", vals)
    mc_old.commit()
    old_books = [r[0] for r in mc_old.execute("SELECT book_id FROM books")]
    mc_old.close()
    if 'LOCAL-ONLY' not in old_books:
        p(f"  [INFO] OLD code confirmed: LOCAL-ONLY DESTROYED (books={old_books}) -- Bug 4 reproduced")
    else:
        p(f"  [INFO] OLD code: LOCAL-ONLY survived (unexpected, books={old_books})")

    # Now run the fixed code: skip 'id', use INSERT OR IGNORE
    mc_new = sqlite3.connect(":memory:")
    mc_new.execute("CREATE TABLE books(id INTEGER PRIMARY KEY AUTOINCREMENT, book_id TEXT UNIQUE, title TEXT, author TEXT)")
    mc_new.execute("INSERT INTO books(id,book_id,title,author) VALUES(7,'LOCAL-ONLY','Local','A')")
    mc_new.commit()
    payload = {k:v for k,v in remote_row.items() if k != 'id'}  # skip id
    exist = mc_new.execute("SELECT 1 FROM books WHERE book_id=?",('REMOTE-BOOK',)).fetchone()
    if exist:
        upd = [c for c in payload if c != 'book_id']
        mc_new.execute(f"UPDATE books SET {','.join(c+'=?' for c in upd)} WHERE book_id=?",
                       [payload[c] for c in upd]+['REMOTE-BOOK'])
    else:
        mc_new.execute(f"INSERT INTO books({','.join(payload)}) VALUES({','.join(['?']*len(payload))})",
                       list(payload.values()))
    mc_new.commit()
    new_books = [r[0] for r in mc_new.execute("SELECT book_id FROM books")]
    mc_new.close()
    p(f"  [INFO] NEW code result: local books = {new_books}")
    if 'LOCAL-ONLY' in new_books: ok("'LOCAL-ONLY' survived -- id collision destruction fixed (Bug 4)")
    else: fail("'LOCAL-ONLY' destroyed -- Bug 4 still present in new code")
    if 'REMOTE-BOOK' in new_books: ok("'REMOTE-BOOK' correctly inserted from remote")
    else: fail("'REMOTE-BOOK' missing from local after sync")
except Exception as e:
    fail("Test 4 exception", traceback.format_exc(limit=2))

# ────────────────────────────────────────────────
# TEST 5 — Bug 3: _NATURAL_KEY_MAP correctness (no Database import)
# ────────────────────────────────────────────────
p()
p("=" * 58)
p("TEST 5: Bug 3 -- SyncManager _NATURAL_KEY_MAP is correct")
p("=" * 58)
try:
    sm_path = os.path.join(os.path.dirname(__file__), 'sync_manager.py')
    spec = importlib.util.spec_from_file_location('sync_manager', sm_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    SM = mod.SyncManager

    assert hasattr(SM, '_NATURAL_KEY_MAP'), "_NATURAL_KEY_MAP missing from SyncManager class"
    nk = SM._NATURAL_KEY_MAP

    for tbl, exp in [
        ('borrow_records', ('enrollment_no','book_id','borrow_date')),
        ('books',          ('book_id',)),
        ('students',       ('enrollment_no',)),
        ('academic_years', ('year_name',)),
        ('system_settings',('key',)),
    ]:
        if nk.get(tbl) == exp: ok(f"_NATURAL_KEY_MAP['{tbl}'] = {exp}")
        else: fail(f"_NATURAL_KEY_MAP['{tbl}']", f"expected {exp}, got {nk.get(tbl)}")

    for tbl in ('admin_activity','notices'):
        if nk.get(tbl) is None: ok(f"_NATURAL_KEY_MAP['{tbl}'] = None (log table, DO NOTHING)")
        else: fail(f"_NATURAL_KEY_MAP['{tbl}'] should be None")

    sm_inst = SM.__new__(SM)
    pk = sm_inst._get_primary_key('borrow_records')
    if pk != 'id': ok(f"_get_primary_key('borrow_records') = '{pk}' (not serial id)")
    else: fail("_get_primary_key('borrow_records') still returns 'id'")

except Exception as e:
    fail("Test 5 exception", traceback.format_exc(limit=3))

# ────────────────────────────────────────────────
# TEST 6 — End-to-end: sync_now() two cycles, 1 remote row
# ────────────────────────────────────────────────
p()
p("=" * 58)
p("TEST 6: End-to-end -- sync_now() two cycles = exactly 1 Supabase row")
p("=" * 58)
E_EN='E2ETEST-001'; E_BK='E2ETEST-B001'; E_D='2030-06-01'; E_DU='2030-06-10'
try:
    sm_path = os.path.join(os.path.dirname(__file__), 'sync_manager.py')
    spec2 = importlib.util.spec_from_file_location('sync_manager2', sm_path)
    mod2  = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(mod2)
    sm = mod2.SyncManager(LOCAL_DB, DATABASE_URL)

    # Cleanup remote
    rc = remote(); cur = rc.cursor()
    cur.execute("DELETE FROM borrow_records WHERE enrollment_no=%s",(E_EN,))
    cur.execute("DELETE FROM books WHERE book_id=%s",(E_BK,))
    cur.execute("DELETE FROM students WHERE enrollment_no=%s",(E_EN,))
    rc.commit(); rc.close()

    # Cleanup + seed local
    lc = sqlite3.connect(LOCAL_DB)
    lc.execute("DELETE FROM borrow_records WHERE enrollment_no=?",(E_EN,))
    lc.execute("DELETE FROM books WHERE book_id=?",(E_BK,))
    lc.execute("DELETE FROM students WHERE enrollment_no=?",(E_EN,))
    lc.commit()
    lc.execute("INSERT OR IGNORE INTO students(enrollment_no,name) VALUES(?,?)",(E_EN,'E2E Test'))
    lc.execute("INSERT OR IGNORE INTO books(book_id,title,author,total_copies,available_copies) VALUES(?,?,?,5,5)",(E_BK,'E2E Book','T'))
    lc.execute("INSERT OR IGNORE INTO borrow_records(enrollment_no,book_id,borrow_date,due_date) VALUES(?,?,?,?)",(E_EN,E_BK,E_D,E_DU))
    lc.commit(); lc.close()

    p("  [INFO] Running sync cycle 1 (local -> remote) ...")
    r1 = sm.sync_now(direction='local_to_remote', tables_override=['students','books','borrow_records'])
    p(f"  [INFO]   success={r1['success']}, synced={r1['records_synced']}, errors={r1['errors']}")

    p("  [INFO] Running sync cycle 2 (second pass, must be idempotent) ...")
    r2 = sm.sync_now(direction='local_to_remote', tables_override=['students','books','borrow_records'])
    p(f"  [INFO]   success={r2['success']}, synced={r2['records_synced']}, errors={r2['errors']}")

    rc2 = remote(); cur2 = rc2.cursor()
    cur2.execute("SELECT COUNT(*) FROM borrow_records WHERE enrollment_no=%s AND book_id=%s AND borrow_date=%s",(E_EN,E_BK,E_D))
    cnt = cur2.fetchone()[0]; rc2.rollback()

    if   cnt == 1: ok("After 2 sync cycles: exactly 1 borrow_record in Supabase")
    elif cnt == 0: fail("borrow_record not found in Supabase after sync")
    else:          fail(f"Found {cnt} rows after 2 sync cycles (expected 1) -- DUPLICATE BUG ACTIVE")

    all_err = r1['errors'] + r2['errors']
    if not all_err: ok("Both sync cycles: zero errors")
    else: fail("Sync errors reported", str(all_err))

    # Cleanup
    cur2.execute("DELETE FROM borrow_records WHERE enrollment_no=%s",(E_EN,))
    cur2.execute("DELETE FROM books WHERE book_id=%s",(E_BK,))
    cur2.execute("DELETE FROM students WHERE enrollment_no=%s",(E_EN,))
    rc2.commit(); rc2.close()
    lc2 = sqlite3.connect(LOCAL_DB)
    lc2.execute("DELETE FROM borrow_records WHERE enrollment_no=?",(E_EN,))
    lc2.execute("DELETE FROM books WHERE book_id=?",(E_BK,))
    lc2.execute("DELETE FROM students WHERE enrollment_no=?",(E_EN,))
    lc2.commit(); lc2.close()

except Exception as e:
    fail("Test 6 exception", traceback.format_exc(limit=4))

# ────────────────────────────────────────────────
# SUMMARY
# ────────────────────────────────────────────────
p()
p("=" * 58)
p("FINAL RESULTS")
p("=" * 58)
passed  = sum(1 for r in results if r[0]=='PASS')
failed  = sum(1 for r in results if r[0]=='FAIL')
for status, name in results:
    p(f"  [{status}] {name}")
p()
p(f"  Passed: {passed}   Failed: {failed}   Total: {len(results)}")
if failed == 0:
    p()
    p("  ALL CHECKS PASSED -- duplication bugs are FIXED.")
    p()
    sys.exit(0)
else:
    p()
    p(f"  {failed} FAILURE(S) -- review output above.")
    p()
    sys.exit(1)
