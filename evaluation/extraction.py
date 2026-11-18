"""Sentence-ID scoring, independent from provider quality or task-field metrics."""
def score(gold: set, predicted: set) -> dict:
    tp,fp,fn=len(gold & predicted),len(predicted-gold),len(gold-predicted)
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,'f1':f1}


def evidence_ids(sentences: list[dict], evidence: str) -> set[int]:
    text='\n'.join(s['s'] for s in sentences)
    # 一个证据可能跨多句；重复原文全部计入，作为明确保守的定位规则。
    locations=[];start=0
    while evidence and (start:=text.find(evidence,start))>=0:
        locations.append((start,start+len(evidence)));start+=1
    result=set();position=0
    for sentence in sentences:
        end=position+len(sentence['s'])
        if any(a<end and b>position for a,b in locations): result.add(sentence['id'])
        position=end+1
    return result
