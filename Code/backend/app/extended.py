from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
import datetime,json
from backend.app.database import connect,rows,audit
from backend.app.services.analysis import compare
from backend.app.services.exports import export_table
router=APIRouter(prefix='/v2')
class ProjectIn(BaseModel): name:str; description:str=''
class ReviewIn(BaseModel): item_type:str; item_id:int; decision:str; reviewer:str='Engineer'; comment:str=''; corrected_value:str=''
@router.post('/projects')
def create_project(x:ProjectIn):
 c=connect(); c.execute('INSERT OR IGNORE INTO projects(name,description,created_at) VALUES(?,?,?)',(x.name,x.description,datetime.datetime.utcnow().isoformat())); c.commit(); c.close(); audit('PROJECT_CREATED',x.model_dump()); return {'ok':True}
@router.get('/projects')
def projects(): return rows('SELECT * FROM projects ORDER BY id DESC')
@router.get('/entities')
def entities(document_id:int|None=None,entity_type:str|None=None):
 q='SELECT * FROM entities WHERE 1=1'; a=[]
 if document_id:q+=' AND document_id=?';a.append(document_id)
 if entity_type:q+=' AND entity_type=?';a.append(entity_type)
 return rows(q,a)
@router.get('/relationships')
def relationships(): return rows('SELECT * FROM relationships')
@router.get('/findings')
def findings(): return rows('SELECT * FROM findings')
@router.post('/reviews')
def review(x:ReviewIn):
 c=connect(); c.execute('INSERT INTO reviews(item_type,item_id,decision,reviewer,comment,corrected_value,created_at) VALUES(?,?,?,?,?,?,?)',(x.item_type,x.item_id,x.decision,x.reviewer,x.comment,x.corrected_value,datetime.datetime.utcnow().isoformat()));
 if x.item_type in {'finding','entity','relationship'}: c.execute(f'UPDATE {x.item_type}s SET review_status=? WHERE id=?',(x.decision,x.item_id)) if x.item_type!='finding' else c.execute('UPDATE findings SET status=?,reviewer=?,comment=? WHERE id=?',(x.decision,x.reviewer,x.comment,x.item_id))
 c.commit();c.close();audit('REVIEW_RECORDED',x.model_dump());return {'ok':True}
@router.get('/audit')
def audits(): return rows('SELECT * FROM audit ORDER BY id DESC')
@router.get('/exports/{table}')
def export(table:str,fmt:str='csv'): return {'path':export_table(table,fmt)}
@router.get('/compare')
def comparison(document_a:int,document_b:int):
 return compare(rows('SELECT * FROM entities WHERE document_id=?',(document_a,)),rows('SELECT * FROM entities WHERE document_id=?',(document_b,)))
