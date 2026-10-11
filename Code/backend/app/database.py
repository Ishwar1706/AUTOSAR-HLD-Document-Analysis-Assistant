import sqlite3, json, datetime
from pathlib import Path
DB=Path('./storage/autohld.db')

def connect():
    DB.parent.mkdir(parents=True,exist_ok=True); c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=connect(); c.executescript("""
    CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY,name TEXT UNIQUE,description TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,project_id INTEGER,name TEXT,doc_id TEXT,version TEXT,status TEXT,domain TEXT,sha256 TEXT UNIQUE,pages INTEGER,native_pages INTEGER,ocr_pages INTEGER,created_at TEXT);
    CREATE TABLE IF NOT EXISTS entities(id INTEGER PRIMARY KEY,document_id INTEGER,entity_type TEXT,entity_id TEXT,name TEXT,attributes TEXT,page INTEGER,section TEXT,confidence REAL,review_status TEXT DEFAULT 'UNREVIEWED');
    CREATE TABLE IF NOT EXISTS relationships(id INTEGER PRIMARY KEY,document_id INTEGER,source TEXT,target TEXT,relation_type TEXT,interface TEXT,page INTEGER,evidence TEXT,confidence REAL,review_status TEXT DEFAULT 'UNREVIEWED');
    CREATE TABLE IF NOT EXISTS findings(id INTEGER PRIMARY KEY,document_id INTEGER,finding_type TEXT,severity TEXT,entity TEXT,evidence TEXT,page INTEGER,status TEXT DEFAULT 'UNREVIEWED',reviewer TEXT,comment TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,item_type TEXT,item_id INTEGER,decision TEXT,reviewer TEXT,comment TEXT,corrected_value TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,event_type TEXT,details TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS queries(id INTEGER PRIMARY KEY,question TEXT,answer TEXT,response_mode TEXT,provider TEXT,model TEXT,citations TEXT,confidence TEXT,created_at TEXT);
    """); c.commit(); c.close()

def audit(event,details):
    c=connect(); c.execute('INSERT INTO audit(event_type,details,created_at) VALUES(?,?,?)',(event,json.dumps(details),datetime.datetime.utcnow().isoformat())); c.commit(); c.close()

def rows(sql,args=()):
    c=connect(); out=[dict(x) for x in c.execute(sql,args).fetchall()]; c.close(); return out
init_db()
