"""Verify live local Compose using temporary synthetic fixtures, never a fake LLM success."""
import json
import secrets
import subprocess
import time
from pathlib import Path
from uuid import UUID, uuid4
import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.db.session import build_engine
from app.models.user import User
from app.models.meeting import Meeting
from app.models.action_item import ActionItem, Task
from app.models.knowledge import KnowledgeChunk


def main():
    email='compose-smoke-'+uuid4().hex+'@example.com'
    password=secrets.token_urlsafe(24)
    settings=Settings()
    from sqlalchemy.engine import make_url
    if settings.app_env not in {'development','test'} or make_url(settings.database_url.get_secret_value()).host not in {'127.0.0.1','localhost'}:
        raise ValueError('Smoke test requires a local development database')
    engine=build_engine(settings.database_url.get_secret_value())
    uid=None;meeting_ids=[];candidate_id=None;task_id=None
    report={'candidate_origin':'synthetic fixture inserted for workflow verification; not an LLM result','checks':{}}
    try:
        with httpx.Client(base_url='http://127.0.0.1:8000',timeout=60) as client:
            assert client.get('/health').status_code==200
            r=client.post('/auth/register',json={'email':email,'display_name':'Synthetic Compose verifier','password':password})
            assert r.status_code==201;uid=UUID(r.json()['id'])
            r=client.post('/auth/login',json={'email':email,'password':password})
            assert r.status_code==200
            client.headers['Authorization']='Bearer '+r.json()['access_token']
            with Session(engine) as session:
                user=session.get(User,uid)
                assert user.email==email
                user.is_owner=True;session.commit()
            assert client.get('/auth/me').json()['is_owner']
            r=client.post('/meetings',json={'title':'Synthetic Compose smoke','content':'小张周五完成接口测试。'})
            assert r.status_code==201;mid=r.json()['id'];meeting_ids.append(UUID(mid))
            assert client.patch('/meetings/'+mid,json={'title':'Synthetic Compose persistence check'}).status_code==200
            for extension,mime in [('txt','text/plain'),('md','text/markdown')]:
                r=client.post('/meetings/upload',files={'file':('synthetic.'+extension,b'Synthetic upload only',mime)})
                assert r.status_code==201;meeting_ids.append(UUID(r.json()['id']))
            report['checks']['auth_crud_txt_md']=True
            assert client.post('/meetings/'+mid+'/index').status_code==200
            assert client.post('/knowledge/company/ingest').status_code==200
            sources=client.post('/knowledge/search',json={'question':'P1几分钟内响应？','k':5}).json()['sources']
            assert any('P1/P2' in x['source_title'] for x in sources)
            assert client.get('/knowledge/chunks/'+sources[0]['chunk_id']).status_code==200
            report['checks']['real_cpu_pgvector_retrieval']=True
            if not settings.llm_api_key.get_secret_value():
                missing=client.post('/meetings/'+mid+'/extract')
                assert missing.status_code==503 and missing.json()['detail']=='provider_not_configured'
                report['checks']['missing_provider_is_explicit_failure']=True
            else:
                report['checks']['provider_call']='not_called_to_avoid_unapproved_cost'
            with Session(engine) as session:
                item=ActionItem(meeting_id=UUID(mid),task='完成接口测试（合成验证）',assignee_name='小张',
                                assignee_user_id=uid,due_date_text='周五',evidence='小张周五完成接口测试。')
                session.add(item);session.commit();candidate_id=item.id
            subprocess.run(['docker','compose','restart','postgres','api'],check=True,capture_output=True)
            for _ in range(60):
                try:
                    if client.get('/meetings/'+mid).status_code==200: break
                except httpx.TransportError:
                    pass  # 有限启动轮询；失败最后明确抛出。
                time.sleep(1)
            else: raise RuntimeError('Compose did not recover within 60 seconds')
            pending=client.get('/meetings/'+mid+'/candidates').json()
            assert pending[0]['status']=='pending'
            report['checks']['database_and_pending_review_survive_restart']=True
            r=client.post(f'/candidates/{candidate_id}/confirm',json={'revision':1})
            assert r.status_code==200;task_id=UUID(r.json()['id'])
            duplicate=client.post(f'/candidates/{candidate_id}/confirm',json={'revision':1})
            assert duplicate.status_code==200 and duplicate.json()['id']==str(task_id)
            assert any(x['id']==str(task_id) for x in client.get('/tasks/my').json())
            assert client.patch('/tasks/'+str(task_id),json={'status':'done'}).status_code==200
            report['checks']['human_review_tasks_idempotency_my_tasks']=True
            report['checks']['api_health']=client.get('/health').status_code==200
    finally:
        with Session(engine) as session:
            if candidate_id: session.execute(delete(Task).where(Task.source_action_item_id==candidate_id))
            if candidate_id: session.execute(delete(ActionItem).where(ActionItem.id==candidate_id))
            for mid in meeting_ids:
                session.execute(delete(Meeting).where(Meeting.id==mid))
            if uid: session.execute(delete(User).where(User.id==uid,User.email==email))
            session.commit()
        engine.dispose()
    report['temporary_user_and_meetings_removed']=True
    report['company_documents_retained']='12 original synthetic documents for local demo'
    out=Path('outputs/checks/compose_smoke.json');out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__': main()
