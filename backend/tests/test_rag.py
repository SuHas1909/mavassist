import json
import httpx
import pytest
from sqlalchemy import select
from app import ai
from app.db import KnowledgeChunk, Service, SessionLocal
from app.knowledge import import_passages, seed_knowledge

def test_refund_regression_context_citations_and_no_it_office(client,student):
    r=client.post('/api/chat',headers=student,json={'text':'I have paid extra tuition fee to accounts how to get refund!'}).json()
    assert r['mode']=='grounded'
    names=[s['name'] for s in r['recommendations']]
    assert names[0]=='Student Accounts' and 'OIT Help Desk' not in names and len(names)<=3
    assert r['recommendations'][0]['role']=='recommended' and r['recommendations'][0]['reason']
    text=' '.join(p['text'] for p in r['answer']+r['steps']).lower()
    assert 'credit balance' in text and 'refund' in text
    assert r['answer'] and r['steps'] and r['sources']
    allowed={s['id'] for s in r['sources']}
    assert all(p['source_ids'] and set(p['source_ids'])<=allowed for p in r['answer']+r['steps'])
    assert all(s['url'].startswith('https://www.uta.edu/business-affairs/student-accounts/') for s in r['sources'])
    assert 'guaranteed' not in text and 'approved your' not in text

def test_refund_followup_and_new_topic(client,student):
    history=[{'question':'I paid too much tuition. How do I get a refund?','answer':'Published refund guidance.'}]
    r=client.post('/api/chat',headers=student,json={'text':'How long does it take?','history':history}).json()
    text=' '.join(p['text'] for p in r['answer'])
    assert 'after processing' in text.lower() or 'after' in text.lower()
    assert r['recommendations'][0]['name']=='Student Accounts'
    r=client.post('/api/chat',headers=student,json={'text':'My wifi password is not working','history':history}).json()
    assert r['recommendations'][0]['name']=='OIT Help Desk'

def test_conditional_flywire_rule_not_applied_to_every_refund(client,student):
    r=client.post('/api/chat',headers=student,json={'text':'I paid extra tuition and want a refund'}).json()
    assert not any('Flywire' in p['text'] for p in r['answer'])
    r=client.post('/api/chat',headers=student,json={'text':'What happens to a Flywire overpayment refund above $500?'}).json()
    assert any('originating bank' in p['text'] for p in r['answer'])

def test_archiving_excludes_source_passages(client,student,admin):
    with SessionLocal() as db: sid=db.scalar(select(Service.id).where(Service.name=='Student Accounts'))
    client.patch(f'/api/admin/services/{sid}/active',json={'active':False},headers=admin)
    r=client.post('/api/chat',headers=student,json={'text':'tuition refund overpayment'}).json()
    assert not any(s['name']=='Student Accounts' for s in r['recommendations'])
    assert not any('/student-accounts/' in s['url'] for s in r['sources'])

def test_valid_generated_answer_and_prompt_carries_context(client,student,monkeypatch):
    captured=[]
    class FakeClient:
        def __init__(self,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,headers,json):
            captured.append(json);context=__import__('json').loads(json['messages'][-1]['content']);sid=context['sources'][0]['source_id']
            result={'answer':[{'text':'Check whether your account has a credit balance; Student Accounts handles refund questions.','source_ids':[sid]}],'steps':[{'text':'Review the cited official guidance.','source_ids':[sid]}]}
            return httpx.Response(200,json={'choices':[{'message':{'content':__import__('json').dumps(result)}}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(ai.httpx,'Client',FakeClient);monkeypatch.setattr(ai,'API_KEY','test');monkeypatch.setattr(ai,'MODEL','test-model')
    r=client.post('/api/chat',headers=student,json={'text':'How do I get it back?','history':[{'question':'I paid extra tuition and need a refund','answer':'Test Student 1002271374 student@example.com'}]}).json()
    assert r['mode']=='rag' and r['answer'][0]['text'].startswith('Check whether')
    raw=captured[0]['messages'][-1]['content'];payload=json.loads(raw);assert payload['sources'] and payload['conversation_history']
    assert all(x not in raw for x in ['1002271374','student@example.com','Test Student'])
    assert 'credit balance' in ' '.join(s['content'] for s in payload['sources']).lower()

@pytest.mark.parametrize('result',[
    {'answer':[{'text':'Unsupported','source_ids':[]}],'steps':[]},
    {'answer':[{'text':'Invented citation','source_ids':[999999]}],'steps':[]},
    {'answer':[],'steps':[]},
    {'service_ids':[1]},
])
def test_malformed_generation_rejected(client,monkeypatch,result):
    with SessionLocal() as db: passages=ai.retrieve(db,'tuition refund')
    class FakeClient:
        def __init__(self,**kw): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,url,**kw): return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(result)}}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(ai.httpx,'Client',FakeClient);monkeypatch.setattr(ai,'API_KEY','test');monkeypatch.setattr(ai,'MODEL','test')
    with pytest.raises(ValueError): ai.generate('tuition refund',[],passages)

def test_knowledge_import_idempotence_and_validation(client,tmp_path):
    with SessionLocal() as db:
        original=len(list(db.scalars(select(KnowledgeChunk))))
        seed_knowledge(db);assert len(list(db.scalars(select(KnowledgeChunk))))==original
        row={'key':'new-reviewed-guide','service_name':'Student Accounts','title':'Example reviewed guide','content':'Contact the official service for a specific account question.','source_url':'https://www.uta.edu/','steps':['Review the guide.'],'keywords':['account'],'reviewed_at':'2026-10-14'}
        p=tmp_path/'knowledge.json';p.write_text(json.dumps([row]));assert import_passages(db,p)==1
        assert import_passages(db,p)==1
        assert len(list(db.scalars(select(KnowledgeChunk))))==original+1
        p.write_text(json.dumps([{**row,'source_url':'javascript:alert(1)'}]))
        with pytest.raises(ValueError): import_passages(db,p)

def test_bounded_history_and_no_history_persistence(client,student):
    assert client.post('/api/chat',headers=student,json={'text':'hello','history':[{'question':'q','answer':'a'}]*4}).status_code==422
    r=client.post('/api/chat',headers=student,json={'text':'xyzabc qqqzzz'}).json();assert r['mode']=='clarification' and r['answer']==[]

def test_semantic_path_uses_embeddings_without_a_live_model(client,monkeypatch):
    class Vector(list):
        def tolist(self): return list(self)
    class Encoder:
        def encode(self,text,**kwargs): return Vector([1.0]+[0.0]*383)
    monkeypatch.setattr(ai,'MODE','rag');monkeypatch.setattr(ai,'encoder',lambda:Encoder())
    with SessionLocal() as db:
        chunks=list(db.scalars(select(KnowledgeChunk)))
        for c in chunks: c.embedding=([1.0] if c.key=='uta-refund-overpayment' else [-1.0])+[0.0]*383
        db.commit()
        ranked=ai.retrieve(db,'recover excess money')
        assert ranked and any(c.key=='uta-refund-overpayment' for c in ranked)
        s=db.get(Service,chunks[0].service_id);ai.embed(s);assert len(s.embedding)==384
        ai.embed_chunk(chunks[0]);assert len(chunks[0].embedding)==384
