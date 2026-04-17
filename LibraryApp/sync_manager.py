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

        This keeps Supabase aligned with SQLite when additive migrations are made
        locally (for example, the `updated_at` column used by delta sync).
        """
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
            default_portal_tables_pull = ['requests', 'deletion_requests', 'student_auth']
            default_portal_tables_push = ['notices', 'student_auth']

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
        """Sync a table from local to remote"""
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
            
            # Get records modified since last sync
            has_updated_at = False
            try:
                local_cursor.execute(f"PRAGMA table_info({table_name})")
                has_updated_at = any(str(col[1]).lower() == 'updated_at' for col in local_cursor.fetchall())
            except Exception:
                has_updated_at = False

            if cutoff and has_updated_at:
                local_cursor.execute(f"SELECT * FROM {table_name} WHERE updated_at IS NULL OR updated_at > ?", (cutoff,))
            else:
                local_cursor.execute(f"SELECT * FROM {table_name}")
            rows = local_cursor.fetchall()
            
            if not rows:
                return 0
            
            # Get column names
            columns = [desc[0] for desc in local_cursor.description]
            primary_key = self._get_primary_key(table_name)
            pk_idx = columns.index(primary_key) if primary_key in columns else 0
            
            synced_count = 0
            for row in rows:
                try:
                    # Skip rows with null primary key
                    if row[pk_idx] is None:
                        continue
                    
                    # Try to insert or update
                    placeholders = ', '.join(['%s'] * len(row))
                    cols = ', '.join(columns)
                    
                    # Use UPSERT (INSERT ... ON CONFLICT)
                    update_cols = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != primary_key])
                    
                    query = f"""
                        INSERT INTO {table_name} ({cols})
                        VALUES ({placeholders})
                        ON CONFLICT ({primary_key}) 
                        DO UPDATE SET {update_cols}
                    """
                    
                    remote_cursor.execute(query, row)
                    synced_count += 1
                    
                except Exception as e:
                    # Rollback the failed transaction to continue with next rows
                    try:
                        remote_conn.rollback()
                    except:
                        pass
                    print(f"Error syncing row in {table_name}: {e}")
            
            remote_conn.commit()
            return synced_count
            
        except Exception as e:
            print(f"Error syncing table {table_name} local to remote: {e}")
            return 0
    
    def _sync_table_remote_to_local(self, local_conn, remote_conn, table_name):
        """Sync a table from remote to local"""
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
            
            # Get records from remote
            try:
                remote_cursor.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = %s
                """, (table_name,))
                has_updated_at = any(str(r[0]).lower() == 'updated_at' for r in remote_cursor.fetchall())
            except Exception:
                has_updated_at = False

            if cutoff and has_updated_at:
                remote_cursor.execute(f"SELECT * FROM {table_name} WHERE updated_at IS NULL OR updated_at > %s", (cutoff,))
            else:
                remote_cursor.execute(f"SELECT * FROM {table_name}")
            rows = remote_cursor.fetchall()
            
            if not rows:
                return 0
            
            # Get column names
            columns = [desc[0] for desc in remote_cursor.description]
            
            synced_count = 0
            for row in rows:
                try:
                    # Try to insert or replace
                    placeholders = ', '.join(['?'] * len(row))
                    cols = ', '.join(columns)
                    
                    query = f"INSERT OR REPLACE INTO {table_name} ({cols}) VALUES ({placeholders})"
                    local_cursor.execute(query, row)
                    synced_count += 1
                    
                except Exception as e:
                    print(f"Error syncing row in {table_name}: {e}")
            
            local_conn.commit()
            return synced_count
            
        except Exception as e:
            print(f"Error syncing table {table_name} remote to local: {e}")
            return 0
    
    def _get_primary_key(self, table_name):
        """Get primary key column name for table"""
        pk_map = {
            'students': 'enrollment_no',
            'books': 'book_id',
            'borrow_records': 'id',
            'admin_activity': 'id',
            'requests': 'req_id',
            'notices': 'id',
            'academic_years': 'id',
            'promotion_history': 'id',
            'system_settings': 'key'
        }
        return pk_map.get(table_name, 'id')
    
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
                        if table_name == 'student_auth':
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
                        if table_name == 'student_auth':
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
    
    def auto_sync_daemon(self, interval_minutes=5):
        """Run automatic sync in background thread.
        
        Performs an immediate initial sync (remote→local) so the desktop
        starts with the latest cloud data, then continues syncing
        bidirectionally on the given interval.
        """
        def sync_loop():
            # Initial sync: pull cloud data into local SQLite
            print(f"[Auto-Sync] Initial sync (cloud → local) started...")
            try:
                result = self.sync_now(direction='remote_to_local')
                if result.get('success'):
                    print(f"[Auto-Sync] Initial pull complete: {result.get('records_synced', 0)} records")
                else:
                    errors = result.get('errors', result.get('error', 'Unknown'))
                    print(f"[Auto-Sync] Initial pull had issues: {errors}")
            except Exception as e:
                print(f"[Auto-Sync] Initial pull failed: {e}")
            next_run_ts = time.time() + (interval_minutes * 60)
            cycle_count = 0
            while True:
                now = time.time()
                if now < next_run_ts:
                    # Short sleep keeps daemon responsive without busy loop
                    time.sleep(min(5, max(1, next_run_ts - now)))
                    continue

                print(f"[Auto-Sync] Background sync at {datetime.now().strftime('%H:%M:%S')}")
                try:
                    cycle_count += 1
                    # Periodic sync: use a lighter table set to avoid re-pulling the heavy books table.
                    # Full sync still happens on startup/manual sync.
                    light_tables = ['students', 'borrow_records', 'admin_activity', 'academic_years', 'promotion_history', 'system_settings', 'requests', 'deletion_requests', 'student_auth', 'notices']
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
                            print(f"[Auto-Sync] Backoff active: retry in {backoff}s (failure #{self.consecutive_failures})")
                        next_run_ts = time.time() + max(interval_minutes * 60, backoff)
                except Exception as e:
                    print(f"[Auto-Sync] Exception: {e}")
                    self._register_sync_failure(e)
                    backoff = self._compute_backoff_seconds()
                    if backoff > 0:
                        print(f"[Auto-Sync] Backoff after exception: retry in {backoff}s")
                    next_run_ts = time.time() + max(interval_minutes * 60, backoff)
        
        thread = threading.Thread(target=sync_loop, daemon=True)
        thread.start()
        print(f"[Auto-Sync] Daemon started (initial pull + every {interval_minutes} min)")


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
