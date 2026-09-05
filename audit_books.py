"""
Check for:
1. Duplicate books (same title+author, different entries)
2. ISBN field actually containing publisher name
3. Books where the accession numbers from the Excel don't match what's in DB
4. Category is always 'Technology' even for non-tech books
"""
import sqlite3

conn = sqlite3.connect('LibraryApp/library.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Check for duplicates
print("=== POTENTIAL DUPLICATES (same title, different author spelling) ===")
cur.execute("SELECT book_id, title, author, total_copies, barcode FROM books ORDER BY title")
rows = cur.fetchall()

title_groups = {}
for row in rows:
    t = (row['title'] or '').strip().lower()
    if t not in title_groups:
        title_groups[t] = []
    title_groups[t].append(row)

dups_found = 0
for title, group in title_groups.items():
    if len(group) > 1:
        # Different authors or same author different spellings?
        authors = set((r['author'] or '').strip().lower() for r in group)
        if len(authors) > 1:
            dups_found += 1
            if dups_found <= 20:
                print(f"\n  Title: '{group[0]['title']}'")
                for r in group:
                    barcode = r['barcode'] or ''
                    print(f"    [{r['book_id']}] Author='{r['author']}' Copies={r['total_copies']} Barcode={barcode[:30]}")
        elif len(authors) == 1:
            # Same author - true duplicate entries
            dups_found += 1
            if dups_found <= 20:
                print(f"\n  EXACT DUP Title: '{group[0]['title']}'")
                for r in group:
                    barcode = r['barcode'] or ''
                    print(f"    [{r['book_id']}] Author='{r['author']}' Copies={r['total_copies']} Barcode={barcode[:30]}")
print(f"\nTotal potential duplicates: {dups_found}")

# 2. How is isbn field used?
print("\n\n=== ISBN FIELD USAGE ===")
cur.execute("SELECT isbn, COUNT(*) as cnt FROM books GROUP BY isbn ORDER BY cnt DESC LIMIT 20")
for row in cur.fetchall():
    print(f"  '{row['isbn']}' -> {row['cnt']} books")

# 3. What categories exist?
print("\n\n=== CATEGORIES ===")
cur.execute("SELECT category, COUNT(*) as cnt FROM books GROUP BY category ORDER BY cnt DESC")
for row in cur.fetchall():
    print(f"  '{row['category']}' -> {row['cnt']} books")
