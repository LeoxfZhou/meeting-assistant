from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import event, select, func
from sqlalchemy.exc import OperationalError
from app.api.actions import get_llm
from app.core.config import Settings
from app.main import create_app
from app.models.action_item import ActionItem, Task
from tests.helpers import authenticate
from tests.test_llm import llm, response

TEXT='小张周五完成测试。'
MOCK='{"action_items":[{"task":"完成测试","assignee_name":"小张","deadline":"周五","evidence":"小张周五完成测试。"}]}'


def candidate(client):
    client.app.dependency_overrides[get_llm]=lambda: llm(lambda _:response(MOCK))
    mid=client.post('/meetings',json={'title':'合成会议','content':TEXT}).json()['id']
    r=client.post(f'/meetings/{mid}/extract')
    assert r.status_code==201,r.text
    return mid,r.json()[0]


def test_review_confirm_idempotent(client):
    mid,item=candidate(client)
    assert client.get('/tasks').json()==[]
    assert item['status']=='pending' and item['assignee_user_id'] is None
    assert client.post(f'/meetings/{mid}/extract').status_code==409
    edited=client.patch('/candidates/'+item['id'],json={'revision':1,'task':'完成接口测试'}).json()
    assert edited['revision']==2
    assert client.post(f"/candidates/{item['id']}/confirm",json={'revision':1}).status_code==409
    first=client.post(f"/candidates/{item['id']}/confirm",json={'revision':2})
    assert first.status_code==200
    again=client.post(f"/candidates/{item['id']}/confirm",json={'revision':2})
    assert again.json()['id']==first.json()['id']
    assert len(client.get('/tasks').json())==1
    assert client.patch('/meetings/'+mid,json={'content':'changed'}).status_code==409
    assert client.delete('/meetings/'+mid).status_code==409
    assert client.post(f"/candidates/{item['id']}/reject",json={'revision':3}).status_code==409


def test_reject_and_permissions(client):
    mid,item=candidate(client)
    assert client.post(f"/candidates/{item['id']}/reject",json={'revision':1}).status_code==200
    assert client.post(f"/candidates/{item['id']}/confirm",json={'revision':2}).status_code==409
    assert client.get('/tasks').json()==[]
    authenticate(client)
    assert client.get(f'/meetings/{mid}/candidates').status_code==404
    assert client.post(f'/meetings/{mid}/extract').status_code==404
    assert client.patch('/candidates/'+item['id'],json={'revision':2,'task':'hack'}).status_code==404


def test_assignee_my_tasks(client):
    creator_auth=client.headers['Authorization']
    other=authenticate(client)
    assignee_auth=client.headers['Authorization']
    client.headers['Authorization']=creator_auth
    mid,item=candidate(client)
    edited=client.patch('/candidates/'+item['id'],json={'revision':1,'assignee_user_id':other['id']})
    assert edited.status_code==200
    task=client.post(f"/candidates/{item['id']}/confirm",json={'revision':2}).json()
    client.headers['Authorization']=assignee_auth
    assert client.get('/tasks/my').json()[0]['id']==task['id']
    assert client.get('/tasks/'+task['id']).status_code==200
    assert client.patch('/tasks/'+task['id'],json={'status':'done'}).status_code==200
    assert client.patch('/tasks/'+task['id'],json={'title':'unauthorized change'}).status_code==403
    assert client.get('/meetings/'+mid).status_code==404
    authenticate(client)
    assert client.get('/tasks/'+task['id']).status_code==404


def test_provider_missing(client):
    mid=client.post('/meetings',json={'title':'x','content':'y'}).json()['id']
    assert client.post(f'/meetings/{mid}/extract').status_code==503
    assert client.get(f'/meetings/{mid}/candidates').json()==[]


def test_concurrent_confirm_and_transaction_rollback(database_url):
    app=create_app(Settings(_env_file=None,database_url=database_url,jwt_secret='test-only-'*8,app_env='test'))
    with TestClient(app) as c:
        authenticate(c)
        mid,item=candidate(c)
        def fail(mapper,connection,target):
            raise OperationalError('private SQL',{},RuntimeError('injected write failure'))
        event.listen(Task,'before_insert',fail)
        try:
            assert c.post(f"/candidates/{item['id']}/confirm",json={'revision':1}).status_code==503
        finally:
            event.remove(Task,'before_insert',fail)
        assert c.get(f'/meetings/{mid}/candidates').json()[0]['status']=='pending'
        assert c.get('/tasks').json()==[]
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _: c.post(f"/candidates/{item['id']}/confirm",json={'revision':1}),range(2)))
        assert [r.status_code for r in responses]==[200,200]
        assert responses[0].json()['id']==responses[1].json()['id']
        with app.state.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Task).where(Task.source_action_item_id==UUID(item['id'])))==1
