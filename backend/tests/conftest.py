import os
import tempfile
from pathlib import Path
import pytest

# TEST_DATABASE_URL allows the same suite to run against pgvector/PostgreSQL in CI.
os.environ['DATABASE_URL']=os.getenv('TEST_DATABASE_URL','sqlite:///'+str(Path(tempfile.gettempdir())/('mavassist-test-'+str(os.getpid())+'.db')).replace('\\','/'))
os.environ['JWT_SECRET']='test-only-secret-not-for-deployment-1234567890'
os.environ['AI_MODE']='keyword'
os.environ['APP_ENV']='development'
os.environ['RATE_LIMIT']='false'
from app.db import Base, SessionLocal, User, engine
from app.seed import seed
from app.main import app, session
from fastapi.testclient import TestClient
from sqlalchemy import text

@pytest.fixture()
def client():
    if engine.dialect.name=='postgresql':
        with engine.begin() as c: c.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with SessionLocal() as db: seed(db)
    from app import ai;ai.AI_DOWN_UNTIL=0.0
    with TestClient(app) as c: yield c

@pytest.fixture()
def student(client):
    r=client.post('/api/auth/register',json={'name':'Test Student','email':'test@example.com','password':'Strong-pass123!'})
    assert r.status_code==201
    return {'Authorization':'Bearer '+r.json()['access_token']}

@pytest.fixture()
def admin(client):
    import bcrypt
    with SessionLocal() as db:
        u=User(name='Admin Tester',email='admin@example.com',password_hash=bcrypt.hashpw(b'Admin-pass123!',bcrypt.gensalt(12)).decode(),role='administrator')
        db.add(u);db.commit();token=session(u)['access_token']
    return {'Authorization':'Bearer '+token}
