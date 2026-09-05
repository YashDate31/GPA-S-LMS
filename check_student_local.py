import sqlite3

conn = sqlite3.connect('LibraryApp/library.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(students)")
cols = [col[1] for col in cur.fetchall()]
print("Columns:", cols)

cur.execute("SELECT * FROM students WHERE enrollment_no='24210270242'")
row = cur.fetchone()
print("Row:", row)

if 'synced_remote' in cols:
    print("synced_remote:", row[cols.index('synced_remote')])
