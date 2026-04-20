import sys
import os

# Add LibraryApp directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database

def verify_schema():
    print("Initializing database...")
    db = Database()
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    print("Checking 'books' table info in library.db...")
    cursor.execute("PRAGMA table_info(books)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'cover_url' in columns:
        print("[SUCCESS] 'cover_url' column exists in 'books' table.")
    else:
        print("[FAILURE] 'cover_url' column NOT found in 'books' table.")
        print(f"Current columns: {columns}")
        
    conn.close()

if __name__ == "__main__":
    verify_schema()
