"""Frozen 30-meeting holdout; production extraction, resumable evidence and bounded HTTP."""
import argparse
import hashlib
import json
import random
import time
from collections import defaultdict
from pathlib import Path
from urllib.request import getproxies
import httpx
from app.core.config import Settings
from app.llm.client import LLMClient, LLMError
from app.llm.extraction import extract, text_windows
from evaluation.extraction import evidence_ids, score
from scripts.evaluate_extraction import records
from scripts.audit_alimeeting4mug import DEFAULT_ARCHIVE

ROOT = Path('outputs/evaluations')
MANIFEST = Path('evaluation/action_item_eval_manifest.jsonl')
SEED = 20261119

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)

def select():
    clean = json.loads(Path('data/processed/clean_split.json').read_text())
    assert hashlib.sha256(DEFAULT_ARCHIVE.read_bytes()).hexdigest() == clean['archive_sha256']
    allowed = {(x['original_split'],x['meeting_key']) for x in clean['meetings'] if x['included']}
    excluded = set(json.loads(Path('evaluation/action_item_development_exclusions.json').read_text())['meeting_ids'])
    eligible = [(s,r) for s,r in records() if s.startswith('Test1') and (s,r['meeting_key']) in allowed and r['meeting_key'] not in excluded]
    lengths = sorted(len(r['sentences']) for _,r in eligible)
    median = lengths[len(lengths)//2]
    groups = defaultdict(list)
    for s,r in eligible:
        n = len(r['action_ids'])
        group = ('empty' if n==0 else 'sparse' if n<=2 else 'multiple') + ('_short' if len(r['sentences'])<=median else '_long')
        groups[group].append((s,r))
    rng = random.Random(SEED)
    chosen=[]
    for group in sorted(groups):
        pool=sorted(groups[group],key=lambda x:x[1]['meeting_key']); rng.shuffle(pool)
        chosen.extend((s,r,group) for s,r in pool[:5])
    assert len(chosen)==30
    rng.shuffle(chosen)
    order={r['meeting_key']:i for i,(_,r,_) in enumerate(chosen)}
    group_map={r['meeting_key']:g for _,r,g in chosen}
    rows=[]
    for s,r in sorted(eligible,key=lambda x:x[1]['meeting_key']):
        text='\n'.join(z['s'] for z in r['sentences'])
        rows.append(dict(meeting_id=r['meeting_key'],split=s,sentence_count=len(r['sentences']),gold_action_count=len(r['action_ids']),empty_label=not r['action_ids'],included=r['meeting_key'] in order,order=order.get(r['meeting_key']),stratum=group_map.get(r['meeting_key']),seed=SEED,character_count=len(text),windows=len(text_windows(text)),transcript_sha256=hashlib.sha256(text.encode()).hexdigest()))
    serialized=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
    if MANIFEST.exists(): assert MANIFEST.read_text()==serialized, 'Frozen manifest changed'
    else: MANIFEST.write_text(serialized)
    return rows

class Observer(httpx.HTTPTransport):
    def __init__(self,ledger,label,limit):
        super().__init__(proxy=getproxies().get('https'),retries=0)
        self.ledger,self.label,self.limit=ledger,label,limit
    def handle_request(self,request):
        if len(self.ledger)>=self.limit: raise LLMError('evaluation_budget_exhausted')
        row={'meeting_id':self.label,'http_status':None,'request_sha256':hashlib.sha256(request.content).hexdigest()}; self.ledger.append(row)
        dump(ROOT/'action_item_requests.json',self.ledger)
        start=time.monotonic()
        try:
            response=super().handle_request(request); response.read(); row['http_status']=response.status_code
            try: body=response.json()
            except ValueError: body={}
            if isinstance(body,dict):
                usage=body.get('usage') or {}
                row['usage']={k:v for k,v in usage.items() if k in {'prompt_tokens','completion_tokens','total_tokens'} and type(v) is int and v>=0} if isinstance(usage,dict) else {}
                row['model']=body.get('model')
                if response.status_code==200:
                    dump(ROOT/'private_responses'/f'{len(self.ledger):04d}.json', {'meeting_id':self.label,'choices':body.get('choices')})
            return response
        except httpx.TransportError as exc:
            row['error_type']=type(exc).__name__; raise
        finally:
            row['latency_ms']=round((time.monotonic()-start)*1000)
            dump(ROOT/'action_item_requests.json',self.ledger)

def main():
    global ROOT
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['select','smoke','final','score'],required=True);args=p.parse_args()
    manifest=select(); selected=sorted((r for r in manifest if r['included']),key=lambda r:r['order'])
    print(json.dumps({'selected':len(selected),'windows':sum(r['windows'] for r in selected),'seed':SEED}),flush=True)
    if args.stage=='select':return
    if args.stage=='smoke':
        ROOT=ROOT/'action_item_development_v3'
        pool=sorted((r for split,r in records() if split=='Train' and r['meeting_key']!='M3298'),key=lambda r:r['meeting_key'])
        selected=[{'meeting_id':r['meeting_key'],'windows':len(text_windows('\n'.join(z['s'] for z in r['sentences'])))} for r in random.Random(SEED).sample(pool,5)]
        dump(ROOT/'manifest.json',selected)
    path=ROOT/'action_item_predictions.jsonl'; path.parent.mkdir(parents=True,exist_ok=True)
    results=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    ledgerpath=ROOT/'action_item_requests.json';ledger=json.loads(ledgerpath.read_text()) if ledgerpath.exists() else []
    settings=Settings()
    if args.stage!='score' and not (settings.llm_api_key.get_secret_value() and settings.llm_base_url and settings.llm_model):
        raise SystemExit('Provider configuration missing; no evaluation started')
    lookup={r['meeting_key']:r for s,r in records()}
    if args.stage=='final':
        smoke=[json.loads(s) for s in (ROOT/'action_item_development_v3/action_item_predictions.jsonl').read_text().splitlines()]
        assert len(smoke)==5 and all(r['error'] is None for r in smoke), 'Train smoke must pass before final holdout'
    target=selected[:5] if args.stage=='smoke' else selected
    if args.stage!='score':
        for entry in target:
            key=entry['meeting_id']
            if any(r['meeting_id']==key for r in results):continue
            record=lookup[key]; gold={x['id'] for x in record['action_ids']};pred=set();items=[];error=None
            start=time.monotonic();before=len(ledger)
            try:
                output=extract('\n'.join(s['s'] for s in record['sentences']),LLMClient(settings,transport=Observer(ledger,key,150)))
                items=[i.model_dump() for i in output.action_items]
                for item in items:pred|=evidence_ids(record['sentences'],item['evidence'])
            except LLMError as exc:error=exc.kind
            row=dict(meeting_id=key,gold_ids=sorted(gold),predicted_ids=sorted(pred),items=items,error=error,metrics=score(gold,pred),requests=len(ledger)-before,latency_ms=round((time.monotonic()-start)*1000))
            with path.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
            results.append(row);print(json.dumps({k:v for k,v in row.items() if k in {'meeting_id','error','metrics','requests'}}),flush=True)
            if error in {'provider_unauthorized','provider_request_rejected','evaluation_budget_exhausted'}:break
    gold={(r['meeting_id'],i) for r in results for i in r['gold_ids']};pred={(r['meeting_id'],i) for r in results for i in r['predicted_ids']}
    failed=sum(r.get('http_status')!=200 for r in ledger)
    report=dict(meetings=len(results),selected=len(selected),model=settings.llm_model,micro=score(gold,pred),failed_meetings=sum(r['error'] is not None for r in results),request_count=len(ledger),failed_requests=failed,retry_count=len(ledger)-len({(r['meeting_id'],r['request_sha256']) for r in ledger}),input_tokens=sum(r.get('usage',{}).get('prompt_tokens',0) for r in ledger),output_tokens=sum(r.get('usage',{}).get('completion_tokens',0) for r in ledger),total_tokens=sum(r.get('usage',{}).get('total_tokens',0) for r in ledger),latency_ms=sum(r['latency_ms'] for r in ledger),estimated_cost=None,manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),archive_sha256=hashlib.sha256(DEFAULT_ARCHIVE.read_bytes()).hexdigest(),alignment='Exact evidence substring; all overlapping sentence IDs at every matching location; set deduplication per meeting. Failed meeting counted empty.',field_accuracy=None)
    dump(ROOT/'action_item_metrics.json',report)
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
