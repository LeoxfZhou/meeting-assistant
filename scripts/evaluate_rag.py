"""Reproducible, isolated synthetic RAG retrieval evaluation; optional real LLM answers."""
import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.security import hasher
from app.db.session import build_engine
from app.models.user import User
from app.models.meeting import Meeting
from app.rag.embedding import get_embedder, MODEL_ID
from app.rag.service import ingest_company,index_meeting,retrieve,company_id
from app.rag.answer import answer_question
from app.llm.client import LLMClient,LLMError
from evaluation.database import isolated_database


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--with-llm',action='store_true')
    parser.add_argument('--k',type=int,default=5)
    parser.add_argument('--output',type=Path,default=Path('outputs/evaluations/rag'))
    args=parser.parse_args()
    if not 1<=args.k<=10: parser.error('k must be 1..10')
    settings=Settings()
    if args.with_llm and not (settings.llm_api_key.get_secret_value() and settings.llm_base_url and settings.llm_model):
        parser.error('Configure real LLM settings before answer evaluation')
    questions=[json.loads(s) for s in Path('evaluation/rag_questions.jsonl').read_text().splitlines() if s.strip()]
    fixtures=json.loads(Path('evaluation/synthetic_meetings.json').read_text())['meetings']
    embedder=get_embedder();rows=[]
    with isolated_database() as url:
        engine=build_engine(url)
        try:
            with Session(engine,expire_on_commit=False) as session:
                user=User(email=f'eval-{uuid4().hex}@example.com',display_name='Synthetic evaluator',
                          password_hash=hasher.hash(uuid4().hex),is_owner=True)
                session.add(user);session.commit()
                chunks=ingest_company(session,embedder)
                names={str(company_id(p.stem)):p.stem for p in Path('data/company_docs').glob('*.md')}
                for fixture in fixtures:
                    meeting=Meeting(title=fixture['title'],content=fixture['content'],creator_user_id=user.id,source_type='pasted_text')
                    session.add(meeting);session.commit()
                    index_meeting(session,meeting.id,user,embedder)
                    names[str(meeting.id)]='meeting:'+fixture['slug']
                for q in questions:
                    sources=retrieve(session,q['question'],user,embedder,args.k)
                    ranked=[names[s['source_id']] for s in sources]
                    gold=set(q['expected_sources']);hits=gold & set(ranked)
                    row={**q,'retrieved_sources':ranked,'scores':[s['score'] for s in sources],
                        'hit':bool(hits) if gold else None,'recall':len(hits)/len(gold) if gold else None,
                        'mrr':next((1/(i+1) for i,s in enumerate(ranked) if s in gold),0) if gold else None,
                        'answer_evaluation':'not_run_no_provider_call'}
                    if args.with_llm:
                        try:
                            answer=answer_question(q['question'],sources,LLMClient(settings))
                            cited={names[s['source_id']] for s in answer['sources']}
                            row.update(answer_evaluation='completed',answer=answer,
                                source_precision=len(cited & gold)/len(cited) if cited else (1.0 if not gold else 0.0),
                                no_answer_correct=answer['no_answer']==(not gold))
                        except LLMError as exc:
                            row.update(answer_evaluation='failed',error_type=exc.kind,source_precision=0.0,no_answer_correct=False)
                    rows.append(row)
        finally: engine.dispose()
    answerable=[r for r in rows if r['expected_sources']]
    report={'model':MODEL_ID,'questions':len(rows),'answerable':len(answerable),'company_documents':12,
            'synthetic_meetings':len(fixtures),'company_chunks':chunks,'k':args.k,
            'hit_at_k':sum(r['hit'] for r in answerable)/len(answerable),
            'recall_at_k':sum(r['recall'] for r in answerable)/len(answerable),
            'mrr':sum(r['mrr'] for r in answerable)/len(answerable),
            'citation_source_accuracy':sum(r['source_precision'] for r in rows)/len(rows) if args.with_llm else None,
            'no_answer_accuracy':sum(r['no_answer_correct'] for r in rows if not r['expected_sources'])/sum(not r['expected_sources'] for r in rows) if args.with_llm else None,
            'answer_evaluation':'real_provider' if args.with_llm else 'not_run_retrieval_only',
            'questions_sha256':hashlib.sha256(Path('evaluation/rag_questions.jsonl').read_bytes()).hexdigest(),
            'limitations':['Small self-authored synthetic benchmark; not independent production validation.',
                          'No-answer retrieval alone is not answer refusal accuracy.','Exact citation checks do not prove semantic entailment.']}
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    (args.output/'predictions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    bad=[r for r in rows if (r['expected_sources'] and (r['recall']<1 or r['mrr']<1)) or r.get('no_answer_correct') is False]
    (args.output/'bad_cases.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in bad))
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
