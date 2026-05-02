import sqlite3, json, os

db_paths = [
    r'\\wsl.localhost\Ubuntu\home\eclaw\EbookDatabase\instance\DX_2.0-5.0.db',
    r'\\wsl.localhost\Ubuntu\home\eclaw\EbookDatabase\instance\DX_6.0.db',
]

for db in db_paths:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        print(f'{os.path.basename(db)} tables: {tables}')
        for t in tables:
            c.execute(f'PRAGMA table_info({t})')
            cols = [(r[1], r[2]) for r in c.fetchall()]
            print(f'  {t}: {[c[0] for c in cols]}')
        conn.close()
    else:
        print(f'{os.path.basename(db)}: not found')
