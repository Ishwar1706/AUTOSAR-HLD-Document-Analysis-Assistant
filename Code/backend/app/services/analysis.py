from collections import Counter

def confidence(evidence,ocr=False,approved=True):
    if not evidence:return {'level':'INSUFFICIENT','score':0}
    top=evidence[0]['score']; support=sum(x['score']>=max(.45,top-.12) for x in evidence)
    score=min(1,.55*top+.1*min(support,3)+(.1 if approved else 0)-(.1 if ocr else 0))
    return {'level':'HIGH' if score>=.75 else 'MEDIUM' if score>=.55 else 'LOW','score':round(score,3)}

def compare(a,b):
    ka={(x['entity_type'],x['name']) for x in a}; kb={(x['entity_type'],x['name']) for x in b}
    return {'added':[{'type':x[0],'name':x[1]} for x in sorted(kb-ka)],'removed':[{'type':x[0],'name':x[1]} for x in sorted(ka-kb)],'unchanged_count':len(ka&kb)}
