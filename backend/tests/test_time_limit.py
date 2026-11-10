"""NFR-01: the hosted model gets a total time limit per question; past it the answer comes from cited sources."""
import json
import logging
import time
import httpx
from app import ai


def provider(delay, captured):
    """Fake OpenRouter client that waits `delay` seconds, then routes to the first hinted office with a cited answer."""
    class FakeClient:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, url, headers, json):
            captured.append(url); time.sleep(delay)
            payload = __import__('json').loads(json['messages'][-1]['content'])
            sid = payload['retrieval_hints'][0]['service_id']
            source = next(o for o in payload['knowledge'] if o['service_id'] == sid)['passages'][0]['source_id']
            reply = {'intent': 'campus', 'urgency': 'normal', 'opening': 'Here is who can help.', 'primary_service_id': sid,
                     'reason': 'It handles this.', 'alternatives': [], 'answer': [{'text': 'They can help with this.', 'source_ids': [source]}],
                     'steps': [], 'clarifying_question': None, 'message': None}
            return httpx.Response(200, json={'choices': [{'message': {'content': __import__('json').dumps(reply)}}]}, request=httpx.Request('POST', url))
    return FakeClient


def use_provider(monkeypatch, delay, limit, captured):
    monkeypatch.setattr(ai.httpx, 'Client', provider(delay, captured))
    monkeypatch.setattr(ai, 'API_KEY', 'sk-or-test'); monkeypatch.setattr(ai, 'MODEL', 'test/model')
    monkeypatch.setattr(ai, 'LLM_TOTAL_TIMEOUT', limit)


def test_slow_provider_falls_back_to_cited_sources_within_the_limit(client, student, monkeypatch, caplog):
    captured = []
    use_provider(monkeypatch, delay=1.5, limit=0.3, captured=captured)
    start = time.monotonic()
    with caplog.at_level(logging.WARNING, logger='mavassist.ai'):
        r = client.post('/api/chat', json={'text': 'How do I pay my tuition bill?'}, headers=student).json()
    elapsed = time.monotonic() - start
    assert captured, 'the provider should have been called'
    assert r['mode'] == 'fallback' and r['recommendations']
    assert r['sources'] and r['answer'] and all(p['source_ids'] for p in r['answer']), 'fallback must be cited summaries'
    assert elapsed < 1.4, f'answer took {elapsed:.2f} s; the 0.3 s limit should have cut the 1.5 s provider call'
    assert any('exceeded the 0.3 s total time limit' in rec.getMessage() for rec in caplog.records)
    assert ai.llm_ready(), 'a slow answer must not trip the circuit breaker'


def test_fast_provider_within_the_limit_still_gives_a_hosted_answer(client, student, monkeypatch):
    captured = []
    use_provider(monkeypatch, delay=0.05, limit=2.0, captured=captured)
    r = client.post('/api/chat', json={'text': 'How do I pay my tuition bill?'}, headers=student).json()
    assert captured and r['mode'] == 'rag'


def test_limit_zero_disables_the_total_time_limit(client, student, monkeypatch):
    captured = []
    use_provider(monkeypatch, delay=0.4, limit=0, captured=captured)
    r = client.post('/api/chat', json={'text': 'How do I pay my tuition bill?'}, headers=student).json()
    assert captured and r['mode'] == 'rag'
