import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('c:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/.env')
db_url = os.getenv('DATABASE_URL')

if not db_url:
    print("No DATABASE_URL found in .env")
    exit(1)

print("Connecting to Supabase to wipe tables...")
try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO public;")
    print("Successfully dropped and recreated public schema on Supabase.")
except Exception as e:
    print(f"Error wiping Supabase: {e}")

# Delete local databases
local_paths = [
    'c:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/LibraryApp/library.db',
    'c:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/LibraryApp/Web-Extension/portal.db',
    'c:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/LibraryApp/sync_log.json'
]

for p in local_paths:
    if os.path.exists(p):
        try:
            os.remove(p)
            print(f"Deleted local file: {p}")
        except Exception as e:
            print(f"Failed to delete {p}: {e}")
    else:
        print(f"File not found (already deleted): {p}")

print("Wipe complete.")
