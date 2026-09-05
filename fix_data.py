+"""
Fix ONLY the clearly broken data issues. 
DO NOT touch anything that is ambiguous.

Issues to fix:
1. EXACT DUPLICATE: 'Discrete Mathematics & Its Applications' has two entries
   with book_id '429, 12666' and '429,12666' (space difference) — merge them.
2. Author name spelling variants that are clearly the same person:
   - 'B.K. Sharma' vs 'B.K.Sharma' (Industrial Chemistry) 
   - 'ADAIR JOHN' vs 'JOHN ADAIR' (same person)
   - 'ANDREW S. TANENBAUM' vs 'Andrew Tanenbaum' (same person)  
   - 'ACHYUT S. GODBOLE' vs 'GODBOLE ACHUT' vs 'Acyut.S.Godbole' (same person)
   - 'LOUIS E FRENZEL' vs 'FRENZEL' (same person)
   - 'Godbole' vs 'Achyut Godbole' (Demystifying Computers)
   - 'Junaid Khateeb' vs 'Khateeb' (Computer Programming in Java)
   - 'BISHOP SUE' vs 'SUE BISHOP' (same person)
   - 'LOWE PHILL' vs 'PHIL LOWE' (same person)
   - 'Erwin Kreyszig' vs 'H.K.Das' - DIFFERENT authors, NOT duplicates
"""
import sqlite3

conn = sqlite3.connect('LibraryApp/library.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

fixed = 0

# 1. Fix the exact duplicate: merge '429, 12666' into '429,12666'
# (or vice versa — whichever exists)
cur.execute("SELECT book_id, total_copies, available_copies, barcode FROM books WHERE book_id IN ('429, 12666', '429,12666')")
dups = cur.fetchall()
if len(dups) == 2:
    # Keep the one without space, delete the other
    keep = None
    delete = None
    for d in dups:
        if d['book_id'] == '429,12666':
            keep = d
        else:
            delete = d
    if keep and delete:
        # Update borrow_records referencing the deleted book_id
        cur.execute("UPDATE borrow_records SET book_id=?, updated_at=CURRENT_TIMESTAMP WHERE book_id=?",
                    (keep['book_id'], delete['book_id']))
        cur.execute("DELETE FROM books WHERE book_id=?", (delete['book_id'],))
        print(f"FIXED: Deleted duplicate entry '{delete['book_id']}', kept '{keep['book_id']}'")
        fixed += 1
    else:
        print("  Could not identify keep/delete for Discrete Mathematics duplicate")
elif len(dups) == 1:
    # Only one exists, fix the space if needed
    d = dups[0]
    if ' ' in d['book_id']:
        new_id = d['book_id'].replace(' ', '')
        cur.execute("SELECT 1 FROM books WHERE book_id=?", (new_id,))
        if not cur.fetchone():
            cur.execute("UPDATE borrow_records SET book_id=?, updated_at=CURRENT_TIMESTAMP WHERE book_id=?",
                        (new_id, d['book_id']))
            cur.execute("UPDATE books SET book_id=?, updated_at=CURRENT_TIMESTAMP WHERE book_id=?",
                        (new_id, d['book_id']))
            print(f"FIXED: Removed space from book_id '{d['book_id']}' -> '{new_id}'")
            fixed += 1

conn.commit()
print(f"\nTotal fixes applied: {fixed}")
conn.close()
