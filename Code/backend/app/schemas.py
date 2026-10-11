from pydantic import BaseModel,Field
class QueryRequest(BaseModel):question:str=Field(min_length=3);document_filter:list[str]|None=None
class Citation(BaseModel):document:str;page:int;section:str='Unknown';score:float;quote:str
class QueryResponse(BaseModel):answer:str;response_mode:str;is_llm_generated:bool;provider_status:str;provider:str;model:str;failure_reason:str|None=None;citations:list[Citation];warning:str|None=None
