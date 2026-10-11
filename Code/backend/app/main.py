from pathlib import Path
import hashlib,json,datetime
from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.schemas import QueryRequest,QueryResponse
from backend.app.services.extraction import extract_pdf,chunks
from backend.app.services.vector_store import store
from backend.app.services.qa import answer
from backend.app.services.entities import extract_entities,extract_relationships
from backend.app.database import connect,audit
from backend.app.extended import router
app=FastAPI(title='AutoHLD Insight API');app.include_router(router);app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
@app.get('/health')
def health():return {'status':'ok','provider':settings.llm_provider,'model':settings.groq_model,'vector_chunks':store.col.count(),'ocr_enabled':settings.enable_ocr}
@app.post('/documents/upload')
async def upload(file:UploadFile=File(...)):
 data=await file.read();safe=Path(file.filename).name;path=Path(settings.upload_directory)/safe;path.write_bytes(data);pages=extract_pdf(path);added=store.add(chunks(pages,safe));sha=hashlib.sha256(data).hexdigest();c=connect();c.execute("INSERT OR IGNORE INTO projects(id,name,description,created_at) VALUES(1,'Default Project','Auto-created',?)",(datetime.datetime.utcnow().isoformat(),));c.execute('INSERT OR IGNORE INTO documents(project_id,name,doc_id,version,status,domain,sha256,pages,native_pages,ocr_pages,created_at) VALUES(1,?,?,?,?,?,?,?,?,?,?)',(safe,safe,'unknown','REVIEW_CANDIDATE','unknown',sha,len(pages),sum(x['method']=='native' for x in pages),sum(x['method']=='ocr' for x in pages),datetime.datetime.utcnow().isoformat()));c.commit();did=c.execute('SELECT id FROM documents WHERE sha256=?',(sha,)).fetchone()[0]
 if c.execute('SELECT COUNT(*) FROM entities WHERE document_id=?',(did,)).fetchone()[0]==0:
  for e in extract_entities(pages):c.execute('INSERT INTO entities(document_id,entity_type,entity_id,name,attributes,page,section,confidence) VALUES(?,?,?,?,?,?,?,?)',(did,e['entity_type'],e['entity_id'],e['name'],json.dumps(e['attributes']),e['page'],e['section'],e['confidence']))
  for x in extract_relationships(pages):c.execute('INSERT INTO relationships(document_id,source,target,relation_type,interface,page,evidence,confidence) VALUES(?,?,?,?,?,?,?,?)',(did,x['source'],x['target'],x['relation_type'],x['interface'],x['page'],x['evidence'],x['confidence']))
 c.commit();c.close();record={'document':safe,'sha256':sha,'pages':len(pages),'native_pages':sum(x['method']=='native' for x in pages),'ocr_pages':sum(x['method']=='ocr' for x in pages),'chunks_added':added,'page_details':pages};(Path(settings.processed_directory)/(safe+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8');audit('DOCUMENT_INGESTED',record);return record
@app.get('/documents')
def docs():return [json.loads(p.read_text()) for p in Path(settings.processed_directory).glob('*.json')]
@app.post('/query',response_model=QueryResponse)
def query(x:QueryRequest):return answer(x.question,x.document_filter)
