import json
import httpx
import pytest
from app.core.config import Settings
from app.llm.client import LLMClient, LLMError
from app.llm.extraction import Extraction, extract


def llm(handler, sleeps=None):
    return LLMClient(Settings(_env_file=None, database_url='postgresql+psycopg://localhost/test',
        jwt_secret='test-only-'*8, llm_api_key='fake-test-key', llm_base_url='https://provider.invalid/v1', llm_model='mock'),
        transport=httpx.MockTransport(handler), sleep=(sleeps.append if sleeps is not None else lambda x: None))


def response(content):
    return httpx.Response(200, json={'choices':[{'finish_reason':'stop','message':{'content':content}}],
        'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}})


def test_extraction_and_empty():
    item = {'task':'完成测试','assignee_name':'小张','deadline':'周五','evidence':'小张周五完成测试。'}
    result = extract('小张周五完成测试。', llm(lambda _: response(json.dumps({'action_items':[item]}))))
    assert result.action_items[0].assignee_name == '小张'
    assert extract('没有安排。', llm(lambda _: response('{"action_items":[]}'))).action_items == []


@pytest.mark.parametrize('content',['not json','{}','{"action_items": null}',
    '{"action_items":[{"task":123,"assignee_name":null,"deadline":null,"evidence":"abc"}]}',
    '{"action_items":[{"task":"a","evidence":"abc"}]}'])
def test_invalid_output(content):
    with pytest.raises(LLMError,match='invalid_structured_output'):
        llm(lambda _: response(content)).generate([],Extraction)


def test_bad_evidence():
    item = {'task':'完成测试','assignee_name':None,'deadline':None,'evidence':'编造证据'}
    with pytest.raises(LLMError,match='unsupported_evidence'):
        extract('原文',llm(lambda _: response(json.dumps({'action_items':[item]}))))


@pytest.mark.parametrize('status',[429,500,503])
def test_limited_retry(status):
    calls=[]; waits=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(status,headers={'Retry-After':'100'})
    with pytest.raises(LLMError): llm(handler,waits).generate([],Extraction)
    assert len(calls)==3 and waits==[10,10]


@pytest.mark.parametrize('status',[401,403,400])
def test_no_retry(status):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(status)
    with pytest.raises(LLMError): llm(handler).generate([],Extraction)
    assert len(calls)==1


@pytest.mark.parametrize('error',[httpx.ConnectTimeout,httpx.ReadTimeout])
def test_timeout(error):
    calls=[]
    def handler(request):
        calls.append(request);raise error('private provider details')
    with pytest.raises(LLMError) as exc: llm(handler).generate([],Extraction)
    assert exc.value.status_code==504 and len(calls)==3


def test_transient_success():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(503) if len(calls)==1 else response('{"action_items":[]}')
    assert llm(handler).generate([],Extraction).action_items==[]
    assert len(calls)==2


def test_long_windows_cover_and_reject_partial_failure():
    from app.llm.extraction import text_windows
    text='小张周五完成测试。\n' * 1000
    windows=text_windows(text)
    assert windows[0].startswith('小张') and windows[-1].endswith('。\n')
    assert len(windows)>1
    calls=[]
    def handler(request):
        calls.append(request)
        return response('{"action_items":[]}') if len(calls)==1 else response('invalid')
    with pytest.raises(LLMError): extract(text,llm(handler))
    with pytest.raises(LLMError,match='meeting_too_long_for_extraction'): extract('x'*50001,llm(handler))


def test_current_and_legacy_generation_parameters():
    calls=[]
    def handler(request):
        calls.append(json.loads(request.content))
        return response('{"action_items":[]}')
    client=llm(handler)
    client.generate([],Extraction)
    assert calls[-1]['max_completion_tokens']==4096
    assert 'max_tokens' not in calls[-1] and 'temperature' not in calls[-1]
    client.settings=client.settings.model_copy(update={'llm_token_limit_parameter':'max_tokens','llm_temperature':0.0})
    client.generate([],Extraction)
    assert calls[-1]['max_tokens']==4096 and calls[-1]['temperature']==0
    assert 'max_completion_tokens' not in calls[-1]


def test_evidence_whitespace_restored_without_fuzzy_matching():
    from app.llm.extraction import restore_evidence
    assert restore_evidence('小张负责\n提交报告。', '小张负责提交报告。') == '小张负责\n提交报告。'
    assert restore_evidence('提交原稿。', '提交修改稿。') is None
    assert restore_evidence('甲\n乙，甲 乙', '甲乙') is None
    assert restore_evidence('原文', '') is None


def test_evidence_repair_once_and_reject_if_still_unsupported():
    calls=[]
    item={'task':'提交报告','assignee_name':None,'deadline':None,'evidence':'改写原文'}
    def handler(request):
        calls.append(request)
        return response(json.dumps({'action_items':[item]}))
    with pytest.raises(LLMError,match='unsupported_evidence'):
        extract('原文',llm(handler))
    assert len(calls)==2


def test_evidence_repair_keeps_valid_original_quote():
    calls=[]
    def handler(request):
        calls.append(request)
        item={'task':'提交报告','assignee_name':None,'deadline':None,'evidence':'原话明天提交报告。' if len(calls)==2 else '错误引用'}
        return response(json.dumps({'action_items':[item]}))
    assert extract('原话明天提交报告。',llm(handler)).action_items[0].evidence=='原话明天提交报告。'
    assert len(calls)==2


def test_numbered_evidence_reconstructed_from_source():
    def handler(request):
        payload=json.loads(request.content)
        assert '[L1] 小张负责' in payload['messages'][1]['content']
        return response(json.dumps({'action_items':[{'task':'提交报告','assignee_name':'小张','deadline':None,'evidence_start_line':1,'evidence_end_line':2}]}))
    item=extract('小张负责\n提交报告。\n背景。',llm(handler)).action_items[0]
    assert item.evidence=='小张负责\n提交报告。'


@pytest.mark.parametrize('start,end',[(3,2),(1,99),(None,1)])
def test_invalid_evidence_line_range_rejected(start,end):
    item={'task':'提交报告','assignee_name':None,'deadline':None,'evidence_start_line':start,'evidence_end_line':end}
    with pytest.raises(LLMError,match='unsupported_evidence'):
        extract('会议内容。',llm(lambda _:response(json.dumps({'action_items':[item]}))))
