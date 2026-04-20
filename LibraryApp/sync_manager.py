#!/usr/bin/env python3
"""
Database Synchronization Manager
Syncs data between local SQLite and remote PostgreSQL databases
"""

import os
import json
import sqlite3

# Load .env if available (for DATABASE_URL)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        load_dotenv()
except ImportError:
    pass

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None
from datetime import datetime
import threading
import time

class SyncManager:
    """Manages bidirectional sync between local and remote databases"""
    
    def __init__(self, local_db_path, remote_config):
        self.local_db_path = local_db_path
        self.remote_config = remote_config
        self.sync_log_path = os.path.join(os.path.dirname(local_db_path), 'sync_log.json')
        self.is_syncing = False
        self._sync_lock = threading.Lock()
        self.last_sync_time = self._load_last_sync_time()
        # Adaptive retry/backoff state for unstable networks/cloud outages
        self.consecutive_failures = 0
        self.last_error = None
        self.backoff_base_seconds = 30
        self.backoff_max_seconds = 15 * 60
        # Schema cache: avoid repeated information_schema queries on every sync cycle
        self._schema_cache = set()  # tables already ensured this session

    def _compute_backoff_seconds(self):
        """Exponential backoff capped at backoff_max_seconds."""
        if self.consecutive_failures <= 0:
            return 0
        # 30s, 60s, 120s, 240s... capped
        return min(self.backoff_max_seconds, self.backoff_base_seconds * (2 ** (self.consecutive_failures - 1)))

    def _register_sync_success(self):
        self.consecutive_failures = 0
        self.last_error = None

    def _register_sync_failure(self, err_msg):
        self.consecutive_failures += 1
        self.last_error = str(err_msg)
        
    def _load_last_sync_time(self):
        """Load last sync timestamp from log"""
        if os.path.exists(self.sync_log_path):
            try:
                with open(self.sync_log_path, 'r') as f:
                    data = json.load(f)
                    return data.get('last_sync', '2000-01-01 00:00:00')
            except:
                pass
        return '2000-01-01 00:00:00'
    
    def _save_sync_time(self, status='completed'):
        """Save current sync timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.sync_log_path, 'w') as f:
                json.dump({
                    'last_sync': timestamp,
                    'status': status
                }, f, indent=4)
            if status in ('completed', 'completed_with_errors'):
                self.last_sync_time = timestamp
        except Exception as e:
            print(f"Error saving sync time: {e}")
    
    def _mark_sync_in_progress(self):
        """Mark sync as in progress"""
        try:
            with open(self.sync_log_path, 'w') as f:
                json.dump({
                    'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'in_progress'
                }, f, indent=4)
        except Exception as e:
            print(f"Error marking sync in progress: {e}")

    def _get_sync_cutoff(self):
        """Return the last successful sync timestamp string for incremental sync queries."""
        try:
            cutoff = datetime.strptime(self.last_sync_time, '%Y-%m-%d %H:%M:%S')
            if cutoff.year <= 2000:
                return None
            return cutoff.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    def _ensure_remote_table_columns(self, local_conn, remote_conn, table_name):
        """Add missing remote columns so cloud sync can accept the local schema.

        Cached per SyncManager lifetime: only runs the expensive information_schema
        queries once per table, not on every sync cycle.
        """
        if table_name in self._schema_cache:
            return  # Already checked this session — skip the expensive query
        try:
            remote_cursor = remote_conn.cursor()

            remote_cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, (table_name,))
            if not remote_cursor.fetchone()[0]:
                # Only auto-create the shared runtime settings table here; the
                # remaining core tables are expected to exist already.
                if table_name == 'system_settings':
                    remote_cursor.execute("""
                        CREATE TABLE IF NOT EXISTS system_settings (
                            key TEXT PRIMARY KEY,
                            value TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    remote_conn.commit()
                return

            local_cursor = local_conn.cursor()
            local_cursor.execute(f"PRAGMA table_info({table_name})")
            local_columns = local_cursor.fetchall()
            if not local_columns:
                return

            remote_cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s
            """, (table_name,))
            remote_columns = {str(row[0]).lower() for row in remote_cursor.fetchall()}

            primary_key = self._get_primary_key(table_name).lower()
            added_any = False

            for col in local_columns:
                col_name = str(col[1])
                col_name_lower = col_name.lower()
                if col_name_lower in remote_columns:
                    continue
                if col_name_lower == primary_key:
                    continue

                col_type = str(col[2] or '').strip().upper() or 'TEXT'
                if col_name_lower == 'updated_at':
                    col_def = 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                else:
                    col_def = col_type

                try:
                    remote_cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}')
                    if col_name_lower == 'updated_at':
                        try:
                            remote_cursor.execute(
                                f'UPDATE {table_name} SET {col_name} = CURRENT_TIMESTAMP WHERE {col_name} IS NULL'
                            )
                        except Exception:
                            pass
                    added_any = True
                except Exception as e:
                    print(f"[Schema Sync] Could not add {table_name}.{col_name}: {e}")

            if added_any:
                remote_conn.commit()
            self._schema_cache.add(table_name)  # Cache: skip this table next sync cycle
        except Exception as e:
            print(f"[Schema Sync] Failed for {table_name}: {e}")
    
    def sync_now(self, direction='both', progress_callback=None, tables_override=None):
        """
        Perform synchronization with graceful interruption handling
        
        Args:
            direction: 'local_to_remote', 'remote_to_local', or 'both'
            progress_callback: Function to call with progress updates
        
        Returns:
            Dictionary with sync statistics
        """
        with self._sync_lock:
            if self.is_syncing:
                return {'success': False, 'error': 'Sync already in progress', 'records_synced': 0}
            self.is_syncing = True

        self._mark_sync_in_progress()  # Mark as in progress
        results = {
            'success': False,
            'direction': direction,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tables_synced': [],
            'records_synced': 0,
            'errors': []
        }

        local_conn = None
        remote_conn = None

        try:
            if psycopg2 is None:
                results['errors'].append(
                    "Remote sync requires 'psycopg2'. Install it (e.g., psycopg2-binary) and restart the app."
                )
                self._register_sync_failure(results['errors'][-1])
                self._save_sync_time(status='failed')
                return results

            local_conn = sqlite3.connect(self.local_db_path)
            # Enable WAL so the sync thread (long-lived connection) doesn't block
            # the UI thread's short read/write connections during book issue/return.
            local_conn.execute('PRAGMA journal_mode=WAL')
            local_conn.execute('PRAGMA busy_timeout = 10000')  # 10s retry
            local_conn.row_factory = sqlite3.Row
            # Fast failure on network problems + keepalive for unstable links
            remote_conn = psycopg2.connect(
                self.remote_config,
                connect_timeout=8,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=3,
            )
            
            # Library tables (bidirectional sync)
            default_tables_to_sync = ['students', 'books', 'borrow_records', 'admin_activity', 'academic_years', 'promotion_history', 'system_settings']
            default_portal_tables_pull = ['requests', 'deletion_requests', 'student_auth', 'book_wishlist', 'book_ratings']
            default_portal_tables_push = ['notices', 'student_auth', 'book_wishlist', 'book_ratings']

            if tables_override:
                requested = set(tables_override)
                tables_to_sync = [t for t in default_tables_to_sync if t in requested]
                portal_tables_pull = [t for t in default_portal_tables_pull if t in requested]
                portal_tables_push = [t for t in default_portal_tables_push if t in requested]
            else:
                tables_to_sync = default_tables_to_sync
                portal_tables_pull = default_portal_tables_pull
                portal_tables_push = default_portal_tables_push

            # Sync deletions ONCE before any table upserts so deleted rows don't reappear.
            try:
                self._ensure_sync_deletions_tables(local_conn, remote_conn)
                if direction in ['local_to_remote', 'both']:
                    self._sync_deletions_local_to_remote(local_conn, remote_conn, allowed_tables=tables_to_sync)
                if direction in ['remote_to_local', 'both']:
                    self._sync_deletions_remote_to_local(local_conn, remote_conn, allowed_tables=tables_to_sync)
            except Exception as e:
                # Deletion sync should not hard-fail the entire sync cycle.
                print(f"[Sync Deletions] Warning: {e}")
            
            for idx, table in enumerate(tables_to_sync):
                if progress_callback:
                    progress = ((idx + 1) / len(tables_to_sync)) * 50  # First half for library
                    progress_callback(table, progress)
                
                try:
                    if direction in ['local_to_remote', 'both']:
                        records = self._sync_table_local_to_remote(
                            local_conn, remote_conn, table
                        )
                        results['records_synced'] += records
                    
                    if direction in ['remote_to_local', 'both']:
                        records = self._sync_table_remote_to_local(
                            local_conn, remote_conn, table
                        )
                        results['records_synced'] += records
                    
                    results['tables_synced'].append(table)
                    
                except Exception as e:
                    results['errors'].append(f"{table}: {str(e)}")
            
            # Portal tables (requests) - sync from remote to local so desktop sees web requests
            try:
                portal_db_path = os.path.join(os.path.dirname(self.local_db_path), 'Web-Extension', 'portal.db')
                if os.path.exists(os.path.dirname(portal_db_path)):
                    portal_conn = sqlite3.connect(portal_db_path)
                    portal_conn.row_factory = sqlite3.Row
                    
                    # Tables to sync FROM cloud TO local (student submissions + auth)
                    for idx, table in enumerate(portal_tables_pull):
                        if progress_callback:
                            denom = max(1, len(portal_tables_pull))
                            progress = 50 + ((idx + 1) / denom) * 25
                            progress_callback(f"portal.{table}", progress)
                        
                        try:
                            # Sync from remote to local (students submit on web → desktop admin sees them)
                            records = self._sync_portal_table_remote_to_local(
                                portal_conn, remote_conn, table
                            )
                            results['records_synced'] += records
                            results['tables_synced'].append(f'portal.{table}')
                        except Exception as e:
                            # Don't fail entire sync if portal tables have issues
                            results['errors'].append(f"portal.{table}: {str(e)}")
                    
                    # Tables to sync FROM local TO cloud (admin broadcasts + auth)
                    for idx, table in enumerate(portal_tables_push):
                        if progress_callback:
                            denom = max(1, len(portal_tables_push))
                            progress = 75 + ((idx + 1) / denom) * 25
                            progress_callback(f"portal.{table} (push)", progress)
                        
                        try:
                            # Sync from local to remote (admin creates notices → web portal shows them)
                            records = self._sync_portal_table_local_to_remote(
                                portal_conn, remote_conn, table
                            )
                            results['records_synced'] += records
                            results['tables_synced'].append(f'portal.{table}')
                        except Exception as e:
                            results['errors'].append(f"portal.{table} (push): {str(e)}")
                    
                    portal_conn.commit()
                    portal_conn.close()
            except Exception as e:
                results['errors'].append(f"Portal sync: {str(e)}")
            
            results['success'] = len(results['errors']) == 0
            # Save sync time with status
            if results['success']:
                self._register_sync_success()
                self._save_sync_time(status='completed')
            else:
                self._register_sync_failure('; '.join(results['errors']) if results['errors'] else 'sync errors')
                self._save_sync_time(status='completed_with_errors')
            
        except Exception as e:
            results['errors'].append(f"Connection error: {str(e)}")
            self._register_sync_failure(results['errors'][-1])
            self._save_sync_time(status='failed')
        
        finally:
            try:
                if local_conn is not None:
                    local_conn.close()
            except Exception:
                pass
            try:
                if remote_conn is not None:
                    remote_conn.close()
            except Exception:
                pass
            with self._sync_lock:
                self.is_syncing = False
        
        return results

    def _ensure_sync_deletions_tables(self, local_conn, remote_conn):
        """Ensure the sync_deletions tombstone table exists in both local and remote DBs."""
        # Local (SQLite)
        lc = local_conn.cursor()
        lc.execute("""
            CREATE TABLE IF NOT EXISTS sync_deletions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                pk_value TEXT NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'desktop',
                synced_remote INTEGER DEFAULT 0,
                UNIQUE(table_name, pk_value)
            )
        """)
        local_conn.commit()

        # Remote (Postgres)
        rc = remote_conn.cursor()
        rc.execute("""
            CREATE TABLE IF NOT EXISTS sync_deletions (
                id SERIAL PRIMARY KEY,
                table_name TEXT NOT NULL,
                pk_value TEXT NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'desktop',
                UNIQUE(table_name, pk_value)
            )
        """)
        remote_conn.commit()

    def _sync_deletions_local_to_remote(self, local_conn, remote_conn, allowed_tables=None):
        """Push local tombstones to remote and delete the corresponding remote rows."""
        allowed = set(allowed_tables) if allowed_tables else None
        lc = local_conn.cursor()
        rc = remote_conn.cursor()

        # Only push unsynced tombstones
        if allowed:
            placeholders = ','.join(['?'] * len(allowed))
            lc.execute(
                f"SELECT table_name, pk_value, deleted_at, source FROM sync_deletions WHERE synced_remote=0 AND table_name IN ({placeholders})",
                tuple(allowed)
            )
        else:
            lc.execute("SELECT table_name, pk_value, deleted_at, source FROM sync_deletions WHERE synced_remote=0")
        rows = lc.fetchall() or []
        if not rows:
            return 0

        pushed = 0
        for row in rows:
            table_name = str(row[0])
            pk_value = str(row[1])
            deleted_at = row[2]
            source = str(row[3] or 'desktop')
            if allowed and table_name not in allowed:
                continue

            # 1) Upsert tombstone to remote
            rc.execute(
                """
                INSERT INTO sync_deletions (table_name, pk_value, deleted_at, source)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (table_name, pk_value)
                DO UPDATE SET deleted_at = EXCLUDED.deleted_at, source = EXCLUDED.source
                """,
                (table_name, pk_value, deleted_at, source)
            )

            # 2) Delete remote row from the actual table
            pk_col = self._get_primary_key(table_name)
            try:
                rc.execute(f"DELETE FROM {table_name} WHERE {pk_col} = %s", (pk_value,))
            except Exception as e:
                # If table doesn't exist remotely or constraints block, keep tombstone anyway.
                print(f"[Sync Deletions] Remote delete failed for {table_name}({pk_value}): {e}")

            # 3) Mark local tombstone as synced
            lc.execute(
                "UPDATE sync_deletions SET synced_remote=1 WHERE table_name=? AND pk_value=?",
                (table_name, pk_value)
            )
            pushed += 1

        remote_conn.commit()
        local_conn.commit()
        return pushed

    def _sync_deletions_remote_to_local(self, local_conn, remote_conn, allowed_tables=None):
        """Pull remote tombstones and delete the corresponding local rows."""
        allowed = set(allowed_tables) if allowed_tables else None
        lc = local_conn.cursor()
        rc = remote_conn.cursor()
        cutoff = self._get_sync_cutoff()

        # Pull only new tombstones when possible
        if cutoff:
            rc.execute("SELECT table_name, pk_value, deleted_at, source FROM sync_deletions WHERE deleted_at IS NULL OR deleted_at > %s", (cutoff,))
        else:
            rc.execute("SELECT table_name, pk_value, deleted_at, source FROM sync_deletions")
        rows = rc.fetchall() or []
        if not rows:
            return 0

        applied = 0
        for row in rows:
            table_name = str(row[0])
            pk_value = str(row[1])
            deleted_at = row[2]
            source = str(row[3] or 'remote')
            if allowed and table_name not in allowed:
                continue

            # Persist tombstone locally (synced_remote=1 because it exists in cloud)
            try:
                lc.execute(
                    "INSERT OR REPLACE INTO sync_deletions (table_name, pk_value, deleted_at, source, synced_remote) VALUES (?, ?, ?, ?, 1)",
                    (table_name, pk_value, deleted_at, source)
                )
            except Exception:
                pass

            # Delete local row
            pk_col = self._get_primary_key(table_name)
            try:
                lc.execute(f"DELETE FROM {table_name} WHERE {pk_col} = ?", (pk_value,))
            except Exception as e:
                print(f"[Sync Deletions] Local delete failed for {table_name}({pk_value}): {e}")
                continue
            applied += 1

        local_conn.commit()
        return applied
    
    def _sync_table_local_to_remote(self, local_conn, remote_conn, table_name):
        """Sync a table from local SQLite to remote Postgres using natural business keys.

        Bug fixes applied:
        - Bug 3: Never sends the auto-increment 'id' in the payload — avoids serial id mismatch
          that caused ON CONFLICT (id) to never fire and create duplicates each cycle.
        - Bug 2: Sync manager is the ONLY writer to Supabase for data tables (_push_to_cloud
          removed from borrow/return/book writes in database.py).
        - Uses natural business key from _NATURAL_KEY_MAP for ON CONFLICT resolution.
        - For tables with no natural key (admin_activity, notices): INSERT ... DO NOTHING.
        """
        try:
            local_cursor = local_conn.cursor()
            remote_cursor = remote_conn.cursor()
            cutoff = self._get_sync_cutoff()

            # Keep the remote schema aligned with the local schema before upserts.
            self._ensure_remote_table_columns(local_conn, remote_conn, table_name)

            # Ensure remote table exists for shared runtime settings
            if table_name == 'system_settings':
                remote_cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                remote_conn.commit()

            # Delta sync: only changed records since last sync
            has_updated_at = False
            try:
                local_cursor.execute(f"PRAGMA table_info({table_name})")
                has_updated_at = any(str(col[1]).lower() == 'updated_at' for col in local_cursor.fetchall())
            except Exception:
                has_updated_at = False

            if cutoff and has_updated_at:
                local_cursor.execute(
                    f"SELECT * FROM {table_name} WHERE updated_at > ?",
                    (cutoff,)
                )
            else:
                local_cursor.execute(f"SELECT * FROM {table_name}")
            rows = local_cursor.fetchall()

            if not rows:
                return 0

            # All column names from local
            all_columns = [desc[0] for desc in local_cursor.description]

            # FIX Bug 3: Never send the local auto-increment 'id' to Supabase.
            # Local SQLite id sequence is completely independent from Supabase SERIAL.
            # Including it causes ON CONFLICT (id) to miss (ids differ) → duplicate insert.
            SKIP_COLS = {'id'}
            payload_columns = [c for c in all_columns if c.lower() not in SKIP_COLS]

            # Natural key for this table (drives ON CONFLICT target)
            natural_key = self._NATURAL_KEY_MAP.get(table_name)

            synced_count = 0
            for row in rows:
                try:
                    row_dict = dict(zip(all_columns, row))

                    # Skip rows where any natural key field is NULL
                    if natural_key:
                        if any(row_dict.get(k) is None for k in natural_key):
                            continue

                    payload_vals = [row_dict[c] for c in payload_columns]

                    # Normalize book_id in payload if present
                    if 'book_id' in payload_columns:
                        b_idx = payload_columns.index('book_id')
                        if payload_vals[b_idx] is not None:
                            payload_vals[b_idx] = str(payload_vals[b_idx]).replace(' ', '')

                    # Fix 1: Backfill NULL updated_at before pushing to Supabase.
                    if 'updated_at' in payload_columns:
                        idx = payload_columns.index('updated_at')
                        if payload_vals[idx] is None:
                            payload_vals[idx] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    placeholders = ', '.join(['%s'] * len(payload_columns))
                    cols_str = ', '.join(payload_columns)

                    if natural_key:
                        conflict_target = ', '.join(natural_key)
                        update_cols = ', '.join(
                            [f"{col} = EXCLUDED.{col}"
                             for col in payload_columns
                             if col not in natural_key]
                        )
                        if update_cols:
                            query = f"""
                                INSERT INTO {table_name} ({cols_str})
                                VALUES ({placeholders})
                                ON CONFLICT ({conflict_target})
                                DO UPDATE SET {update_cols}
                            """
                        else:
                            query = f"""
                                INSERT INTO {table_name} ({cols_str})
                                VALUES ({placeholders})
                                ON CONFLICT ({conflict_target}) DO NOTHING
                            """
                    else:
                        # Log/audit table: no natural key → insert only, skip exact duplicates
                        query = f"""
                            INSERT INTO {table_name} ({cols_str})
                            VALUES ({placeholders})
                            ON CONFLICT DO NOTHING
                        """

                    remote_cursor.execute(query, payload_vals)
                    synced_count += 1

                except Exception as e:
                    try:
                        remote_conn.rollback()
                    except Exception:
                        pass
                    print(f"Error syncing row in {table_name} (local→remote): {e}")

            remote_conn.commit()
            return synced_count

        except Exception as e:
            print(f"Error syncing table {table_name} local to remote: {e}")
            return 0
    
    def _sync_table_remote_to_local(self, local_conn, remote_conn, table_name):
        """Sync a table from remote Postgres to local SQLite using natural business keys.

        Bug fixes applied:
        - Bug 4: Replaces destructive INSERT OR REPLACE with INSERT OR IGNORE + explicit UPDATE.
          INSERT OR REPLACE deletes the row first if ANY unique constraint conflicts, which
          silently destroys unrelated rows that share a local id with an incoming remote row.
        - Bug 3: Never writes the remote 'id' to SQLite — Supabase SERIAL ids are independent
          from SQLite AUTOINCREMENT ids; writing them would destroy local rows via id collision.
        - Uses natural business key for existence check + selective UPDATE.
        """
        try:
            local_cursor = local_conn.cursor()
            remote_cursor = remote_conn.cursor()
            cutoff = self._get_sync_cutoff()

            # Ensure local table exists for shared runtime settings
            if table_name == 'system_settings':
                local_cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                local_conn.commit()

            # Delta sync from remote
            try:
                remote_cursor.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = %s
                """, (table_name,))
                has_updated_at = any(str(r[0]).lower() == 'updated_at' for r in remote_cursor.fetchall())
            except Exception:
                has_updated_at = False

            if cutoff and has_updated_at:
                remote_cursor.execute(
                    f"SELECT * FROM {table_name} WHERE updated_at > %s",
                    (cutoff,)
                )
            else:
                remote_cursor.execute(f"SELECT * FROM {table_name}")
            rows = remote_cursor.fetchall()

            if not rows:
                return 0

            # All column names from remote result
            all_remote_columns = [desc[0] for desc in remote_cursor.description]

            # FIX Bug 4 + Bug 3: Never write the remote 'id' into local SQLite.
            # Supabase SERIAL and SQLite AUTOINCREMENT sequences are completely independent.
            # Writing the remote id causes INSERT OR REPLACE to delete a different local row
            # that happened to have that id, silently destroying data.
            SKIP_COLS = {'id'}
            # available_copies is a DERIVED column — always computed from borrow_records.
            # NEVER pull it from Supabase. Supabase's value may be corrupted by old
            # concurrent _push_to_cloud increment/decrement bugs (e.g. showing 18545
            # for a book with 1 copy). Local recalculation at startup is the source of truth.
            if table_name == 'books':
                SKIP_COLS.add('available_copies')
            # Only include columns that actually exist locally (handles schema drift)
            local_cursor.execute(f"PRAGMA table_info({table_name})")
            local_col_names = {col[1].lower() for col in local_cursor.fetchall()}
            payload_columns = [
                c for c in all_remote_columns
                if c.lower() not in SKIP_COLS and c.lower() in local_col_names
            ]

            if not payload_columns:
                return 0

            natural_key = self._NATURAL_KEY_MAP.get(table_name)

            synced_count = 0
            for row in rows:
                try:
                    row_dict = dict(zip(all_remote_columns, row))
                    payload_vals = [row_dict.get(c) for c in payload_columns]

                    if natural_key:
                        key_vals = [row_dict.get(k) for k in natural_key]
                        # Skip rows with NULL in any natural key field
                        if any(v is None for v in key_vals):
                            continue
                        # Bug 4 fix: only normalize whitespace on book_id specifically.
                        # Stripping spaces from ALL key columns (enrollment_no, borrow_date)
                        # is harmless but stripping from book_id in the WHERE clause while
                        # not doing so consistently in payload causes zero-match lookups that
                        # re-insert as duplicates instead of updating the existing record.
                        if table_name in ('books', 'borrow_records') and 'book_id' in natural_key:
                            bk_key_idx = list(natural_key).index('book_id')
                            if key_vals[bk_key_idx] is not None:
                                key_vals[bk_key_idx] = str(key_vals[bk_key_idx]).replace(' ', '')
                        
                        # Normalize payload values too so they are saved clean
                        if 'book_id' in payload_columns:
                            b_idx = payload_columns.index('book_id')
                            if payload_vals[b_idx] is not None:
                                payload_vals[b_idx] = str(payload_vals[b_idx]).replace(' ', '')

                        where_clause = ' AND '.join([f"{k} = ?" for k in natural_key])

                        # Check if this record already exists locally
                        local_cursor.execute(
                            f"SELECT 1 FROM {table_name} WHERE {where_clause} LIMIT 1",
                            key_vals
                        )
                        exists = local_cursor.fetchone()

                        if exists:
                            # Update non-key columns only
                            update_cols = [c for c in payload_columns if c not in natural_key]
                            if update_cols:
                                set_clause = ', '.join([f"{c} = ?" for c in update_cols])
                                update_vals = [row_dict.get(c) for c in update_cols] + key_vals
                                local_cursor.execute(
                                    f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}",
                                    update_vals
                                )
                        else:
                            # New record: insert without id (SQLite will auto-generate)
                            placeholders = ', '.join(['?'] * len(payload_columns))
                            cols_str = ', '.join(payload_columns)
                            local_cursor.execute(
                                f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})",
                                payload_vals
                            )
                        synced_count += 1

                    else:
                        # No natural key (log/audit tables): insert only, never overwrite
                        # INSERT OR IGNORE is safe here — won't delete anything
                        placeholders = ', '.join(['?'] * len(payload_columns))
                        cols_str = ', '.join(payload_columns)
                        local_cursor.execute(
                            f"INSERT OR IGNORE INTO {table_name} ({cols_str}) VALUES ({placeholders})",
                            payload_vals
                        )
                        synced_count += 1

                except Exception as e:
                    print(f"Error syncing row from remote in {table_name}: {e}")

            local_conn.commit()
            return synced_count

        except Exception as e:
            print(f"Error syncing table {table_name} remote to local: {e}")
            return 0
    
    # Natural business-key map — used by both local→remote and remote→local sync.
    # These are content-based unique keys, NEVER the auto-increment serial 'id'.
    # None = no natural key (log/audit tables) → INSERT ... DO NOTHING / INSERT OR IGNORE
    _NATURAL_KEY_MAP = {
        'students':          ('enrollment_no',),
        'books':             ('book_id',),
        'borrow_records':    ('enrollment_no', 'accession_no', 'borrow_date'),
        'admin_activity':    None,
        'academic_years':    ('year_name',),
        'promotion_history': ('enrollment_no', 'old_year', 'new_year', 'promotion_date'),
        'system_settings':   ('key',),
        'requests':          None,
        'notices':           None,
        'student_auth':      ('enrollment_no',),
        'deletion_requests': ('student_id', 'timestamp'),
        'book_wishlist':     ('book_id', 'enrollment_no'),
        'book_ratings':      ('book_id', 'enrollment_no'),
    }

    def _get_primary_key(self, table_name):
        """Legacy helper — returns first natural key column or 'id' as fallback.
        Prefer _NATURAL_KEY_MAP for new sync logic."""
        nk = self._NATURAL_KEY_MAP.get(table_name)
        return nk[0] if nk else 'id'
    
    def _sync_portal_table_remote_to_local(self, local_conn, remote_conn, table_name):
        """Sync portal tables (requests, notices) from remote Postgres to local SQLite.
        
        Uses content-based deduplication since cloud and local IDs are independent.
        For requests: uses (enrollment_no, request_type, created_at) as unique key.
        For notices: uses (title, created_at) as unique key.
        """
        try:
            local_cursor = local_conn.cursor()
            remote_cursor = remote_conn.cursor()
            
            # Check if table exists remotely
            remote_cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            if not remote_cursor.fetchone()[0]:
                return 0
            
            # Get records from remote
            remote_cursor.execute(f"SELECT * FROM {table_name}")
            rows = remote_cursor.fetchall()
            
            if not rows:
                return 0
            
            # Get column names from remote
            remote_columns = [desc[0] for desc in remote_cursor.description]
            
            # Get local column names to handle schema differences
            local_cursor.execute(f"PRAGMA table_info({table_name})")
            local_col_info = local_cursor.fetchall()
            local_columns = [col[1] for col in local_col_info]
            
            # Column mapping: remote → local (skip ID columns - let local auto-generate)
            column_map = {}
            skip_cols = {'req_id', 'id'}  # Don't sync IDs - they're independent
            for rc in remote_columns:
                if rc in skip_cols:
                    continue  # Skip ID columns
                if rc in local_columns:
                    column_map[rc] = rc
            
            # Define unique key for deduplication based on table
            if table_name == 'requests':
                unique_key_cols = ['enrollment_no', 'request_type', 'created_at']
            elif table_name == 'deletion_requests':
                unique_key_cols = ['student_id', 'timestamp']
            elif table_name == 'student_auth':
                unique_key_cols = ['enrollment_no']
            elif table_name == 'book_wishlist':
                unique_key_cols = ['book_id', 'enrollment_no']
            elif table_name == 'book_ratings':
                unique_key_cols = ['book_id', 'enrollment_no']
            elif table_name == 'notices':
                unique_key_cols = ['title', 'created_at']
            else:
                unique_key_cols = ['created_at']  # Fallback
            
            # Verify unique key columns exist locally
            unique_key_cols = [c for c in unique_key_cols if c in local_columns]
            if not unique_key_cols:
                print(f"Warning: No unique key columns found for {table_name}")
                return 0
            
            synced_count = 0
            new_count = 0
            
            for row in rows:
                try:
                    # Create dict for easier access
                    row_dict = dict(zip(remote_columns, row))
                    
                    # Build unique key values for deduplication check
                    unique_vals = [row_dict.get(c) for c in unique_key_cols]
                    if any(v is None for v in unique_vals):
                        continue  # Skip rows with null unique keys
                    
                    # Check if record already exists locally using unique key
                    where_clause = ' AND '.join([f"{c} = ?" for c in unique_key_cols])
                    check_query = f"SELECT 1 FROM {table_name} WHERE {where_clause} LIMIT 1"
                    local_cursor.execute(check_query, unique_vals)
                    exists = local_cursor.fetchone()
                    
                    if exists:
                        # For student_auth, update existing records (password may have changed)
                        if table_name == 'student_auth' or table_name == 'book_ratings':
                            update_cols = []
                            update_vals = []
                            for rc in remote_columns:
                                if rc in column_map and rc not in unique_key_cols:
                                    update_cols.append(f"{column_map[rc]} = ?")
                                    update_vals.append(row_dict[rc])
                            if update_cols:
                                update_vals.extend(unique_vals)
                                update_query = f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE {where_clause}"
                                local_cursor.execute(update_query, update_vals)
                        synced_count += 1
                        continue
                    
                    # Build insert row with only mapped columns (no ID)
                    insert_cols = []
                    insert_vals = []
                    for rc in remote_columns:
                        if rc in column_map:
                            insert_cols.append(column_map[rc])
                            insert_vals.append(row_dict[rc])
                    
                    if not insert_cols:
                        continue
                    
                    # Insert new record (let SQLite auto-generate ID)
                    placeholders = ', '.join(['?'] * len(insert_cols))
                    cols = ', '.join(insert_cols)
                    
                    query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                    local_cursor.execute(query, insert_vals)
                    synced_count += 1
                    new_count += 1
                    
                except Exception as e:
                    print(f"Error syncing portal row in {table_name}: {e}")
            
            if new_count > 0:
                print(f"[Portal Sync] {table_name}: {new_count} new records synced")
            
            return synced_count
            
        except Exception as e:
            print(f"Error syncing portal table {table_name} remote to local: {e}")
            return 0
    
    def _sync_portal_table_local_to_remote(self, local_conn, remote_conn, table_name):
        """Sync portal tables (notices) from local SQLite to remote Postgres.
        
        Used for admin broadcasts - notices created on desktop should appear on web portal.
        Uses content-based deduplication since cloud and local IDs are independent.
        """
        try:
            local_cursor = local_conn.cursor()
            remote_cursor = remote_conn.cursor()

            # Keep the remote portal schema aligned before pushing rows.
            self._ensure_remote_table_columns(local_conn, remote_conn, table_name)
            
            # Check if table exists remotely
            remote_cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            if not remote_cursor.fetchone()[0]:
                # Create table if it doesn't exist
                if table_name == 'notices':
                    remote_cursor.execute("""
                        CREATE TABLE IF NOT EXISTS notices (
                            id SERIAL PRIMARY KEY,
                            title TEXT,
                            message TEXT,
                            active INTEGER DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    remote_conn.commit()
                elif table_name == 'student_auth':
                    remote_cursor.execute("""
                        CREATE TABLE IF NOT EXISTS student_auth (
                            enrollment_no TEXT PRIMARY KEY,
                            password TEXT NOT NULL,
                            is_first_login INTEGER DEFAULT 1,
                            last_changed TIMESTAMP
                        )
                    """)
                    remote_conn.commit()
                elif table_name == 'book_wishlist':
                    remote_cursor.execute("""
                        CREATE TABLE IF NOT EXISTS book_wishlist (
                            id SERIAL PRIMARY KEY,
                            book_id TEXT NOT NULL,
                            enrollment_no TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(book_id, enrollment_no)
                        )
                    """)
                    remote_conn.commit()
                elif table_name == 'book_ratings':
                    remote_cursor.execute("""
                        CREATE TABLE IF NOT EXISTS book_ratings (
                            id SERIAL PRIMARY KEY,
                            book_id TEXT NOT NULL,
                            enrollment_no TEXT NOT NULL,
                            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(book_id, enrollment_no)
                        )
                    """)
                    remote_conn.commit()
            
            # Get records from local
            local_cursor.execute(f"SELECT * FROM {table_name}")
            rows = local_cursor.fetchall()
            
            if not rows:
                return 0
            
            # Get column names from local
            local_cursor.execute(f"PRAGMA table_info({table_name})")
            local_col_info = local_cursor.fetchall()
            local_columns = [col[1] for col in local_col_info]
            
            # Get remote column names
            remote_cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s
            """, (table_name,))
            remote_columns = [row[0] for row in remote_cursor.fetchall()]
            
            # Column mapping: local → remote (skip ID columns)
            skip_cols = {'id', 'req_id'}
            column_map = {}
            for lc in local_columns:
                if lc in skip_cols:
                    continue
                if lc in remote_columns:
                    column_map[lc] = lc
            
            # Define unique key for deduplication
            if table_name == 'notices':
                unique_key_cols = ['title', 'created_at']
            elif table_name == 'student_auth':
                unique_key_cols = ['enrollment_no']
            elif table_name == 'book_wishlist':
                unique_key_cols = ['book_id', 'enrollment_no']
            elif table_name == 'book_ratings':
                unique_key_cols = ['book_id', 'enrollment_no']
            else:
                unique_key_cols = ['created_at']
            
            unique_key_cols = [c for c in unique_key_cols if c in remote_columns]
            if not unique_key_cols:
                return 0
            
            synced_count = 0
            new_count = 0
            
            for row in rows:
                try:
                    row_dict = dict(row)
                    
                    # Build unique key values for deduplication check
                    unique_vals = [row_dict.get(c) for c in unique_key_cols]
                    if any(v is None for v in unique_vals):
                        continue
                    
                    # Check if record already exists remotely
                    where_clause = ' AND '.join([f"{c} = %s" for c in unique_key_cols])
                    check_query = f"SELECT 1 FROM {table_name} WHERE {where_clause} LIMIT 1"
                    remote_cursor.execute(check_query, unique_vals)
                    exists = remote_cursor.fetchone()
                    
                    if exists:
                        # For student_auth, update existing records (password may have changed)
                        if table_name == 'student_auth' or table_name == 'book_ratings':
                            update_cols = []
                            update_vals = []
                            for lc in local_columns:
                                if lc in column_map and lc not in unique_key_cols:
                                    update_cols.append(f"{column_map[lc]} = %s")
                                    update_vals.append(row_dict[lc])
                            if update_cols:
                                update_vals.extend(unique_vals)
                                update_query = f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE {where_clause}"
                                remote_cursor.execute(update_query, update_vals)
                                remote_conn.commit()
                        synced_count += 1
                        continue
                    
                    # Build insert row with only mapped columns (no ID)
                    insert_cols = []
                    insert_vals = []
                    for lc in local_columns:
                        if lc in column_map:
                            insert_cols.append(column_map[lc])
                            insert_vals.append(row_dict[lc])
                    
                    if not insert_cols:
                        continue
                    
                    # Insert new record (let Postgres auto-generate ID)
                    placeholders = ', '.join(['%s'] * len(insert_cols))
                    cols = ', '.join(insert_cols)
                    
                    query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                    remote_cursor.execute(query, insert_vals)
                    remote_conn.commit()
                    synced_count += 1
                    new_count += 1
                    
                except Exception as e:
                    print(f"Error pushing portal row in {table_name}: {e}")
            
            if new_count > 0:
                print(f"[Portal Sync] {table_name}: {new_count} new records pushed to cloud")
            
            return synced_count
            
        except Exception as e:
            print(f"Error syncing portal table {table_name} local to remote: {e}")
            return 0

    def _sync_table_full_mirror(self, local_conn, remote_conn, table_name):
        """Full mirror: make local EXACTLY match remote (cloud is authoritative).

        Unlike the delta sync, this:
        1. Fetches ALL rows from remote.
        2. Deletes local rows whose natural key is NOT present in remote.
        3. Upserts all remote rows into local.

        Used on startup so that clearing Supabase propagates to local.
        """
        try:
            local_cursor = local_conn.cursor()
            remote_cursor = remote_conn.cursor()

            # Check table exists remotely before touching local
            remote_cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables WHERE table_name = %s
                )
            """, (table_name,))
            if not remote_cursor.fetchone()[0]:
                return 0

            # Pull all remote rows
            remote_cursor.execute(f"SELECT * FROM {table_name}")
            remote_rows = remote_cursor.fetchall()
            all_remote_columns = [desc[0] for desc in remote_cursor.description]

            natural_key = self._NATURAL_KEY_MAP.get(table_name)
            if not natural_key:
                # No natural key → skip destructive mirror for safety (log/audit tables)
                return 0

            # ── SAFETY CHECK ────────────────────────────────────────────────
            # If Supabase has 0 rows but local has significant data, the cloud
            # was likely manually cleared (not legitimately empty). In that case
            # push local UP to Supabase — never delete a full local dataset
            # just because the cloud is empty.
            if len(remote_rows) == 0:
                local_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                local_count = local_cursor.fetchone()[0]
                if local_count > 0:
                    print(f"[Full Mirror] {table_name}: Supabase empty but local has {local_count} rows "
                          f"— pushing local -> Supabase (cloud was cleared manually)")
                    pushed = self._sync_table_local_to_remote(
                        local_conn, remote_conn, table_name
                    )
                    remote_conn.commit()
                    return pushed
                else:
                    # Both sides genuinely empty — nothing to do
                    print(f"[Full Mirror] {table_name}: both local and Supabase empty — nothing to sync")
                    return 0

            # Build set of remote natural keys
            remote_key_set = set()
            for row in remote_rows:
                row_dict = dict(zip(all_remote_columns, row))
                key = tuple(str(row_dict.get(k) or '').replace(' ', '') for k in natural_key)
                remote_key_set.add(key)


            # Define columns to sync (skip ID and specific status/count columns that should not be mirrored blindly)
            SKIP_COLS = {'id'}
            if table_name == 'books':
                SKIP_COLS.add('available_copies')
                
            local_cursor.execute(f"PRAGMA table_info({table_name})")
            local_col_names = {col[1].lower() for col in local_cursor.fetchall()}
            payload_columns = [
                c for c in all_remote_columns
                if c.lower() not in SKIP_COLS and c.lower() in local_col_names
            ]

            # 1) UPSERT all remote rows into local FIRST
            upserted = 0
            for row in remote_rows:
                row_dict = dict(zip(all_remote_columns, row))
                key_vals = [row_dict.get(k) for k in natural_key]
                if any(v is None for v in key_vals):
                    continue
                # Normalize book_id whitespace
                if table_name in ('books', 'borrow_records'):
                    key_vals = [str(v).replace(' ', '') if v is not None else v for v in key_vals]

                where = ' AND '.join([f"{k} = ?" for k in natural_key])
                local_cursor.execute(f"SELECT 1 FROM {table_name} WHERE {where} LIMIT 1", key_vals)
                exists = local_cursor.fetchone()

                payload_vals = [row_dict.get(c) for c in payload_columns]
                # Normalize payload book_id to ensure clean storage
                if 'book_id' in payload_columns:
                    b_idx = payload_columns.index('book_id')
                    if payload_vals[b_idx] is not None:
                        payload_vals[b_idx] = str(payload_vals[b_idx]).replace(' ', '')
                if exists:
                    update_cols = [c for c in payload_columns if c not in natural_key]
                    if update_cols:
                        set_clause = ', '.join([f"{c} = ?" for c in update_cols])
                        update_vals = [row_dict.get(c) for c in update_cols] + key_vals
                        local_cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE {where}", update_vals)
                else:
                    placeholders = ', '.join(['?'] * len(payload_columns))
                    cols_str = ', '.join(payload_columns)
                    local_cursor.execute(f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})", payload_vals)
                upserted += 1

            # 2) DELETE local rows NOT present in remote (cloud has authority)
            local_cursor.execute(f"SELECT * FROM {table_name}")
            local_rows = local_cursor.fetchall()
            local_all_cols = [desc[0] for desc in local_cursor.description]

            deleted = 0
            for lrow in local_rows:
                ldict = dict(zip(local_all_cols, lrow))
                lkey = tuple(str(ldict.get(k) or '').replace(' ', '') for k in natural_key)
                if lkey not in remote_key_set:
                    where = ' AND '.join([f"{k} = ?" for k in natural_key])
                    vals = [ldict.get(k) for k in natural_key]
                    local_cursor.execute(f"DELETE FROM {table_name} WHERE {where}", vals)
                    deleted += 1

            local_conn.commit()
            if deleted > 0:
                print(f"[Full Mirror] {table_name}: removed {deleted} local rows not in Supabase")
            print(f"[Full Mirror] {table_name}: {len(remote_rows)} remote rows → {upserted} upserted, {deleted} pruned locally")
            return upserted

        except Exception as e:
            print(f"[Full Mirror] Error mirroring {table_name}: {e}")
            return 0

    def _enforce_local_unique_constraints(self, local_conn):
        """Add unique indexes to local SQLite tables to prevent future duplicates."""
        cur = local_conn.cursor()
        constraints = [
            # borrow_records: same student can't borrow the same specific copy on the same date twice
            ("borrow_records", "idx_borrow_unique",
             "enrollment_no, accession_no, borrow_date"),
        ]
        for table, idx_name, cols in constraints:
            try:
                cur.execute(f"""
                    CREATE UNIQUE INDEX IF NOT EXISTS {idx_name}
                    ON {table} ({cols})
                """)
                local_conn.commit()
            except Exception as e:
                # If duplicates still exist this will fail — that's OK, dedup first
                print(f"[Constraints] Could not add {idx_name}: {e}")

    def auto_sync_daemon(self, interval_minutes=5):
        """Run automatic sync in background thread.

        ARCHITECTURE: Supabase is the source of truth.
        - Startup: Full mirror — local mirrors Supabase exactly.
          If you clear Supabase, local clears too on next start.
        - Offline: Uses local SQLite cache automatically.
        - Periodic: Delta sync (bidirectional) every interval_minutes.
        """
        def sync_loop():
            # --- Step 1: Enforce local unique constraints ---
            try:
                lc = sqlite3.connect(self.local_db_path)
                self._enforce_local_unique_constraints(lc)
                lc.close()
            except Exception as e:
                print(f"[Auto-Sync] Constraint setup warning: {e}")

            # --- Step 2: Full mirror on startup (Supabase → local, destructive) ---
            print(f"[Auto-Sync] Startup FULL MIRROR (Supabase is authoritative)...")
            try:
                if psycopg2 is None:
                    raise RuntimeError("psycopg2 not installed")
                local_conn = sqlite3.connect(self.local_db_path, timeout=30)
                local_conn.execute('PRAGMA journal_mode=WAL')
                local_conn.execute('PRAGMA busy_timeout = 10000')
                remote_conn = psycopg2.connect(
                    self.remote_config,
                    connect_timeout=8, keepalives=1,
                    keepalives_idle=30, keepalives_interval=10, keepalives_count=3
                )
                mirror_tables = ['students', 'books', 'borrow_records',
                                 'academic_years', 'promotion_history', 'system_settings']
                total = 0
                for tbl in mirror_tables:
                    total += self._sync_table_full_mirror(local_conn, remote_conn, tbl)
                
                # --- NEW Step: Recalculate available_copies based on active borrows ---
                # This fixes corrupted counts by deriving them solely from current borrow status
                print("[Auto-Sync] Recalculating book available_copies...")
                lc = local_conn.cursor()
                rc = remote_conn.cursor()
                lc.execute("SELECT book_id, total_copies FROM books")
                books_list = lc.fetchall()
                for b_id, t_copies in books_list:
                    lc.execute("SELECT COUNT(*) FROM borrow_records WHERE book_id = ? AND status = 'borrowed'", (b_id,))
                    borrowed_count = lc.fetchone()[0]
                    new_available = max(0, t_copies - borrowed_count)
                    # Update local
                    lc.execute("UPDATE books SET available_copies = ?, updated_at = CURRENT_TIMESTAMP WHERE book_id = ?", (new_available, b_id))
                    # Update remote (individual push to ensure Supabase is updated immediately after mirror fixes)
                    rc.execute("UPDATE books SET available_copies = %s, updated_at = CURRENT_TIMESTAMP WHERE book_id = %s", (new_available, b_id))
                
                local_conn.commit()
                remote_conn.commit()
                remote_conn.close()
                local_conn.close()
                self._register_sync_success()
                self._save_sync_time(status='completed')
                print(f"[Auto-Sync] Full mirror and count recalculation complete: {total} records synced")
            except Exception as e:
                print(f"[Auto-Sync] Full mirror failed (offline?): {e}")
                print(f"[Auto-Sync] Running in OFFLINE mode — using local SQLite cache")

            next_run_ts = time.time() + (interval_minutes * 60)
            cycle_count = 0
            while True:
                now = time.time()
                if now < next_run_ts:
                    time.sleep(min(5, max(1, next_run_ts - now)))
                    continue

                print(f"[Auto-Sync] Background sync at {datetime.now().strftime('%H:%M:%S')}")
                try:
                    cycle_count += 1
                    # Periodic delta sync (light — delta since last sync)
                    light_tables = ['students', 'borrow_records', 'admin_activity',
                                    'academic_years', 'promotion_history', 'system_settings',
                                    'requests', 'deletion_requests', 'student_auth', 'notices']
                    tables_for_run = list(light_tables)
                    # Every 4th cycle, include books for eventual consistency
                    if cycle_count % 4 == 0:
                        tables_for_run.insert(1, 'books')
                    result = self.sync_now(direction='both', tables_override=tables_for_run)
                    if result.get('success'):
                        print(f"[Auto-Sync] Completed: {result.get('records_synced', 0)} records synced")
                        next_run_ts = time.time() + (interval_minutes * 60)
                    else:
                        errors = result.get('errors', result.get('error', 'Unknown'))
                        print(f"[Auto-Sync] Completed with issues: {errors}")
                        backoff = self._compute_backoff_seconds()
                        if backoff > 0:
                            print(f"[Auto-Sync] Backoff: retry in {backoff}s (failure #{self.consecutive_failures})")
                        next_run_ts = time.time() + max(interval_minutes * 60, backoff)
                except Exception as e:
                    print(f"[Auto-Sync] Exception: {e}")
                    self._register_sync_failure(e)
                    backoff = self._compute_backoff_seconds()
                    next_run_ts = time.time() + max(interval_minutes * 60, backoff)

        thread = threading.Thread(target=sync_loop, daemon=True)
        thread.start()
        print(f"[Auto-Sync] Daemon started (full mirror on startup + delta every {interval_minutes} min)")


def create_sync_manager(db):
    """
    Create a sync manager instance for the given database
    
    Args:
        db: Database instance (should be using local SQLite)
    
    Returns:
        SyncManager instance or None if remote config not available
    """
    try:
        # Get local database path from the Database instance
        local_db_path = db.db_path
        
        if not local_db_path:
            print("[WARNING] Sync Manager: No local database path available")
            return None
        
        # Get remote database config from environment
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            print("[WARNING] Sync Manager: No remote database URL configured (DATABASE_URL not set)")
            print("   Sync disabled - desktop will work offline only")
            return None

        if psycopg2 is None:
            print("[WARNING] Sync Manager: psycopg2 not installed - remote sync disabled")
            return None
        
        # Parse PostgreSQL connection string
        # Format: postgresql://user:password@host:port/database
        remote_config = database_url
        
        print(f"[OK] Sync Manager: Configured for remote sync")
        print(f"   Local: {local_db_path}")
        return SyncManager(local_db_path, remote_config)
            
    except Exception as e:
        print(f"[WARNING] Sync Manager: Failed to initialize: {e}")
        return None
