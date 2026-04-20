path = r'c:\Users\Yash\OneDrive\Desktop\GPA-S-LMS\LibraryApp\main.py'
with open(path, encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

target_lines = [(i+1, l.rstrip()) for i, l in enumerate(lines) if '_log_worker' in l or ('_log_admin_activity' in l and 'def' in l)]
for ln, text in target_lines:
    print(f'{ln}: {text}')
print('Total lines:', len(lines))
