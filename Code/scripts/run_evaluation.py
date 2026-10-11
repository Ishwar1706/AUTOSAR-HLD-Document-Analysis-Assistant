import csv,time,requests,sys
from pathlib import Path
qfile=Path('../Evaluation_Results/evaluation_questions.csv'); out=Path('../Evaluation_Results/measured_results.csv')
rows=list(csv.DictReader(qfile.open(encoding='utf-8'))); results=[]
for x in rows:
 t=time.perf_counter(); r=requests.post('http://127.0.0.1:8000/query',json={'question':x['question']},timeout=180); latency=time.perf_counter()-t; y=r.json()
 keyword=x['expected_answer_keyword'].lower(); ok=keyword in y['answer'].lower() if keyword!='insufficient evidence' else y['response_mode']=='insufficient_evidence'
 cited=any(c['document']==x['expected_document'] for c in y['citations'])
 results.append({**x,'actual_answer':y['answer'],'response_mode':y['response_mode'],'keyword_correct':ok,'expected_document_cited':cited,'latency_seconds':round(latency,3)})
with out.open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=results[0]);w.writeheader();w.writerows(results)
print('Questions:',len(results),'Accuracy:',sum(x['keyword_correct'] for x in results)/len(results),'Citation accuracy:',sum(x['expected_document_cited'] for x in results)/len(results));print(out)
