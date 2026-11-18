import json
from tests.test_llm import llm,response
from app.llm.extraction import Extraction


def test_request_id_and_body_limit(client):
    first=client.get('/health',headers={'X-Request-ID':'untrusted'})
    second=client.get('/health')
    assert first.headers['X-Request-ID']!='untrusted'
    assert first.headers['X-Request-ID']!=second.headers['X-Request-ID']
    assert client.post('/meetings',content=b'x'*(4*1024*1024+1)).status_code==413


def test_structured_logs_hide_private_content(caplog):
    caplog.set_level('INFO',logger='meeting_assistant')
    client=llm(lambda _:response('{"action_items":[]}'))
    client.generate([{'role':'user','content':'NEVER_LOG_THIS_PRIVATE_MEETING'}],Extraction)
    assert 'NEVER_LOG_THIS_PRIVATE_MEETING' not in caplog.text
    assert 'fake-test-key' not in caplog.text
    event=next(json.loads(r.message) for r in caplog.records if r.name=='meeting_assistant')
    assert event['token_usage']=={'input_tokens':10,'output_tokens':5,'total_tokens':15}
    assert event['estimated_cost'] is None
    assert {'request_id','user_id','meeting_id','model','latency_ms','status','error_type'}<=event.keys()
