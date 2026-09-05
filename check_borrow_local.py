import sqlite3

conn = sqlite3.connect('LibraryApp/library.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM borrow_records WHERE enrollment_no='24210270242'")
rows = cur.fetchall()
for row in rows:
    print(dict(row))
