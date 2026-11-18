"""Opt-in, budgeted synthetic verification; never part of the automatic pytest suite."""
import argparse
import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import getproxies
from uuid import UUID

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from pydantic import SecretStr

from app.api.actions import get_llm
from app.core.config import Settings
from app.llm.client import LLMClient, LLMError
from app.llm.extraction import extract
from app.main import create_app
from app.models.user import User
from app.rag.service import company_id
from evaluation.database import isolated_database


class BudgetTransport(httpx.HTTPTransport):
    """Observe actual HTTP, preserving the system HTTPS proxy; never retain headers."""
    def __init__(self, ledger, save, limit, label):
        super().__init__(proxy=getproxies().get('https'), retries=0)
        self.ledger, self.save, self.limit, self.label = ledger, save, limit, label

    def handle_request(self, request):
        if len(self.ledger) >= self.limit:
            raise LLMError('verification_request_budget_exhausted', 503)
        row = {'case': self.label, 'http_status': None}
        self.ledger.append(row)
        self.save()  # 发出请求前持久记录，失败/中断也占预算。
        start = time.monotonic()
        try:
            response = super().handle_request(request)
            response.read()
            row['http_status'] = response.status_code
            try:
                body = response.json()
            except ValueError:
                body = {}
            if isinstance(body, dict):
                usage = body.get('usage') or {}
                row['usage'] = {k: v for k, v in usage.items() if k in
                    {'prompt_tokens', 'completion_tokens', 'total_tokens'} and type(v) is int and v >= 0} if isinstance(usage, dict) else {}
                if response.status_code == 200:
                    row['response_model'] = body.get('model')
                    message = (body.get('choices') or [{}])[0].get('message', {})
                    # This runner sends only bundled synthetic data; redact even an unexpected key echo.
                    secret = Settings().llm_api_key.get_secret_value()
                    row['synthetic_response_message'] = {k: (v.replace(secret, '[REDACTED]') if isinstance(v, str) else v)
                        for k, v in message.items() if k in {'content', 'refusal'}}
            return response
        except httpx.TransportError as exc:
            row['error_type'] = type(exc).__name__
            raise
        finally:
            row['latency_ms'] = round((time.monotonic() - start) * 1000)
            self.save()


CASES = [
    ('single', '张三周五前完成接口测试。', 1, '张三', '周五'),
    ('multiple', '李四明天提交预算表。王五下周一完成客户回访。', 2, None, None),
    ('no_actions', '今天只回顾已完成的工作：系统上周已经上线，报告昨日已归档。本次没有新增安排。', 0, None, None),
    ('missing_owner', '会议决定：周五前提交验收清单，负责人尚未确定。', 1, None, '周五'),
    ('missing_deadline', '赵六负责整理测试记录，具体截止时间尚未确定。', 1, '赵六', None),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['extraction', 'workflow-rag', 'rag-recheck'], required=True)
    parser.add_argument('--output', type=Path, default=Path('outputs/evaluations/provider_round1'))
    parser.add_argument('--max-requests', type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.max_requests <= 30:
        parser.error('max-requests must be 1..30')
    args.output.mkdir(parents=True, exist_ok=True)
    # 保留此前阶段报告，重跑不能抹去真实失败。
    for suffix in ['.json', '_bad_cases.json']:
        prior = args.output / (args.stage + suffix)
        if prior.exists():
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            prior.with_name(prior.stem + '_' + stamp + '.json').write_bytes(prior.read_bytes())
    ledger_path = args.output / 'requests.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    settings = Settings().model_copy(update={'llm_max_attempts': 1})
    if not all([settings.llm_api_key.get_secret_value(), settings.llm_base_url, settings.llm_model]):
        parser.error('Real LLM settings required')
    def save():
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2))
    def client(label):
        return LLMClient(settings, transport=BudgetTransport(ledger, save, args.max_requests, label))
    report = {'stage': args.stage, 'model': settings.llm_model, 'synthetic': True, 'cases': []}
    try:
        if args.stage == 'extraction':
            for name, text, count, owner, deadline in CASES:
                parsed = extract(text, client(name))
                row = {'name': name, 'input': text, 'output': parsed.model_dump(), 'pydantic_validated': True}
                report['cases'].append(row)
                checks = [len(parsed.action_items) == count]
                if count == 1:
                    item = parsed.action_items[0]
                    checks += [item.assignee_name == owner,
                        item.deadline is None if deadline is None else deadline in (item.deadline or '')]
                row['passed'] = all(checks)
            assert all(r['passed'] for r in report['cases']), 'Synthetic extraction expectation failed'
        else:
            prior = json.loads((args.output / 'extraction.json').read_text())
            assert prior['status'] == 'passed', 'Extraction must pass before workflow/RAG'
            with isolated_database() as url:
                app = create_app(settings.model_copy(update={'database_url': SecretStr(url), 'app_env': 'test'}))
                # 仅替换观测依赖，仍使用真实网络Transport、真实Provider和真实数据库。
                app.dependency_overrides[get_llm] = lambda: client('workflow')
                with TestClient(app) as api:
                    password = secrets.token_urlsafe(24)
                    user = api.post('/auth/register', json={'email': 'real-eval@example.com', 'display_name': 'Synthetic evaluator', 'password': password})
                    assert user.status_code == 201
                    login = api.post('/auth/login', json={'email': 'real-eval@example.com', 'password': password})
                    assert login.status_code == 200
                    api.headers['Authorization'] = 'Bearer ' + login.json()['access_token']
                    if args.stage == 'workflow-rag':
                        mid = api.post('/meetings', json={'title': 'Synthetic real-provider workflow', 'content': CASES[0][1]}).json()['id']
                        response = api.post(f'/meetings/{mid}/extract')
                        assert response.status_code == 201
                        items = response.json()
                        assert len(items) == 1 and items[0]['status'] == 'pending'
                        assert api.get('/tasks').json() == []
                        item = items[0]
                        edited = api.patch('/candidates/' + item['id'], json={'revision': item['revision'], 'assignee_user_id': user.json()['id']})
                        assert edited.status_code == 200
                        revision = edited.json()['revision']
                        confirmed = api.post('/candidates/' + item['id'] + '/confirm', json={'revision': revision})
                        assert confirmed.status_code == 200
                        again = api.post('/candidates/' + item['id'] + '/confirm', json={'revision': revision})
                        assert again.status_code == 200 and again.json()['id'] == confirmed.json()['id']
                        assert len(api.get('/tasks/my').json()) == 1
                        report['workflow'] = {'passed': True, 'candidate': items[0], 'task': confirmed.json(),
                            'confirmation_actor': 'automated authenticated API test explicitly authorized by user; not a human UI click',
                            'tasks_before_confirmation': 0, 'duplicate_confirmation_same_task': True}
                    with Session(app.state.engine) as session:
                        session.get(User, UUID(user.json()['id'])).is_owner = True
                        session.commit()
                    assert api.post('/knowledge/company/ingest').status_code == 200
                    fixtures = json.loads(Path('evaluation/synthetic_meetings.json').read_text())['meetings']
                    names = {str(company_id(p.stem)): p.stem for p in Path('data/company_docs').glob('*.md')}
                    for fixture in fixtures:
                        mid = api.post('/meetings', json={'title': fixture['title'], 'content': fixture['content']}).json()['id']
                        assert api.post('/meetings/' + mid + '/index').status_code == 200
                        names[mid] = 'meeting:' + fixture['slug']
                    questions = [json.loads(line) for line in Path('evaluation/rag_questions.jsonl').read_text().splitlines()]
                    # 少量固定子集：事实/混淆/跨文档/历史/无答案，不运行完整25题生成。
                    selected = [questions[i] for i in ([0, 1, 7, 19, 22, 23] if args.stage == 'workflow-rag' else [23])]
                    for q in selected:
                        app.dependency_overrides[get_llm] = lambda label=q['id']: client(label)
                        sources = api.post('/knowledge/search', json={'question': q['question'], 'k': 5}).json()['sources']
                        reply = api.post('/knowledge/ask', json={'question': q['question'], 'k': 5})
                        row = {**q, 'http_status': reply.status_code, 'retrieved_context': sources}
                        report['cases'].append(row)
                        if reply.status_code != 200:
                            row.update(passed=False, error_type=reply.json().get('detail'))
                            continue
                        answer = reply.json()
                        cited = {names[s['source_id']] for s in answer['sources']}
                        gold = set(q['expected_sources'])
                        row.update(answer=answer, cited_sources=sorted(cited),
                            source_precision=len(cited & gold)/len(cited) if cited else (1.0 if not gold else 0.0),
                            refusal_correct=answer['no_answer'] == (not gold))
                        for source in answer['sources']:
                            resolved = api.get('/knowledge/chunks/' + source['chunk_id'])
                            assert resolved.status_code == 200 and source['quote'] in resolved.json()['content']
                        row['passed'] = row['refusal_correct'] and (bool(cited & gold) if gold else not cited)
                    report['database_cleanup'] = 'isolated database dropped after verification'
                    assert all(r['passed'] for r in report['cases']), 'RAG subset has genuine failures; inspect report'
        report['status'] = 'passed'
    except (LLMError, AssertionError) as exc:
        report['status'] = 'failed'
        report['error_type'] = exc.kind if isinstance(exc, LLMError) else str(exc)
    finally:
        report['request_attempts_cumulative'] = len(ledger)
        (args.output / (args.stage + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2))
        bad = [r for r in report['cases'] if r.get('passed') is False]
        (args.output / (args.stage + '_bad_cases.json')).write_text(json.dumps(bad, ensure_ascii=False, indent=2))
    print(json.dumps({'stage': args.stage, 'status': report['status'], 'attempts_cumulative': len(ledger),
        'passed_cases': sum(r.get('passed', False) for r in report['cases']), 'cases': len(report['cases'])}))
    if report['status'] != 'passed': raise SystemExit(1)


if __name__ == '__main__':
    main()
