import sys

def check_file(path, search_terms):
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        lines = f.readlines()
    print(f"\n=== {path} ({len(lines)} lines) ===")
    for i, line in enumerate(lines, 1):
        for term in search_terms:
            if term in line:
                print(f"  {i}: {line.rstrip()}")
                break

check_file(
    r'c:\Users\Yash\OneDrive\Desktop\GPA-S-LMS\LibraryApp\database.py',
    ['def get_connection', 'sqlite3.connect', 'journal_mode', 'busy_timeout', 'timeout=']
)

check_file(
    r'c:\Users\Yash\OneDrive\Desktop\GPA-S-LMS\LibraryApp\sync_manager.py',
    ['local_conn = sqlite3', 'journal_mode', 'busy_timeout', 'row_factory']
)

check_file(
    r'c:\Users\Yash\OneDrive\Desktop\GPA-S-LMS\LibraryApp\main.py',
    ['def _log_admin_activity', '_log_worker', 'daemon=True', 'book.get(', "b.get('barcode", "b.get('book_id", "book.get('barcode"]
)
