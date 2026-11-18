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
