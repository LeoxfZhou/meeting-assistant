import hashlib
import json
from pathlib import Path
from evaluation.extraction import score,evidence_ids
from scripts.audit_alimeeting4mug import DEFAULT_ARCHIVE


def test_scoring_units():
    assert score({1,2},{2,3})=={'tp':1,'fp':1,'fn':1,'precision':0.5,'recall':0.5,'f1':0.5}
    assert score(set(),set())['f1']==0
    assert evidence_ids([{'id':1,'s':'原文第一句。'},{'id':2,'s':'安排工作。'}],'原文第一句。\n安排工作。')=={1,2}


def test_rag_gold_integrity():
    questions=[json.loads(x) for x in Path('evaluation/rag_questions.jsonl').read_text().splitlines()]
    slugs={p.stem for p in Path('data/company_docs').glob('*.md')}
    meetings=json.loads(Path('evaluation/synthetic_meetings.json').read_text())['meetings']
    available=slugs | {'meeting:'+m['slug'] for m in meetings}
    assert 20<=len(questions)<=30 and len({q['id'] for q in questions})==len(questions)
    for q in questions:
        assert set(q['expected_sources'])<=available and q['expected_answer_points']
        assert bool(q['expected_sources'])==(q['type']!='no_answer')


def test_final_holdout_has_no_development_meetings():
    rows=[json.loads(x) for x in Path('evaluation/action_item_eval_manifest.jsonl').read_text().splitlines()]
    selected=[r for r in rows if r['included']]
    excluded=set(json.loads(Path('evaluation/action_item_development_exclusions.json').read_text())['meeting_ids'])
    assert len(selected)==30 and len({r['meeting_id'] for r in selected})==30
    assert not excluded & {r['meeting_id'] for r in selected}
    assert sorted(r['order'] for r in selected)==list(range(30))
    assert len({r['stratum'] for r in selected})==6
    assert all(r['split'].startswith('Test1') and r['seed']==20261119 for r in selected)


def test_alignment_repeated_spans_and_empty_predictions():
    sentences=[{'id':1,'s':'提交报告。'},{'id':2,'s':'背景说明。'},{'id':3,'s':'提交报告。'}]
    assert evidence_ids(sentences,'提交报告。')=={1,3}
    assert evidence_ids(sentences,'不存在的引用')==set()
    assert score({1,3},set())['fn']==2
