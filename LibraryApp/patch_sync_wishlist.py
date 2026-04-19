import re

path = "C:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/LibraryApp/sync_manager.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Add to pull tables
if "'requests', 'deletion_requests', 'student_auth']" in text:
    text = text.replace(
        "'requests', 'deletion_requests', 'student_auth']",
        "'requests', 'deletion_requests', 'student_auth', 'book_wishlist', 'book_ratings']"
    )

# Add to push tables
if "'notices', 'student_auth']" in text:
    text = text.replace(
        "'notices', 'student_auth']",
        "'notices', 'student_auth', 'book_wishlist', 'book_ratings']"
    )

# Add unique keys for remote to local (pull)
pull_keys = """            elif table_name == 'notices':
                unique_key_cols = ['title', 'created_at']"""
new_pull_keys = """            elif table_name == 'notices':
                unique_key_cols = ['title', 'created_at']
            elif table_name == 'book_wishlist':
                unique_key_cols = ['book_id', 'enrollment_no']
            elif table_name == 'book_ratings':
                unique_key_cols = ['book_id', 'enrollment_no']"""

text = text.replace(pull_keys, new_pull_keys)

# Add create table logics for local to remote (push)
push_create_notices = """                elif table_name == 'student_auth':
                    remote_cursor.execute(\"\"\"
                        CREATE TABLE IF NOT EXISTS student_auth (
                            enrollment_no TEXT PRIMARY KEY,
                            password TEXT NOT NULL,
                            is_first_login INTEGER DEFAULT 1,
                            last_changed TIMESTAMP
                        )
                    \"\"\")
                    remote_conn.commit()"""

new_push_create = """                elif table_name == 'student_auth':
                    remote_cursor.execute(\"\"\"
                        CREATE TABLE IF NOT EXISTS student_auth (
                            enrollment_no TEXT PRIMARY KEY,
                            password TEXT NOT NULL,
                            is_first_login INTEGER DEFAULT 1,
                            last_changed TIMESTAMP
                        )
                    \"\"\")
                    remote_conn.commit()
                elif table_name == 'book_wishlist':
                    remote_cursor.execute(\"\"\"
                        CREATE TABLE IF NOT EXISTS book_wishlist (
                            id SERIAL PRIMARY KEY,
                            book_id TEXT NOT NULL,
                            enrollment_no TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(book_id, enrollment_no)
                        )
                    \"\"\")
                    remote_conn.commit()
                elif table_name == 'book_ratings':
                    remote_cursor.execute(\"\"\"
                        CREATE TABLE IF NOT EXISTS book_ratings (
                            id SERIAL PRIMARY KEY,
                            book_id TEXT NOT NULL,
                            enrollment_no TEXT NOT NULL,
                            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(book_id, enrollment_no)
                        )
                    \"\"\")
                    remote_conn.commit()"""

if "CREATE TABLE IF NOT EXISTS student_auth" in text:
    text = text.replace(push_create_notices, new_push_create)

# Add unique keys for local to remote (push)
push_keys = """            elif table_name == 'student_auth':
                unique_key_cols = ['enrollment_no']"""

new_push_keys = """            elif table_name == 'student_auth':
                unique_key_cols = ['enrollment_no']
            elif table_name == 'book_wishlist':
                unique_key_cols = ['book_id', 'enrollment_no']
            elif table_name == 'book_ratings':
                unique_key_cols = ['book_id', 'enrollment_no']"""

text = text.replace(push_keys, new_push_keys)

# Handle updates for book_ratings in push
# Find student auth update logic
update_logic = """                        if table_name == 'student_auth':
                            update_cols = []
                            update_vals = []
                            for lc in local_columns:
                                if lc in column_map and lc not in unique_key_cols:
                                    update_cols.append(f"{column_map[lc]} = %s")
                                    update_vals.append(row_dict[lc])
                            if update_cols:
                                update_vals.extend(unique_vals)
                                update_query = f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE {where_clause}"
                                remote_cursor.execute(update_query, update_vals)"""

new_update_logic = """                        if table_name == 'student_auth' or table_name == 'book_ratings':
                            update_cols = []
                            update_vals = []
                            for lc in local_columns:
                                if lc in column_map and lc not in unique_key_cols:
                                    update_cols.append(f"{column_map[lc]} = %s")
                                    update_vals.append(row_dict[lc])
                            if update_cols:
                                update_vals.extend(unique_vals)
                                update_query = f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE {where_clause}"
                                remote_cursor.execute(update_query, update_vals)"""

text = text.replace(update_logic, new_update_logic)

# Handle update for remote to local (pull) as well
pull_update_logic = """                        if table_name == 'student_auth':
                            update_cols = []
                            update_vals = []
                            for rc in remote_columns:
                                if rc in column_map and rc not in unique_key_cols:
                                    update_cols.append(f"{column_map[rc]} = ?")
                                    update_vals.append(row_dict[rc])
                            if update_cols:
                                update_vals.extend(unique_vals)
                                update_query = f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE {where_clause_local}"
                                local_cursor.execute(update_query, update_vals)"""

new_pull_update_logic = """                        if table_name == 'student_auth' or table_name == 'book_ratings':
                            update_cols = []
                            update_vals = []
                            for rc in remote_columns:
                                if rc in column_map and rc not in unique_key_cols:
                                    update_cols.append(f"{column_map[rc]} = ?")
                                    update_vals.append(row_dict[rc])
                            if update_cols:
                                update_vals.extend(unique_vals)
                                update_query = f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE {where_clause_local}"
                                local_cursor.execute(update_query, update_vals)"""

text = text.replace(pull_update_logic, new_pull_update_logic)

# Also adding them to _NATURAL_KEY_MAP
nat_key_old = """        'deletion_requests': ('student_id', 'timestamp'),
    }"""
nat_key_new = """        'deletion_requests': ('student_id', 'timestamp'),
        'book_wishlist':     ('book_id', 'enrollment_no'),
        'book_ratings':      ('book_id', 'enrollment_no'),
    }"""
text = text.replace(nat_key_old, nat_key_new)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Pushed all updates to sync_manager.py")
