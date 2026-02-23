import sqlite3
from pathlib import Path
base=Path(r"d:\vehicle\37ab1612-c285-4314-b32a-6a06d35d6d84\Default")

def tb_counts(db_path, tables):
    out={}
    conn=sqlite3.connect(str(db_path))
    c=conn.cursor()
    for t in tables:
        try:
            cnt=c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception as e:
            cnt=str(e)
        out[t]=cnt
    conn.close()
    return out

# Cookies
p1=base/'Cookies'
if p1.exists():
    print('Cookies counts:', tb_counts(p1,['cookies']))
# Logins
p2=base/'Login Data'
if p2.exists():
    print('Logins count:', tb_counts(p2,['logins']))
# History urls
p3=base/'History'
if p3.exists():
    print('History urls count:', tb_counts(p3,['urls']))
    conn=sqlite3.connect(str(p3))
    c=conn.cursor()
    print('\nTop 10 most visited urls:')
    for r in c.execute('SELECT url, visit_count, title FROM urls ORDER BY visit_count DESC LIMIT 10'):
        print(r)
    conn.close()

# Top Sites
p4=base/'Top Sites'
if p4.exists():
    print('\nTop sites:')
    conn=sqlite3.connect(str(p4))
    c=conn.cursor()
    for r in c.execute('SELECT url, url_rank, title FROM top_sites LIMIT 20'):
        print(r)
    conn.close()
