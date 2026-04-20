#!/usr/bin/env python3
"""Patches _log_admin_activity in main.py to use a fire-and-forget background thread (Bug 3 fix)."""

import re

path = r'c:\Users\Yash\OneDrive\Desktop\GPA-S-LMS\LibraryApp\main.py'

with open(path, encoding='utf-8', errors='replace') as f:
    content = f.read()

# Detect line endings
crlf = '\r\n' in content
nl = '\r\n' if crlf else '\n'

# Build search pattern — handle both CRLF and LF
# We search for the function definition up to and including the closing except block
pattern = re.compile(
    r'(    def _log_admin_activity\(self, action, details\):.*?'
    r'print\(f"Error logging admin activity: \{e\}"\))',
    re.DOTALL
)

replacement = (
    '    def _log_admin_activity(self, action, details):\n'
    '        """Log admin activity to database asynchronously (fire-and-forget).\n'
    '\n'
    '        Running this in a background thread prevents it from opening a competing\n'
    '        SQLite connection inside a UI callback that fires immediately after a\n'
    '        borrow/return commit -- the secondary trigger path for \'database is locked\'.\n'
    '        """\n'
    '        def _log_worker():\n'
    '            try:\n'
    '                conn = self.db.get_connection()\n'
    '                c = conn.cursor()\n'
    '                timestamp = datetime.now().strftime(\'%Y-%m-%d %H:%M:%S\')\n'
    '                c.execute(\n'
    '                    \'INSERT INTO admin_activity (timestamp, action, details, admin_user) VALUES (?, ?, ?, ?)\',\n'
    '                    (timestamp, action, details, \'Admin\')\n'
    '                )\n'
    '                conn.commit()\n'
    '                conn.close()\n'
    '            except Exception as e:\n'
    '                print(f"Error logging admin activity: {e}")\n'
    '        import threading as _threading\n'
    '        _threading.Thread(target=_log_worker, daemon=True).start()'
)

m = pattern.search(content)
if m:
    print(f"Match found at positions {m.start()} to {m.end()}")
    print("Matched text preview:", repr(m.group()[:120]))
    new_content = content[:m.start()] + replacement + content[m.end():]
    
    # Write back preserving original line endings for the file overall
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(new_content)
    print("SUCCESS: _log_admin_activity patched to async.")
else:
    print("ERROR: Pattern not found. Dumping lines 3405-3440 for inspection:")
    lines = content.splitlines()
    for i in range(3404, min(3441, len(lines))):
        print(f"  {i+1}: {repr(lines[i])}")
