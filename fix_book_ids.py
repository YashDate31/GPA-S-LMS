"""
Fix all 35 book_id range issues.
The book_id should accurately represent the accession numbers.
For books with non-contiguous accessions from multiple sheets/batches,
book_id = "first_acc-last_acc" (the range of the FIRST batch), NOT spanning all batches.
"""
import sqlite3

conn = sqlite3.connect('LibraryApp/library.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT book_id, title, author, total_copies, barcode FROM books")
rows = cur.fetchall()

fixed = 0
for row in rows:
    bid = row['book_id'] or ''
    barcode = row['barcode'] or ''
    
    if not barcode:
        continue
    
    acc_list = [x.strip() for x in barcode.split(',') if x.strip()]
    if len(acc_list) <= 1:
        continue
    
    # Parse all accessions as integers
    try:
        nums = sorted(int(x) for x in acc_list)
    except:
        continue
    
    # Find contiguous groups
    groups = []
    current_group = [nums[0]]
    for i in range(1, len(nums)):
        if nums[i] == current_group[-1] + 1:
            current_group.append(nums[i])
        else:
            groups.append(current_group)
            current_group = [nums[i]]
    groups.append(current_group)
    
    # Build the proper book_id from the FIRST contiguous group
    first_group = groups[0]
    if len(first_group) == 1:
        correct_book_id = str(first_group[0])
    else:
        correct_book_id = f"{first_group[0]}-{first_group[-1]}"
    
    if correct_book_id != bid:
        # Check no collision
        cur.execute("SELECT 1 FROM books WHERE book_id=? AND book_id!=?", (correct_book_id, bid))
        if cur.fetchone():
            # Collision — fall back to full range  
            if len(nums) == 1:
                correct_book_id = str(nums[0])
            else:
                correct_book_id = f"{nums[0]}-{nums[-1]}"
            if correct_book_id == bid:
                continue
            cur.execute("SELECT 1 FROM books WHERE book_id=? AND book_id!=?", (correct_book_id, bid))
            if cur.fetchone():
                print(f"SKIP (collision): [{bid}] -> [{correct_book_id}]")
                continue
        
        # Also update any borrow_records that reference this book_id
        cur.execute("UPDATE borrow_records SET book_id=?, updated_at=CURRENT_TIMESTAMP WHERE book_id=?", (correct_book_id, bid))
        cur.execute("UPDATE books SET book_id=?, updated_at=CURRENT_TIMESTAMP WHERE book_id=?", (correct_book_id, bid))
        print(f"FIXED: [{bid}] -> [{correct_book_id}] ({row['title'][:50]})")
        fixed += 1

conn.commit()
conn.close()
print(f"\nTotal fixed: {fixed}")
