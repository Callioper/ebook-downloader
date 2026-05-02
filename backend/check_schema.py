import sqlite3, os, shutil

src = r'\\wsl.localhost\Ubuntu\home\eclaw\EbookDatabase\instance\DX_2.0-5.0.db'
dst = r'D:\opencode\ebook-downloader\tmp_check.db'

shutil.copy2(src, dst)

conn = sqlite3.connect(dst)
conn.execute("PRAGMA journal_mode=DELETE")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables)

for t in tables:
    c.execute('PRAGMA table_info("%s")' % t)
    cols = [(r[1], r[2]) for r in c.fetchall()]
    print('  %s: %s' % (t, [c[0] for c in cols]))
    c.execute('SELECT count(*) FROM "%s"' % t)
    print('  Rows: %s' % c.fetchone()[0])

    # First 2 rows
    col_names = [c[0] for c in cols]
    c.execute('SELECT * FROM "%s" LIMIT 2' % t)
    rows = c.fetchall()
    for row in rows:
        preview = dict(zip(col_names, row))
        for k, v in preview.items():
            if isinstance(v, str) and len(v) > 50:
                preview[k] = v[:50] + '...'
        print('  Sample: %s' % json.dumps(preview, ensure_ascii=False))

conn.close()
os.remove(dst)
