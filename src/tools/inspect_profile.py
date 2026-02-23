import sqlite3
from pathlib import Path
import json

base=Path(r"d:\vehicle\37ab1612-c285-4314-b32a-6a06d35d6d84\Default")
files=["Cookies","History","Login Data","Web Data","Top Sites"]
for f in files:
    p=base/f
    if p.exists():
        print('\n===',f,'===')
        try:
            conn=sqlite3.connect(str(p))
            c=conn.cursor()
            for row in c.execute("SELECT name, sql FROM sqlite_master WHERE type='table';"):
                print('\nTABLE:',row[0])
                print(row[1])
            # show up to 5 rows from each table
            for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table';"):
                print('\n-- sample from',t,'--')
                try:
                    for r in c.execute(f"SELECT * FROM {t} LIMIT 5;"):
                        print(r)
                except Exception as e:
                    print('ERROR reading',t,e)
            conn.close()
        except Exception as e:
            print('Cannot open as sqlite',e)
    else:
        print('Missing',f)

# Read Preferences (JSON)
pref=base/'Preferences'
if pref.exists():
    print('\n=== Preferences (first 300 lines) ===')
    with open(pref,'r',encoding='utf-8',errors='replace') as fh:
        for i,l in enumerate(fh):
            if i>300: break
            print(l.rstrip())
else:
    print('Preferences missing')
