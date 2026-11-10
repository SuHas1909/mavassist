"""Parsing and logging of hosted-model replies: lenient JSON extraction, strict validation, no content in logs."""
import json
import logging
import httpx
import pytest
from app import ai


def test_plain_json_object_is_parsed():
    assert ai.parse_json_object('{"intent":"greeting"}') == {'intent': 'greeting'}


@pytest.mark.parametrize('reply', [
    '{"intent":"greeting"}\nHope this helps!',                 # trailing remark after the object
    'Here is the JSON: {"intent":"greeting"}',                 # leading text
    '<think>pick an office first</think>{"intent":"greeting"}',  # reasoning tags
    '```json\n{"intent":"greeting"}\n```',                      # code fence
])
def test_first_json_object_is_extracted(reply):
    assert ai.parse_json_object(reply) == {'intent': 'greeting'}


@pytest.mark.parametrize('reply,error', [
    ('', 'Empty model reply'),
    ('<think>only thinking</think>', 'Empty model reply'),
    ('["not", "an", "object"]', 'Expected a JSON object'),
])
def test_unusable_replies_are_still_rejected(reply, error):
    with pytest.raises(ValueError, match=error):
        ai.parse_json_object(reply)


def test_reply_without_any_object_is_rejected():
    with pytest.raises(json.JSONDecodeError):
        ai.parse_json_object('Sorry, I cannot answer that.')


def test_reject_reason_never_contains_model_output():
    secret = 'student-said-something-private'
    for exc in (json.JSONDecodeError('Extra data', '{"a":1} ' + secret, 8), KeyError(secret + ' with spaces'),
                ValueError(f"invalid literal for int() with base 10: '{secret}'"), TypeError(secret)):
        assert secret not in ai.reject_reason(exc)
    assert ai.reject_reason(KeyError('intent')) == 'KeyError: missing field intent'
    assert ai.reject_reason(ValueError('Unknown intent')) == 'ValueError: Unknown intent'


def raw_reply_client(content):
    class FakeClient:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, url, headers, json):
            return httpx.Response(200, json={'choices': [{'message': {'content': content}}]}, request=httpx.Request('POST', url))
    return FakeClient


def test_rejected_reply_is_logged_without_content_and_answer_falls_back(client, student, monkeypatch, caplog):
    secret = 'PRIVATE-MODEL-TEXT'
    monkeypatch.setattr(ai.httpx, 'Client', raw_reply_client(secret + ' no json here'))
    monkeypatch.setattr(ai, 'API_KEY', 'sk-or-test'); monkeypatch.setattr(ai, 'MODEL', 'test/model')
    with caplog.at_level(logging.WARNING, logger='mavassist.ai'):
        r = client.post('/api/chat', json={'text': 'How do I pay my tuition bill?'}, headers=student).json()
    assert r['mode'] == 'fallback' and r['recommendations']
    lines = [rec.getMessage() for rec in caplog.records if rec.name == 'mavassist.ai']
    assert any('Hosted AI reply rejected (JSONDecodeError' in line for line in lines)
    assert all(secret not in line for line in lines)
