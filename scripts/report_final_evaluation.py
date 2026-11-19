"""Recompute metrics and publish only corpus-free evidence; never invokes the provider."""
import hashlib
import json
import shutil
from pathlib import Path
from evaluation.extraction import score, evidence_ids
from scripts.evaluate_extraction import records

ROOT=Path('outputs/evaluations')
PUBLIC=Path('evaluation/evidence')

def main():
    rows=[json.loads(s) for s in (ROOT/'action_item_predictions.jsonl').read_text().splitlines()]
    assert len(rows)==30 and len({r['meeting_id'] for r in rows})==30
    report=json.loads((ROOT/'action_item_metrics.json').read_text())
    gold={(r['meeting_id'],sid) for r in rows for sid in r['gold_ids']}
    predicted={(r['meeting_id'],sid) for r in rows for sid in r['predicted_ids']}
    assert report['micro']==score(gold,predicted)
    selected=[json.loads(s) for s in Path('evaluation/action_item_eval_manifest.jsonl').read_text().splitlines()]
    assert {r['meeting_id'] for r in rows}=={r['meeting_id'] for r in selected if r['included']}
    report.update(source_sha256=hashlib.sha256(Path('app/llm/extraction.py').read_bytes()).hexdigest(),
                  population='30 stratified Test1 meetings, 5 per density/length stratum; not population-weighted',
                  development_exclusions=json.loads(Path('evaluation/action_item_development_exclusions.json').read_text())['meeting_ids'])
    (ROOT/'action_item_metrics.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    shutil.copyfile(ROOT/'action_item_metrics.json',PUBLIC/'action_item_metrics.json')
    shutil.copyfile('evaluation/action_item_eval_manifest.jsonl',ROOT/'action_item_eval_manifest.jsonl')
    safe=[{k:r[k] for k in ['meeting_id','gold_ids','predicted_ids','error','metrics','requests','latency_ms']} for r in rows]
    (PUBLIC/'action_item_sentence_results.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in safe))
    lookup={r['meeting_key']:r for _,r in records()}
    cases=[]
    # Deterministic selection by observed error counts, not cherry-picked successes.
    for typ in ['false_positive','false_negative']:
        ranked=sorted(rows,key=lambda r:(-r['metrics']['fp' if typ=='false_positive' else 'fn'],r['meeting_id']))
        for r in ranked[:5]:
            ids=sorted(set(r['predicted_ids'])-set(r['gold_ids']) if typ=='false_positive' else set(r['gold_ids'])-set(r['predicted_ids']))
            if not ids:continue
            sid=ids[0]; sentences={s['id']:s['s'] for s in lookup[r['meeting_id']]['sentences']}
            items=[i for i in r['items'] if sid in evidence_ids(lookup[r['meeting_id']]['sentences'],i['evidence'])]
            cases.append(dict(meeting_id=r['meeting_id'],sentence_id=sid,error_type=typ,gold_ids=r['gold_ids'],predicted_ids=r['predicted_ids'],evidence=sentences[sid],prediction=items,error=r['error'],likely_cause='Model selects a broader action/evidence span than the sentence-level annotation; needs manual label review.' if typ=='false_positive' else 'Gold sentence was not covered by accepted evidence; implicit/context-fragmented action or failed meeting are hypotheses, not established causes.',possible_improvement='Review annotation policy and sentence-level evidence boundaries on development data only; do not tune on this holdout.'))
    hypotheses = {
        ('M4285','false_positive'): 'Fragmented conversational lead-in selected with neighbouring lines; possible evidence-boundary/annotation mismatch, not proven hallucination.',
        ('M4056','false_positive'): 'Modal suggestion may be interpreted as a firm assignment; annotation-policy review needed.',
        ('M3291','false_positive'): 'General recommendation may be treated as a concrete action; background-versus-commitment ambiguity.',
        ('M0145','false_positive'): 'Past/completed-work language mixed with later steps; possible tense/status confusion.',
        ('M3310','false_positive'): 'An apparent explicit request lacks this sentence-level Gold label; inspect annotation scope before alleging a false semantic action.',
        ('M3149','false_negative'): 'Gold marks a scheduling concern rather than a standalone imperative; context and annotation-boundary ambiguity.',
        ('M4285','false_negative'): 'Gold is a short duration fragment; action meaning depends on surrounding context.',
        ('M3310','false_negative'): 'Implicit scheduling commitment without a clear owner may be missed.',
        ('M4056','false_negative'): 'Fragmented relative-time plan may be missed without neighbouring context.'
    }
    for c in cases:
        c['analysis_author']='AI-assisted qualitative inspection, not human-adjudicated Gold'
        c['likely_cause']=hypotheses.get((c['meeting_id'],c['error_type']),c['likely_cause'])
        if c['error']:
            c['likely_cause']='Observed provider failure: '+c['error']+'; production rejects the whole meeting rather than saving partial candidates.'
    private=['# Real Action Item Bad Cases (local restricted evidence)','Do not publish original transcript quotes. Root causes are hypotheses, not human adjudication.']
    for c in cases:private+=['\n## '+c['meeting_id']+' / '+c['error_type'], '```json',json.dumps(c,ensure_ascii=False,indent=2),'```']
    (ROOT/'action_item_bad_cases.md').write_text('\n'.join(private)+'\n')
    public=['# Real bad cases — corpus-free index','Full Gold/Prediction/Evidence lives in ignored outputs/evaluations/action_item_bad_cases.md.','| Meeting | Sentence | Type | Gold IDs | Predicted IDs |','|---|---:|---|---|---|']
    for c in cases:public.append(f"|{c['meeting_id']}|{c['sentence_id']}|{c['error_type']}|{c['gold_ids']}|{c['predicted_ids']}|")
    public += ['', '## Qualitative hypotheses (not revised Gold)'] + [c['meeting_id']+' / '+c['error_type']+': '+c['likely_cause'] for c in cases]
    public+=['','Likely causes: evidence span/annotation mismatch for FP; missed implicit/context-dependent commitments or rejected extraction for FN. These are hypotheses requiring human review. No owner/deadline accuracy is claimed. Improve only on development data; keep this holdout frozen.']
    (PUBLIC/'action_item_bad_cases.md').write_text('\n'.join(public)+'\n')
    m=report['micro']
    text=f'''# Action Item Evaluation — frozen small holdout

30 Test1 meetings; seed 20261119; 6 strata (empty / 1–2 / >2 action IDs × shorter / longer than eligible median sentence count), 5 per stratum. This deliberately balanced diagnostic sample is not a representative population estimate. Candidate pool is 77 Test1 meetings after excluding five previously inspected smoke meetings. Those five are development-only: {report['development_exclusions']}.

Known leakage: Train M3298 is excluded; Dev M8016 retained (40 shared long sentences, SequenceMatcher 0.877). Raw archive unchanged; clean split Train294/Dev65/Test1 82. Other semantic near-duplicates have not been exhaustively excluded. No AliMeeting data entered RAG. Five clean Train meetings were used for smoke; final Test1 prompts/code were frozen before inference and not tuned on final scores.

## Measured result

TP={m['tp']}, FP={m['fp']}, FN={m['fn']}.
Micro Precision={m['precision']:.8f}, Recall={m['recall']:.8f}, F1={m['f1']:.8f}.
Failed meetings={report['failed_meetings']}; HTTP attempts={report['request_count']}; failed transport/non-200 attempts={report['failed_requests']}; retries={report['retry_count']}.
Input/output/total reported tokens={report['input_tokens']}/{report['output_tokens']}/{report['total_tokens']}; sum HTTP latency={report['latency_ms']}ms; estimated_cost=null. Failed requests without usage may still have unknown provider-side cost. Model: {report['model']}.

## Metric and alignment

Identity is (meeting_id, sentence_id). TP=predicted∩gold; FP=predicted−gold; FN=gold−predicted. P=TP/(TP+FP), R=TP/(TP+FN), F1=2PR/(P+R); zero denominator gives zero. Explicit empty-label meetings remain in evaluation; extra predictions count FP. A failed meeting counts empty predictions, never removed from the denominator.

Production app.llm.extraction.extract uses 6000-character windows / 300 overlap. Prompt numbers lines; validated inclusive start/end reconstruct exact original evidence, not model-written quotes. Legacy quotes can only restore whitespace when uniquely matched, never fuzzy words; one bounded evidence correction allowed. All surviving evidence is matched exactly against newline-joined original sentences; every overlapping sentence at every exact occurrence is included, then IDs deduplicated per meeting. Broad evidence can increase FP; this is a known conservative alignment limitation, not manually adjudicated accuracy.

No reliable task/assignee/deadline Gold exists: no field accuracy is reported. Qualitative review remains separate. The observed scores describe this model, prompt, subset and alignment only; they do not establish general meeting understanding or business impact.

## Reproduction

Acquire the same dataset lawfully; archive SHA256={report['archive_sha256']}.
Run scripts.clean_split; inspect evaluation/action_item_eval_manifest.jsonl (SHA256={report['manifest_sha256']}). scripts.finalize_evaluation --stage select validates selection; --stage smoke runs Train, --stage final requires successful smoke and resumes missing meetings only. Existing results are not overwritten. To reproduce new stochastic inference, use a fresh output copy, preserve prior evidence, and expect nonidentical predictions.
Run `python -m scripts.report_final_evaluation` to recompute saved ID metrics without API calls. Provider requests/quotes remain local under outputs/evaluations; public evidence contains only counts, IDs and hashes. Source extraction SHA256={report['source_sha256']}.

## Development failures retained

Original 5 Test1 smoke meetings all failed evidence validation and were removed from final eligibility; whitespace/repair-only Train experiment still had failures. Final line-ID design passed 5 Train smoke meetings. These runs are not part of final30 and their token usage is reported separately in run_accounting.json. No test-set result was silently rerun to inflate F1.
'''
    (ROOT/'action_item_evaluation.md').write_text(text)
    (PUBLIC/'action_item_evaluation.md').write_text(text)
    phases={}
    for name,folder in [('development_v1',ROOT/'action_item_development_v1'),('development_v2',ROOT/'action_item_development_v2'),('train_smoke_v3',ROOT/'action_item_development_v3'),('final30',ROOT)]:
        r=json.loads((folder/'action_item_metrics.json').read_text())
        phases[name]={k:r[k] for k in ['meetings','request_count','failed_requests','retry_count','input_tokens','output_tokens','total_tokens','estimated_cost']}
    (PUBLIC/'run_accounting.json').write_text(json.dumps(phases,indent=2))
    print(json.dumps({'verified_meetings':len(rows),'bad_cases':len(cases),'micro':m}))

if __name__=='__main__':main()
