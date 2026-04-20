#!/usr/bin/env python3
"""
Fix all sqlite3.Row .get() crash sites in main.py.

sqlite3.Row does NOT support .get(key, default) — it only supports subscript
access b['col'] and will raise AttributeError on .get().  The 6 barcode
lookup sites all call .get('barcode', '') on a Row returned by get_books().

Fix: replace each pattern with the equivalent try/subscript or ternary form.
"""

path = r'c:\Users\Yash\OneDrive\Desktop\GPA-S-LMS\LibraryApp\main.py'

with open(path, encoding='utf-8-sig', errors='replace') as f:
    content = f.read()

original = content  # keep for diff reporting

replacements = [
    # Lines 5643 / 5893 — inside for-loop: b.get('barcode', '') or ''
    (
        "barcode = str(b.get('barcode', '') or '').lower()\n"
        "                    if query_lower in book_id or query_lower in title or query_lower in author or query_lower in barcode:",
        "barcode = str(b['barcode'] if b['barcode'] else '').lower()\n"
        "                    if query_lower in book_id or query_lower in title or query_lower in author or query_lower in barcode:"
    ),
    # Lines 5651 / 5901 — format_book_display / format_return_book_display
    (
        "barcode_str = f\" [Barcode: {book.get('barcode')}]\" if book.get('barcode') else \"\"",
        "barcode_str = (f\" [Barcode: {book['barcode']}]\" if book['barcode'] else \"\")"
    ),
    # Lines 5666 / 5916 — on_borrow_barcode_scan / on_return_barcode_scan
    (
        "barcode = str(b.get('barcode', '') or '')\n"
        "                        if barcode and barcode.lower() == query.lower():",
        "barcode = str(b['barcode'] if b['barcode'] else '')\n"
        "                        if barcode and barcode.lower() == query.lower():"
    ),
]

count = 0
for old, new in replacements:
    occurrences = content.count(old)
    if occurrences == 0:
        print(f"WARNING: pattern not found:\n  {repr(old[:80])}")
    else:
        content = content.replace(old, new)
        count += occurrences
        print(f"OK: replaced {occurrences}x — {repr(old[:60])}")

if content != original:
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print(f"\nSUCCESS: {count} replacements written to {path}")
else:
    print("\nNo changes made — all patterns already fixed or not found.")
