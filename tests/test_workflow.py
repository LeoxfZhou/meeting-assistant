import pytest
from pydantic import ValidationError
from fastapi import HTTPException
from app.api.actions import get_llm
from app.db.session import get_session
from app.models.user import User
from app.workflow.tools import ToolContext, execute_tool
from tests.test_actions import TEXT, MOCK
from tests.test_llm import llm,response
from uuid import UUID,uuid4


def test_workflow_main_and_failure(client):
    mid=client.post('/meetings',json={'title':'Graph demo','content':TEXT}).json()['id']
    client.app.dependency_overrides[get_llm]=lambda:llm(lambda _:response('invalid JSON'))
    assert client.post(f'/meetings/{mid}/workflow').status_code==502
    assert client.get(f'/meetings/{mid}/candidates').json()==[]
    client.app.dependency_overrides[get_llm]=lambda:llm(lambda _:response(MOCK))
    result=client.post(f'/meetings/{mid}/workflow')
    assert result.status_code==200
    assert result.json()['status']=='awaiting_human_review'
    assert result.json()['knowledge_sources']==[]
    assert client.get('/tasks').json()==[]
    cid=result.json()['candidate_ids'][0]
    assert client.post(f'/candidates/{cid}/confirm',json={'revision':1}).status_code==200
    assert len(client.get('/tasks').json())==1
    assert len(client.get('/workflow/tools').json()['tools'])==4


def test_tools_require_server_confirmation(client):
    session=next(client.app.dependency_overrides[get_session]())
    user=session.get(User,UUID(client.get('/auth/me').json()['id']))
    with pytest.raises(HTTPException) as exc:
        execute_tool('create_task',{'candidate_id':str(uuid4()),'revision':1},ToolContext(session,user))
    assert exc.value.status_code==403
    with pytest.raises(ValidationError):
        execute_tool('create_task',{'candidate_id':str(uuid4()),'revision':1,'human_approved':True},ToolContext(session,user))


def test_optional_knowledge_branch(client):
    mid=client.post('/meetings',json={'title':'Incident','content':'按照 P1 Incident SOP 执行。'}).json()['id']
    client.app.dependency_overrides[get_llm]=lambda:llm(lambda _:response('{"action_items":[]}'))
    result=client.post(f'/meetings/{mid}/workflow')
    assert result.status_code==200
    assert result.json()['status']=='completed_no_actions'
    assert client.get('/tasks').json()==[]


def test_review_survives_app_restart(database_url):
    from app.core.config import Settings
    from app.main import create_app
    from fastapi.testclient import TestClient
    from tests.helpers import authenticate
    settings=Settings(_env_file=None,database_url=database_url,jwt_secret='test-only-'*8,app_env='test')
    with TestClient(create_app(settings)) as first:
        authenticate(first)
        auth=first.headers['Authorization']
        first.app.dependency_overrides[get_llm]=lambda:llm(lambda _:response(MOCK))
        mid=first.post('/meetings',json={'title':'Restart demo','content':TEXT}).json()['id']
        result=first.post(f'/meetings/{mid}/workflow').json()
        cid=result['candidate_ids'][0]
    with TestClient(create_app(settings)) as second:
        second.headers['Authorization']=auth
        assert second.get(f'/meetings/{mid}/candidates').json()[0]['status']=='pending'
        assert second.get('/tasks').json()==[]
        task=second.post(f'/candidates/{cid}/confirm',json={'revision':1})
        assert task.status_code==200
        assert task.json()['source_action_item_id']==cid
