import os,requests,streamlit as st,pandas as pd
from dotenv import load_dotenv
load_dotenv(); API=os.getenv('BACKEND_URL','http://127.0.0.1:8000')
st.set_page_config(page_title='AutoHLD Insight',page_icon='A',layout='wide')
st.title('AutoHLD Insight'); st.caption('HLD intelligence: OCR, grounded RAG, architecture extraction, comparison, review, audit, and evaluation')
def get(path):
 r=requests.get(API+path,timeout=120); r.raise_for_status(); return r.json()
def post(path,**kw):
 r=requests.post(API+path,timeout=600,**kw); r.raise_for_status(); return r.json()
with st.sidebar:
 try: h=get('/health'); st.success('Backend connected'); st.json(h)
 except Exception as e: st.error(f'Backend unavailable: {e}')
 pages=['Dashboard','Project Workspace','Upload & Ingest','Document Library','Grounded Q&A','Architecture Inventory','Dependency Map','Consistency Checks','Revision Comparison','Engineer Review','Audit History','Export Center','Evaluation','System Configuration']
 page=st.radio('Navigate',pages)
if page=='Dashboard':
 docs=get('/documents'); ents=get('/v2/entities'); rels=get('/v2/relationships'); finds=get('/v2/findings')
 a,b,c,d=st.columns(4);a.metric('Documents',len(docs));b.metric('Entities',len(ents));c.metric('Relationships',len(rels));d.metric('Findings',len(finds))
 st.info('All AI-assisted findings require engineering review. This prototype does not certify automotive architecture.')
elif page=='Project Workspace':
 st.subheader('Project workspaces'); name=st.text_input('Project name'); desc=st.text_area('Description')
 if st.button('Create project') and name: post('/v2/projects',json={'name':name,'description':desc});st.rerun()
 st.dataframe(get('/v2/projects'),use_container_width=True)
elif page=='Upload & Ingest':
 fs=st.file_uploader('Choose HLD PDFs',type=['pdf'],accept_multiple_files=True)
 if st.button('Ingest documents',type='primary',disabled=not fs):
  for f in fs:
   with st.spinner(f'Processing {f.name}'): x=post('/documents/upload',files={'file':(f.name,f.getvalue(),'application/pdf')})
   st.success(f'{f.name}: {x["pages"]} pages, {x["ocr_pages"]} OCR pages, {x["chunks_added"]} chunks added')
elif page=='Document Library':
 st.dataframe([{k:v for k,v in x.items() if k!='page_details'} for x in get('/documents')],use_container_width=True)
elif page=='Grounded Q&A':
 q=st.text_input('Question');
 if st.button('Ask',type='primary',disabled=len(q)<3):
  x=post('/query',json={'question':q})
  if x['response_mode']=='deterministic_fallback':st.error('LLM generation failed. This is a deterministic evidence-based answer, NOT an LLM answer.')
  elif x['response_mode']=='insufficient_evidence':st.warning('Insufficient evidence')
  else:st.success('Grounded LLM answer')
  st.write(x['answer']);st.caption(f'Mode: {x["response_mode"]} | {x["provider"]} | {x["model"]}')
  for i,c in enumerate(x['citations'],1):
   with st.expander(f'[{i}] {c["document"]}, page {c["page"]}, score {c["score"]}'):st.write(c['quote'])
elif page=='Architecture Inventory':
 typ=st.selectbox('Entity type',['all','component','interface','port','signal','event','component_id']); path='/v2/entities'+('' if typ=='all' else f'?entity_type={typ}')
 st.dataframe(get(path),use_container_width=True)
elif page=='Dependency Map':
 data=get('/v2/relationships');st.dataframe(data,use_container_width=True)
 if data:
  import plotly.graph_objects as go
  nodes=sorted(set([x['source'] for x in data]+[x['target'] for x in data])); idx={n:i for i,n in enumerate(nodes)}
  st.plotly_chart(go.Figure(go.Sankey(node={'label':nodes},link={'source':[idx[x['source']] for x in data],'target':[idx[x['target']] for x in data],'value':[1]*len(data)})),use_container_width=True)
elif page=='Consistency Checks':
 st.warning('Potential findings require engineer review.');st.dataframe(get('/v2/findings'),use_container_width=True)
elif page=='Revision Comparison':
 st.info('Select database document IDs after both revisions are ingested.');a=st.number_input('Baseline document ID',1,step=1);b=st.number_input('Candidate document ID',2,step=1)
 if st.button('Compare'):st.json(get(f'/v2/compare?document_a={a}&document_b={b}'))
elif page=='Engineer Review':
 item=st.selectbox('Item type',['finding','entity','relationship']); iid=st.number_input('Item ID',1,step=1);decision=st.selectbox('Decision',['ACCEPTED','REJECTED','CORRECTED','NEEDS_CLARIFICATION']);reviewer=st.text_input('Reviewer','Engineer');comment=st.text_area('Comment')
 if st.button('Save review'):post('/v2/reviews',json={'item_type':item,'item_id':iid,'decision':decision,'reviewer':reviewer,'comment':comment,'corrected_value':''});st.success('Review saved')
elif page=='Audit History':st.dataframe(get('/v2/audit'),use_container_width=True)
elif page=='Export Center':
 table=st.selectbox('Dataset',['documents','entities','relationships','findings','reviews','audit','queries']);fmt=st.selectbox('Format',['csv','json'])
 if st.button('Generate export'):st.success(get(f'/v2/exports/{table}?fmt={fmt}')['path'])
elif page=='Evaluation':
 st.subheader('Evaluation framework');st.write('Run scripts/run_evaluation.py after ingesting all documents. Results are written to Evaluation_Results.')
 try: st.dataframe(pd.read_csv('../Evaluation_Results/evaluation_questions.csv'),use_container_width=True)
 except: st.warning('Evaluation question file not found.')
else:
 st.json(get('/health')); st.code("Primary: Groq openai/gpt-oss-120b\nEmbeddings: BAAI/bge-small-en-v1.5\nVector store: ChromaDB\nOCR: Tesseract")
