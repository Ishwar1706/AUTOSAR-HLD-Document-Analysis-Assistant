from openai import OpenAI
from backend.app.config import settings
def spec(p):return (settings.groq_base_url,settings.groq_api_key,settings.groq_model) if p=='groq' else (settings.ollama_base_url,settings.ollama_api_key,settings.ollama_model)
def generate(q,e,p=None):
 p=p or settings.llm_provider;base,key,model=spec(p)
 if p=='groq' and (not key or 'replace_' in key):raise RuntimeError('GROQ_API_KEY not configured')
 ctx='\n\n'.join(f'[SOURCE {i+1}] {x["metadata"]["source"]}, page {x["metadata"]["page"]}\n{x["text"]}' for i,x in enumerate(e));prompt=f'Use only evidence. Cite as [SOURCE n]. If insufficient answer exactly INSUFFICIENT_EVIDENCE.\nQuestion: {q}\n{ctx}';c=OpenAI(base_url=base,api_key=key,timeout=settings.llm_timeout_seconds);z=c.chat.completions.create(model=model,messages=[{'role':'user','content':prompt}],temperature=settings.llm_temperature,max_tokens=settings.llm_max_output_tokens);return z.choices[0].message.content.strip(),p,model
