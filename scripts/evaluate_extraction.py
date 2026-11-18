"""Real AliMeeting scoring. empty-baseline is explicitly NOT an LLM result."""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from evaluation.extraction import score, evidence_ids
from scripts.audit_alimeeting4mug import DEFAULT_ARCHIVE, SPLIT_NAMES


def records():
    csv.field_size_limit(100_000_000)
    with zipfile.ZipFile(DEFAULT_ARCHIVE) as outer:
        for member,split in SPLIT_NAMES.items():
            with zipfile.ZipFile(io.BytesIO(outer.read(member))) as inner:
                name=next(n for n in inner.namelist() if not n.endswith('/'))
                with inner.open(name) as binary:
                    for row in csv.DictReader(io.TextIOWrapper(binary,encoding='utf-8-sig'),delimiter='\t'):
                        yield split,json.loads(row['content'])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['provider','empty-baseline'],required=True)
    parser.add_argument('--split',choices=['Train','Dev','Test1'],default='Dev')
    parser.add_argument('--limit',type=int,default=0,help='0 means all eligible meetings')
    parser.add_argument('--output',type=Path,default=Path('outputs/evaluations/extraction'))
    args=parser.parse_args()
    manifest_path=Path('data/processed/clean_split.json')
    manifest=json.loads(manifest_path.read_text())
    if hashlib.sha256(DEFAULT_ARCHIVE.read_bytes()).hexdigest()!=manifest['archive_sha256']:
        parser.error('Archive changed; regenerate clean split and review it')
    allowed={(x['original_split'],x['meeting_key']) for x in manifest['meetings'] if x['included']}
    if args.mode=='provider':
        from app.core.config import Settings
        from app.llm.client import LLMClient, LLMError
        from app.llm.extraction import extract
        settings=Settings()
        if not (settings.llm_api_key.get_secret_value() and settings.llm_base_url and settings.llm_model):
            parser.error('Configure LLM_API_KEY/BASE_URL/MODEL; no fake provider results will be generated')
        client=LLMClient(settings)
    all_gold=set();all_pred=set();results=[];failures=[]
    for split,record in records():
        key=record['meeting_key']
        if not split.startswith(args.split) or (split,key) not in allowed: continue
        if args.limit and len(results)>=args.limit: break
        gold={int(x['id']) for x in record['action_ids']};pred=set();error=None;items=[]
        if args.mode=='provider':
            try:
                text='\n'.join(s['s'] for s in record['sentences'])
                output=extract(text,client)
                items=[x.model_dump() for x in output.action_items]
                for item in output.action_items: pred|=evidence_ids(record['sentences'],item.evidence)
            except LLMError as exc:
                error=exc.kind
        all_gold|={(key,sid) for sid in gold};all_pred|={(key,sid) for sid in pred}
        row={'meeting_id':key,'split':split,'gold_ids':sorted(gold),'predicted_ids':sorted(pred),
             'error':error,'metrics':score(gold,pred),'items':items}
        results.append(row)
        if gold!=pred or error: failures.append(row)
    if not results: parser.error('No eligible meetings')
    args.output.mkdir(parents=True,exist_ok=True)
    report={'mode':args.mode,'model':settings.llm_model if args.mode=='provider' else None,
        'split':args.split,'meetings':len(results),'micro':score(all_gold,all_pred),
        'failures':sum(r['error'] is not None for r in results),
        'empty_gold_meetings':sum(not r['gold_ids'] for r in results),
        'clean_split_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'field_metrics':'Unavailable: no verified assignee/deadline/task field gold.',
        'scoring_policy':'Deduplicate sentence IDs per meeting; failed calls count as empty predictions; zero denominators score 0.',
        'caveat':'Scoring harness baseline only; not cloud extraction quality.' if args.mode=='empty-baseline' else 'Evidence spans map to all overlapping sentence IDs; inspect ambiguous spans manually.'}
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    for name,rows in [('predictions.jsonl',results),('bad_cases.jsonl',failures)]:
        (args.output/name).write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
