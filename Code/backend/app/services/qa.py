import re
from backend.app.config import settings
from backend.app.services.vector_store import store
from backend.app.services.llm import generate,spec
def deterministic(q,e):
 terms=[x.lower() for x in re.findall(r'[A-Za-z_][A-Za-z0-9_]+',q)];ss=[]
 for x in e:
  for s in re.split(r'(?<=[.!?])\s+|\n+',x['text']):
   if sum(t in s.lower() for t in terms)>=2:ss.append(s.strip())
 return ' '.join(ss[:3]) or 'Insufficient evidence found in the selected HLD documents.'
def answer(q,docs=None):
 e=store.query(q,settings.vector_top_k,docs)[:settings.final_top_k];c=[{'document':x['metadata']['source'],'page':x['metadata']['page'],'section':x['metadata'].get('section','Unknown'),'score':x['score'],'quote':x['text'][:360]} for x in e];model=spec(settings.llm_provider)[2]
 if not e or e[0]['score']<settings.minimum_relevance_score:return {'answer':'Insufficient evidence found in the selected HLD documents.','response_mode':'insufficient_evidence','is_llm_generated':False,'provider_status':'not_called','provider':settings.llm_provider,'model':model,'citations':c}
 try:
  t,p,m=generate(q,e);return {'answer':'Insufficient evidence found in the selected HLD documents.' if t=='INSUFFICIENT_EVIDENCE' else t,'response_mode':'insufficient_evidence' if t=='INSUFFICIENT_EVIDENCE' else 'llm_grounded','is_llm_generated':t!='INSUFFICIENT_EVIDENCE','provider_status':'success','provider':p,'model':m,'citations':c}
 except Exception as ex:return {'answer':deterministic(q,e),'response_mode':'deterministic_fallback','is_llm_generated':False,'provider_status':'failed','provider':settings.llm_provider,'model':model,'failure_reason':str(ex),'citations':c,'warning':'LLM generation failed. This is a deterministic fallback, not an LLM answer.'}
