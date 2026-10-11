from pathlib import Path
import csv,json
from backend.app.database import rows
OUT=Path('./storage/exports'); OUT.mkdir(parents=True,exist_ok=True)
def export_table(table,fmt='csv'):
    allowed={'documents','entities','relationships','findings','reviews','audit','queries'}
    if table not in allowed: raise ValueError('Unsupported export')
    data=rows(f'SELECT * FROM {table}')
    path=OUT/f'{table}.{fmt}'
    if fmt=='json': path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    else:
        with path.open('w',newline='',encoding='utf-8-sig') as f:
            if data:
                w=csv.DictWriter(f,fieldnames=data[0]); w.writeheader(); w.writerows(data)
    return str(path)
