from pathlib import Path
from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
 model_config=SettingsConfigDict(env_file='.env',extra='ignore')
 backend_url:str='http://127.0.0.1:8000';llm_provider:str='groq';groq_api_key:str='';groq_base_url:str='https://api.groq.com/openai/v1';groq_model:str='openai/gpt-oss-120b';ollama_base_url:str='http://localhost:11434/v1';ollama_api_key:str='ollama';ollama_model:str='gpt-oss:20b';enable_provider_fallback:bool=False;enable_deterministic_fallback:bool=True;embedding_model:str='BAAI/bge-small-en-v1.5';chroma_persist_directory:str='./storage/chroma';chroma_collection_name:str='autohld_documents';upload_directory:str='./storage/uploads';processed_directory:str='./storage/processed';export_directory:str='./storage/exports';enable_ocr:bool=True;ocr_language:str='eng';ocr_dpi:int=300;ocr_min_native_characters:int=80;ocr_min_confidence:float=45;chunk_size:int=900;chunk_overlap:int=130;vector_top_k:int=10;final_top_k:int=5;minimum_relevance_score:float=.2;llm_temperature:float=.1;llm_max_output_tokens:int=1400;llm_timeout_seconds:int=90
settings=Settings()
for d in [settings.upload_directory,settings.processed_directory,settings.export_directory,settings.chroma_persist_directory]:Path(d).mkdir(parents=True,exist_ok=True)
