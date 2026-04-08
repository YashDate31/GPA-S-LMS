#!/usr/bin/env python3
"""
Clear all LMS data from local SQLite databases and Supabase PostgreSQL.
Preserves schema, removes only rows.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def _load_env(repo_root: Path) -> None:
    env_path = repo_root / ".env"

    try:
        from dotenv import load_dotenv  # type: ignore
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()
    except Exception:
        pass

    if env_path.exists():
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        except Exception:
            pass


def _wipe_sqlite(db_path: Path, label: str) -> tuple[bool, str]:
    if not db_path.exists():
        return False, f"{label}: not found at {db_path}"

    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = OFF;")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cur.fetchall()]

        for t in tables:
            cur.execute(f'DELETE FROM "{t}"')

        conn.commit()
        cur.execute("PRAGMA foreign_keys = ON;")
        return True, f"{label}: cleared {len(tables)} tables"
    except Exception as e:
        return False, f"{label}: failed - {e}"
    finally:
        conn.close()


def _wipe_supabase() -> tuple[bool, str]:
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        return False, "Supabase: DATABASE_URL is missing"

    try:
        import psycopg2  # type: ignore
    except Exception as e:
        return False, f"Supabase: psycopg2 missing - {e}"

    target_tables = [
        "borrow_records",
        "books",
        "students",
        "admin_activity",
        "academic_years",
        "promotion_history",
        "requests",
        "deletion_requests",
        "student_auth",
        "notices",
        "password_reset_requests",
        "study_materials",
        "email_queue",
        "email_history",
    ]

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            """
        )
        existing = {r[0] for r in cur.fetchall()}
        to_clear = [t for t in target_tables if t in existing]

        if not to_clear:
            return True, "Supabase: no target tables found"

        cleared = 0
        for t in to_clear:
            try:
                cur.execute(f'TRUNCATE TABLE "public"."{t}" RESTART IDENTITY CASCADE')
                cleared += 1
            except Exception:
                try:
                    cur.execute(f'DELETE FROM "public"."{t}"')
                    cleared += 1
                except Exception:
                    continue

        return True, f"Supabase: cleared {cleared} tables"
    except Exception as e:
        return False, f"Supabase: failed - {e}"
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def main() -> int:
    script_path = Path(__file__).resolve()
    library_app_dir = script_path.parent
    repo_root = library_app_dir.parent

    _load_env(repo_root)

    local_library_db = library_app_dir / "library.db"
    local_portal_db = library_app_dir / "Web-Extension" / "portal.db"

    print("=== CLEAR ALL DATA (LOCAL + SUPABASE) ===")

    ok1, msg1 = _wipe_sqlite(local_library_db, "Local library.db")
    print(msg1)

    ok2, msg2 = _wipe_sqlite(local_portal_db, "Local portal.db")
    print(msg2)

    ok3, msg3 = _wipe_supabase()
    print(msg3)

    if ok1 and ok2 and ok3:
        print("DONE: Local + Supabase data cleared.")
        return 0

    print("PARTIAL/FAILED: Please review messages above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
