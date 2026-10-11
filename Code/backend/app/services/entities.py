import re, json
from rapidfuzz import fuzz
ENTITY_PATTERNS={
 'component': r'\b(?:[A-Z][A-Za-z0-9]+(?:Manager|Coordinator|Adapter|Arbitrator|Collector|Router|Monitor))\b',
 'interface': r'\bIf_[A-Za-z0-9_]+\b',
 'port': r'\b(?:Pp|Rp)[A-Z][A-Za-z0-9_]+\b',
 'signal': r'\b[A-Z][A-Za-z0-9]+_(?:kph|rpm|pct|Nm|V)\b',
 'event': r'\bEVT-\d{3}\b',
 'component_id': r'\bSWC-[A-Z]{2}-\d{3}\b'
}
def extract_entities(pages):
    out=[]; seen=set()
    for p in pages:
        for typ,pat in ENTITY_PATTERNS.items():
            for m in re.finditer(pat,p['text']):
                val=m.group(0); key=(typ,val,p['page'])
                if key in seen: continue
                seen.add(key); out.append({'entity_type':typ,'entity_id':val if typ.endswith('_id') or typ=='event' else '', 'name':val,'attributes':{},'page':p['page'],'section':p.get('section','Unknown'),'confidence':0.92 if p['method']=='native' else max(.5,(p.get('ocr_confidence') or 50)/100)})
    return out

def extract_relationships(pages):
    out=[]
    for p in pages:
        text=' '.join(p['text'].split())
        patterns=[
          (r'(\w+(?:Manager|Coordinator|Adapter|Arbitrator|Collector|Router|Monitor)).{0,90}provides?\s+(If_\w+)','PROVIDES'),
          (r'(\w+(?:Manager|Coordinator|Adapter|Arbitrator|Collector|Router|Monitor)).{0,90}(?:consumes|requires)\s+(If_\w+)','REQUIRES'),
          (r'(\w+(?:Manager|Coordinator|Adapter|Arbitrator|Collector|Router|Monitor)).{0,90}publishes?.{0,40}(If_\w+)','PUBLISHES')]
        for pat,rel in patterns:
            for m in re.finditer(pat,text,re.I): out.append({'source':m.group(1),'target':m.group(2),'relation_type':rel,'interface':m.group(2),'page':p['page'],'evidence':m.group(0)[:300],'confidence':.8})
    return out
