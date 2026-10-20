import json
from datetime import timedelta
import time
import httpx
import jwt
import pytest
from sqlalchemy import select
from app import ai
from app.db import Category, ChatLog, Recent, Service, SessionLocal, UsageEvent, User, now
from app.main import SECRET, prune, limiter

def payload(cid):
    return {'name':'Testing Resource','description':'A testing resource with academic help.','category_id':cid,'location':'Campus test office','hours':'Mon-Fri 9-5','contact':'Use official page','source_url':'https://www.uta.edu/','tags':['testing'],'next_steps':['Check the official page.','Contact the office.'],'active':True,'verified':True}

def test_authentication_and_security(client,student):
    login=client.post('/api/auth/login',json={'email':'TEST@example.com','password':'Strong-pass123!'})
    assert login.status_code==200
    claims=jwt.decode(login.json()['access_token'],SECRET,algorithms=['HS256'],audience='mavassist-app',issuer='mavassist')
    assert claims['exp']-claims['iat']==3600
    assert client.get('/api/auth/me',headers=student).json()['role']=='student'
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={'email':'test@example.com','password':'wrong'}).status_code==401
    assert client.post('/api/auth/register',json={'name':'Bad','email':'b@b.com','password':'abcdefghij','role':'administrator'}).status_code==422
    assert client.post('/api/auth/register',json={'name':'Test','email':'test@example.com','password':'abcdefghij'}).status_code==409
    assert client.post('/api/auth/register',json={'name':'Test','email':'not-email','password':'abcdefghij'}).status_code==422
    assert client.post('/api/auth/register',json={'name':'Test','email':'unicode@a.com','password':'🙂'*30}).status_code==422
    with SessionLocal() as db:
        u=db.scalar(select(User).where(User.email=='test@example.com'))
        assert int(u.password_hash.split('$')[2])>=10
    token=jwt.encode({**claims,'exp':int(time.time())-1},SECRET,algorithm='HS256')
    assert client.get('/api/auth/me',headers={'Authorization':'Bearer '+token}).status_code==401

def test_every_admin_route_denies_student(client,student):
    # Derive the protected route inventory from the application rather than a hand-maintained subset.
    for path,operations in client.get('/openapi.json').json()['paths'].items():
        if not path.startswith('/api/admin'): continue
        url=path.replace('{sid}','1').replace('{cid}','1').replace('{nid}','1')
        for method in operations:
            if method not in {'get','post','put','patch','delete'}: continue
            r=client.request(method,url,headers=student,json={})
            assert r.status_code==403,(method,url,r.text)

def test_directory_search_filters(client):
    data=client.get('/api/services').json();assert data['total']==50
    first=data['items'][0];assert all(k in first for k in ['name','description','category','location','hours','contact'])
    assert client.get('/api/services?q=tuition').json()['items'][0]['name']=='Student Accounts'
    assert client.get('/api/services?q=sevis').json()['total']>=1
    assert client.get('/api/services?q=%25').json()['total']==0
    cats=client.get('/api/categories').json()[:2];ids=[x['id'] for x in cats]
    data=client.get('/api/services',params=[('category_ids',i) for i in ids]).json()
    assert data['items'] and all(s['category_id'] in ids for s in data['items'])
    assert client.get('/api/services',params={'limit':3,'offset':2}).json()['items']==client.get('/api/services').json()['items'][2:5]

def test_admin_service_crud_archive_and_notices(client,admin,student):
    cid=client.get('/api/categories').json()[0]['id'];body=payload(cid)
    created=client.post('/api/admin/services',json=body,headers=admin);assert created.status_code==201
    sid=created.json()['id'];body['description']='Updated resource for academic testing.'
    assert client.put(f'/api/admin/services/{sid}',json=body,headers=admin).json()['description']==body['description']
    start=now()-timedelta(hours=1);end=now()+timedelta(hours=1)
    notice={'service_id':sid,'title':'Current notice','body':'Office update for students.','starts_at':start.isoformat(),'ends_at':end.isoformat()}
    nid=client.post('/api/admin/notices',json=notice,headers=admin).json()['id']
    assert len(client.get(f'/api/services/{sid}',headers=student).json()['notices'])==1
    assert client.put(f'/api/admin/notices/{nid}',json={**notice,'title':'Revised notice'},headers=admin).status_code==200
    expired={**notice,'title':'Expired','starts_at':(now()-timedelta(days=2)).isoformat(),'ends_at':(now()-timedelta(days=1)).isoformat()}
    assert client.post('/api/admin/notices',json=expired,headers=admin).status_code==201
    assert len(client.get(f'/api/services/{sid}',headers=student).json()['notices'])==1
    assert client.post('/api/admin/notices',json={**notice,'ends_at':start.isoformat()},headers=admin).status_code==422
    assert client.get('/api/admin/notices',headers=admin).status_code==200
    assert client.delete(f'/api/admin/notices/{nid}',headers=admin).status_code==200
    assert client.patch(f'/api/admin/services/{sid}/active',json={'active':False},headers=admin).status_code==200
    assert client.get(f'/api/services/{sid}',headers=student).status_code==404
    assert all(s['id']!=sid for s in client.get('/api/services').json()['items'])
    r=client.post('/api/chat',json={'text':'Testing Resource'},headers=student).json()
    assert all(s['id']!=sid for s in r['recommendations'])
    assert any(s['id']==sid for s in client.get('/api/admin/services',headers=admin).json())
    assert client.patch(f'/api/admin/services/{sid}/active',json={'active':True},headers=admin).status_code==200

def test_versioned_admin_service_crud_and_soft_delete(client,admin,student):
    cid=client.get('/api/categories').json()[0]['id'];body=payload(cid)
    created=client.post('/api/v1/admin/services',json=body,headers=admin)
    assert created.status_code==201
    sid=created.json()['id']
    body['description']='Updated through the versioned administration API.'
    updated=client.put(f'/api/v1/admin/services/{sid}',json=body,headers=admin)
    assert updated.status_code==200 and updated.json()['description']==body['description']
    assert any(service['id']==sid for service in client.get('/api/v1/admin/services',headers=admin).json())
    archived=client.delete(f'/api/v1/admin/services/{sid}',headers=admin)
    assert archived.status_code==200 and archived.json()['active'] is False
    assert client.get(f'/api/services/{sid}',headers=student).status_code==404
    assert any(service['id']==sid and service['active'] is False for service in client.get('/api/v1/admin/services',headers=admin).json())
    restored=client.patch(f'/api/v1/admin/services/{sid}',json={'active':True},headers=admin)
    assert restored.status_code==200 and restored.json()['active'] is True

def test_category_validation_errors(client,admin):
    r=client.post('/api/admin/categories',json={'name':'New Category'},headers=admin);assert r.status_code==201;cid=r.json()['id']
    assert client.post('/api/admin/categories',json={'name':'New Category'},headers=admin).status_code==409
    assert client.put(f'/api/admin/categories/{cid}',json={'name':'Renamed'},headers=admin).status_code==200
    assert client.delete(f'/api/admin/categories/{cid}',headers=admin).status_code==200
    existing=client.get('/api/categories').json()[0]['id']
    assert client.delete(f'/api/admin/categories/{existing}',headers=admin).status_code==409
    assert client.post('/api/admin/services',json=payload(99999),headers=admin).status_code==422
    assert client.post('/api/admin/services',json={**payload(existing),'source_url':'javascript:alert(1)'},headers=admin).status_code==422
    assert client.post('/api/admin/services',json={**payload(existing),'next_steps':['x'*301,'ok']},headers=admin).status_code==422
    for url,method in [('/api/admin/services/99999','put'),('/api/admin/services/99999/active','patch'),('/api/admin/categories/99999','put'),('/api/admin/categories/99999','delete'),('/api/admin/notices/99999','delete')]:
        data=payload(existing) if method=='put' and 'services' in url else {'active':False} if method=='patch' else {'name':'No such category'}
        assert client.request(method,url,headers=admin,json=data).status_code==404

def test_personal_bookmarks_and_recent_limit(client,student,admin):
    services=client.get('/api/services').json()['items'][:12]
    for s in services: assert client.get('/api/services/'+str(s['id']),headers=student).status_code==200
    recent=client.get('/api/recent',headers=student).json();assert len(recent)==10 and recent[0]['id']==services[-1]['id']
    sid=services[0]['id'];client.get('/api/services/'+str(sid),headers=student)
    assert client.get('/api/recent',headers=student).json()[0]['id']==sid
    for _ in range(2): assert client.put(f'/api/bookmarks/{sid}',headers=student).status_code==200
    assert len(client.get('/api/bookmarks',headers=student).json())==1
    assert client.get('/api/bookmarks',headers=admin).json()==[]
    assert client.get('/api/recent',headers=admin).json()==[]
    assert client.delete(f'/api/bookmarks/{sid}',headers=student).status_code==200
    assert client.get('/api/bookmarks',headers=student).json()==[]

def test_chat_clarification_feedback_analytics_retention(client,student,admin):
    assert client.post('/api/chat',json={'text':'xyzabc qqqzzz'},headers=student).json()['mode']=='clarification'
    r=client.post('/api/chat',json={'text':'help with tuition payment'},headers=student).json()
    assert r['mode']=='grounded' and r['recommendations'][0]['name']=='Student Accounts'
    assert 'updated_at' in r['recommendations'][0] and len(r['recommendations'][0]['next_steps']) in (2,3)
    assert client.post('/api/chat/'+r['answer_id']+'/feedback',json={'helpful':True},headers=student).status_code==200
    assert client.post('/api/chat/'+r['answer_id']+'/feedback',json={'helpful':False},headers=student).status_code==409
    assert client.post('/api/chat/no-such-answer/feedback',json={'helpful':True},headers=student).status_code==404
    client.get('/api/services?q=tuition');client.get('/api/services/'+str(r['recommendations'][0]['id']),headers=student)
    data=client.get('/api/admin/analytics',headers=admin).json()
    assert data['searches'] and data['views'] and data['chat_categories'] and data['feedback']['helpful_percent']==100
    assert client.get('/api/admin/analytics?start=2026-10-14T00:00:00&end=2026-10-15T00:00:00',headers=admin).status_code==422
    with SessionLocal() as db:
        entry=db.get(ChatLog,r['answer_id']);assert not hasattr(entry,'user_id') and not hasattr(entry,'question')
        entry.created_at=now()-timedelta(days=91);db.add(UsageEvent(kind='search',term='old',created_at=now()-timedelta(days=91)));db.commit();prune(db)
        assert not db.get(ChatLog,r['answer_id'])
        assert not db.scalar(select(UsageEvent).where(UsageEvent.term=='old'))

def test_ai_timeout_fallback_and_low_confidence(client,student,monkeypatch):
    monkeypatch.setattr(ai,'API_KEY','test-key');monkeypatch.setattr(ai,'MODEL','test-model')
    monkeypatch.setattr(ai,'generate',lambda *args:(_ for _ in ()).throw(httpx.TimeoutException('forced outage')))
    started=time.monotonic();r=client.post('/api/chat',json={'text':'tuition refund'},headers=student).json()
    assert time.monotonic()-started<3 and r['mode']=='fallback' and r['recommendations'][0]['name']=='Student Accounts'
    assert r['answer'] and r['sources']
    monkeypatch.setattr(ai,'retrieve',lambda db,q:[])
    assert client.post('/api/chat',json={'text':'ambiguous question'},headers=student).json()['mode']=='clarification'


def test_llm_payload_privacy_and_unknown_id_rejection(client,monkeypatch):
    with SessionLocal() as db: passages=ai.retrieve(db,'tuition refund')
    captured=[]
    class FakeClient:
        def __init__(self,**kw): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,headers,json):
            captured.append(json)
            invalid={'answer':[{'text':'A fabricated answer','source_ids':[999999]}],'steps':[]}
            return httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':__import__('json').dumps(invalid)}]}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(ai.httpx,'Client',FakeClient);monkeypatch.setattr(ai,'API_KEY','test-key');monkeypatch.setattr(ai,'MODEL','test-model')
    clean=ai.redact('My email is student@example.com, ID 1002271374, I am Test Student and need tuition help','Test Student')
    with pytest.raises(ValueError): ai.generate(clean,[],passages)
    encoded=json.dumps(captured[0]);assert 'student@example.com' not in encoded and '1002271374' not in encoded and 'Test Student' not in encoded
    assert captured[0]['store'] is False
    assert not any(key in json.loads(captured[0]['input']) for key in ['user_id','email','name'])


def test_rate_limit_and_headers(client,monkeypatch):
    monkeypatch.setenv('RATE_LIMIT','true');limiter.clear()
    for i in range(10): assert client.post('/api/auth/login',json={'email':'none@example.com','password':'wrong'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'none@example.com','password':'wrong'}).status_code==429
    response=client.get('/health');assert response.status_code==200 and response.headers['x-content-type-options']=='nosniff'
