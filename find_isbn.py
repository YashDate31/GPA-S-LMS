import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('LibraryApp/main.py', encoding='utf-8') as f:
    lines = f.readlines()
hits = [(i+1, l.rstrip()) for i, l in enumerate(lines) if 'isbn' in l.lower()]
print(f"Total isbn references: {len(hits)}")
for n, l in hits:
    print(f"{n}: {l[:150]}")
