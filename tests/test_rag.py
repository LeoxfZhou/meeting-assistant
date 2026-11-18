import json
from uuid import UUID
import numpy as np
import pytest
from sqlalchemy import select, func
from app.api.actions import get_llm
from app.db.session import get_session
from app.llm.client import LLMError
from app.models.user import User
from app.models.knowledge import KnowledgeChunk, CompanyDocument
from app.rag.embedding import get_embedder, DIMENSION
from app.rag.chunking import chunks
from app.rag.answer import answer_question
from tests.helpers import authenticate
from tests.test_llm import llm, response


def make_owner(client):
    user=client.get('/auth/me').json()
    session=next(client.app.dependency_overrides[get_session]())
    session.get(User,UUID(user['id'])).is_owner=True
    session.commit()


def test_real_cpu_embedding():
    e=get_embedder()
    v=e.encode(['P1 事件须在五分钟内响应。'])
    q=e.encode(['P1 多久响应？'],query=True)
    assert len(v[0])==DIMENSION and len(q[0])==DIMENSION
    assert np.isclose(np.linalg.norm(v[0]),1,atol=1e-5)
    assert float(np.dot(v[0],q[0]))>0.5


def test_chunking_preserves_coverage():
    text=('小张：确认本周发布。\n小李：需要测试。\n'*80)
    parts=chunks(text,'meeting')
    assert parts[0]['char_start']==0 and parts[-1]['char_end']==len(text)
    for a,b in zip(parts,parts[1:]): assert b['char_start']<=a['char_end']
    assert all(p['content']==text[p['char_start']:p['char_end']] for p in parts)


def test_company_ingestion_and_search(client):
    assert client.post('/knowledge/company/ingest').status_code==403
    make_owner(client)
    first=client.post('/knowledge/company/ingest')
    assert first.status_code==200 and first.json()['chunks']>=12
    second=client.post('/knowledge/company/ingest')
    assert second.json()==first.json()
    session=next(client.app.dependency_overrides[get_session]())
    assert session.scalar(select(func.count()).select_from(CompanyDocument))==12
    sources=client.post('/knowledge/search',json={'question':'P1 事件几分钟内响应？'}).json()['sources']
    assert any('P1/P2' in s['source_title'] for s in sources)
    assert all(s['source_type']=='company_document' for s in sources)
    assert client.get('/knowledge/chunks/'+sources[0]['chunk_id']).status_code==200


def test_historical_permissions_invalidation(client):
    mid=client.post('/meetings',json={'title':'Alpha 延期评审','content':'2026年11月12日决定 Alpha 试点延期至12月20日，林悦负责复核权限。'}).json()['id']
    assert client.post(f'/meetings/{mid}/index').status_code==200
    sources=client.post('/knowledge/search',json={'question':'Alpha 什么时候决定延期？'}).json()['sources']
    assert sources[0]['source_id']==mid
    cid=sources[0]['chunk_id']
    original_auth=client.headers['Authorization']
    authenticate(client)
    assert client.post('/knowledge/search',json={'question':'Alpha 延期？'}).json()['sources']==[]
    assert client.get('/knowledge/chunks/'+cid).status_code==404
    assert client.post(f'/meetings/{mid}/index').status_code==404
    client.headers['Authorization']=original_auth
    assert client.patch('/meetings/'+mid,json={'content':'新的会议正文'}).status_code==200
    assert client.get('/knowledge/chunks/'+cid).status_code==404
    assert client.post('/knowledge/search',json={'question':'Alpha 延期？'}).json()['sources']==[]


def test_answer_citation_and_no_answer():
    sources=[{'chunk_id':'one','source_type':'meeting','source_id':'source','source_title':'demo','content':'周五完成测试。'}]
    good=llm(lambda _:response(json.dumps({'answer':'周五完成测试。','no_answer':False,'citations':[{'chunk_id':'one','quote':'周五完成测试。'}]})))
    assert answer_question('何时完成？',sources,good)['sources'][0]['source_id']=='source'
    refusal=llm(lambda _:response(json.dumps({'answer':'依据不足。','no_answer':True,'citations':[]})))
    assert answer_question('工资多少？',sources,refusal)['no_answer']
    assert answer_question('工资多少？',[],good)['no_answer']
    for citations in [[{'chunk_id':'other','quote':'周五完成测试。'}],[{'chunk_id':'one','quote':'周六'}],[]]:
        bad=llm(lambda _:response(json.dumps({'answer':'编造','no_answer':False,'citations':citations})))
        with pytest.raises(LLMError): answer_question('何时？',sources,bad)
