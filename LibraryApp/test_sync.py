import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sync_manager import SyncManager

local_db_path = "c:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/library.db"
if not os.path.exists(local_db_path):
    print("Trying other path")
    local_db_path = "c:/Users/Yash/OneDrive/Desktop/GPA-S-LMS/LibraryApp/library.db"

remote_config = os.getenv("DATABASE_URL")
if not remote_config:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
    remote_config = os.getenv("DATABASE_URL")

print(f"DATABASE_URL available: {bool(remote_config)}")

if not remote_config:
    print("No DATABASE_URL found")
    sys.exit(1)

manager = SyncManager(local_db_path, remote_config)
print("Starting sync...")
results = manager.sync_now(direction='both')
print("Sync results:")
import json
print(json.dumps(results, indent=2))
