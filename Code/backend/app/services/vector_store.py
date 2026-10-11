import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from backend.app.config import settings
class Store:
 def __init__(self):
  self.client=chromadb.PersistentClient(path=settings.chroma_persist_directory);self.col=self.client.get_or_create_collection(settings.chroma_collection_name,embedding_function=SentenceTransformerEmbeddingFunction(model_name=settings.embedding_model),metadata={'hnsw:space':'cosine'})
 def add(self,c):
  existing=set(self.col.get(ids=[x['id'] for x in c]).get('ids',[]));n=[x for x in c if x['id'] not in existing]
  if n:self.col.add(ids=[x['id'] for x in n],documents=[x['text'] for x in n],metadatas=[x['metadata'] for x in n])
  return len(n)
 def query(self,q,n=10,docs=None):
  if self.col.count()==0:return []
  r=self.col.query(query_texts=[q],n_results=min(n,self.col.count()),where={'source':{'$in':docs}} if docs else None,include=['documents','metadatas','distances']);return [{'text':t,'metadata':m,'score':round(1-float(d),4)} for t,m,d in zip(r['documents'][0],r['metadatas'][0],r['distances'][0])]
store=Store()
