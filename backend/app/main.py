import asyncio
import contextlib
import os
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated
import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Text, case, delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import Bookmark, Category, ChatLog, Notice, Recent, Service, SessionLocal, UsageEvent, User, engine, now
from . import ai
from .schemas import ActiveInput, CategoryInput, Feedback, Login, NoticeInput, Question, Register, ServiceInput

SECRET = os.getenv('JWT_SECRET', '')
if len(SECRET) < 32 or SECRET.startswith('REPLACE_WITH'): raise RuntimeError('Set JWT_SECRET to a random string of at least 32 characters. Run scripts/configure.py.')
ENV = os.getenv('APP_ENV', 'development')
ORIGINS = [s.strip() for s in os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',') if s.strip()]
if '*' in ORIGINS: raise RuntimeError('Use explicit CORS_ORIGINS')
if ENV=='production' and (not all(s.startswith('https://') for s in ORIGINS) or not os.getenv('DATABASE_URL','').startswith(('postgres://','postgresql'))):
    raise RuntimeError('Production requires HTTPS frontend origins and PostgreSQL')

def prune(db):
    cutoff=now()-timedelta(days=90)
    db.execute(delete(ChatLog).where(ChatLog.created_at<cutoff))
    db.execute(delete(UsageEvent).where(UsageEvent.created_at<cutoff))
    db.commit()

async def retention_loop():
    while True:
        with SessionLocal() as db: prune(db)
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app):
    # Schema creation is an explicit Alembic migration step, not a hidden startup change.
    with engine.connect() as conn: conn.execute(text('SELECT 1'))
    if ai.MODE=='rag': ai.encoder()  # Fail clearly if MiniLM is not installed/downloaded.
    task=asyncio.create_task(retention_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError): await task

app=FastAPI(title='MavAssist API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=ORIGINS,allow_credentials=False,allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Authorization','Content-Type'])
limiter: dict[tuple,deque]=defaultdict(deque)

@app.middleware('http')
async def guard(request: Request, call_next):
    # ponytail: one-process limiter suits the course demo; use shared Redis when scaling replicas.
    if request.url.path.startswith('/api') and os.getenv('RATE_LIMIT','true')=='true':
        group='auth' if '/auth/' in request.url.path else 'chat' if request.url.path=='/api/chat' else 'api'
        key=(request.client.host if request.client else 'unknown',group); clock=time.monotonic()
        if len(limiter)>5000:
            for old in list(limiter):
                if not limiter[old] or limiter[old][-1]<clock-60: limiter.pop(old,None)
            if len(limiter)>5000: return JSONResponse({'detail':'Server busy. Try again shortly.'},status_code=429)
        hits=limiter[key]
        while hits and hits[0]<clock-60: hits.popleft()
        if len(hits)>=({'auth':10,'chat':20,'api':180}[group]): return JSONResponse({'detail':'Too many requests. Try again in one minute.'},status_code=429,headers={'Retry-After':'60'})
        hits.append(clock)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    if ENV=='production': response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    return response

def get_db():
    with SessionLocal() as db: yield db
DB=Annotated[Session,Depends(get_db)]
bearer=HTTPBearer(auto_error=False)
def current(db: DB, credential: Annotated[HTTPAuthorizationCredentials | None,Depends(bearer)]):
    if not credential: raise HTTPException(401,'Please sign in')
    try:
        data=jwt.decode(credential.credentials,SECRET,algorithms=['HS256'],issuer='mavassist',audience='mavassist-app',options={'require':['exp','sub','iat']})
        user=db.get(User,int(data['sub']))
    except (jwt.PyJWTError,ValueError,TypeError): raise HTTPException(401,'Session expired. Please sign in again.')
    if not user: raise HTTPException(401,'Account not found')
    return user
USER=Annotated[User,Depends(current)]
def administrator(user: USER):
    if user.role!='administrator': raise HTTPException(403,'Administrator access required')
    return user
ADMIN=Annotated[User,Depends(administrator)]
def profile(user): return {'id':user.id,'name':user.name,'email':user.email,'role':user.role}
def session(user):
    clock=now();expires=clock+timedelta(minutes=60)
    token=jwt.encode({'sub':str(user.id),'iat':clock,'exp':expires,'iss':'mavassist','aud':'mavassist-app'},SECRET,algorithm='HS256')
    return {'access_token':token,'token_type':'bearer','expires_at':expires.isoformat(),'user':profile(user)}
def save(db):
    try: db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'This record already exists or is still in use')
def active_service(db,sid):
    s=db.get(Service,sid)
    if not s or not s.active: raise HTTPException(404,'Service not found')
    return s
def service_json(s,db):
    return {field:getattr(s,field) for field in ['id','name','description','category_id','location','hours','contact','source_url','tags','next_steps','active','verified','updated_at']} | {'category':db.get(Category,s.category_id).name}

@app.get('/health')
def health(db: DB):
    db.execute(text('SELECT 1'));return {'status':'ok','ai_mode':ai.MODE,'llm':bool(ai.API_KEY and ai.MODEL),'llm_model':ai.MODEL or None}
@app.post('/api/auth/register',status_code=201)
def register(body: Register,db: DB):
    if db.scalar(select(User).where(User.email==body.email)): raise HTTPException(409,'An account with this email already exists')
    user=User(name=body.name,email=body.email,password_hash=bcrypt.hashpw(body.password.encode(),bcrypt.gensalt(rounds=12)).decode(),role='student')
    db.add(user);save(db);return session(user)
@app.post('/api/auth/login')
def login(body: Login,db: DB):
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    try: valid=user and bcrypt.checkpw(body.password.encode(),user.password_hash.encode())
    except ValueError: valid=False
    if not valid: raise HTTPException(401,'Email or password is incorrect')
    return session(user)
@app.get('/api/auth/me')
def me(user: USER): return profile(user)

@app.get('/api/categories')
def categories(db: DB): return [{'id':c.id,'name':c.name} for c in db.scalars(select(Category).order_by(Category.name))]
@app.get('/api/services')
def services(db: DB,q: str=Query('',max_length=200),category_ids: list[int]=Query(default=[]),limit: int=Query(100,ge=1,le=100),offset: int=Query(0,ge=0)):
    query=select(Service).where(Service.active.is_(True));order=[Service.name]
    if q:
        # Literal substring matching; escape LIKE metacharacters and bind all parameters.
        term='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        query=query.where(or_(Service.name.ilike(term,escape='\\'),Service.description.ilike(term,escape='\\'),Service.tags.cast(Text).ilike(term,escape='\\')))
        # Relevance order: name matches, then tag matches, then description-only matches.
        order=[case((Service.name.ilike(term,escape='\\'),0),(Service.tags.cast(Text).ilike(term,escape='\\'),1),else_=2),Service.name]
        db.add(UsageEvent(kind='search',term=ai.redact(q)[:200]));save(db)
    if category_ids: query=query.where(Service.category_id.in_(category_ids))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    return {'items':[service_json(s,db) for s in db.scalars(query.order_by(*order).offset(offset).limit(limit))],'total':total}

@app.get('/api/services/{sid}')
def detail(sid: int,db: DB,user: USER):
    s=active_service(db,sid)
    recent=db.scalar(select(Recent).where(Recent.user_id==user.id,Recent.service_id==sid))
    if recent: recent.viewed_at=now()
    else: db.add(Recent(user_id=user.id,service_id=sid,viewed_at=now()))
    db.flush()
    stale=list(db.scalars(select(Recent.id).where(Recent.user_id==user.id).order_by(Recent.viewed_at.desc(),Recent.id.desc()).offset(10)))
    if stale: db.execute(delete(Recent).where(Recent.id.in_(stale)))
    db.add(UsageEvent(kind='view',service_id=sid,category_id=s.category_id));save(db)
    clock=now()
    notices=[{'id':n.id,'title':n.title,'body':n.body,'starts_at':n.starts_at,'ends_at':n.ends_at} for n in db.scalars(select(Notice).where(Notice.service_id==sid,Notice.starts_at<=clock,Notice.ends_at>=clock))]
    return service_json(s,db)|{'notices':notices}

@app.get('/api/bookmarks')
def bookmarks(db: DB,user: USER):
    return [service_json(s,db) for s in db.scalars(select(Service).join(Bookmark,Bookmark.service_id==Service.id).where(Bookmark.user_id==user.id,Service.active.is_(True)).order_by(Service.name))]
@app.put('/api/bookmarks/{sid}')
def bookmark(sid: int,db: DB,user: USER):
    active_service(db,sid)
    if not db.scalar(select(Bookmark).where(Bookmark.user_id==user.id,Bookmark.service_id==sid)):
        db.add(Bookmark(user_id=user.id,service_id=sid));save(db)
    return {'saved':True}
@app.delete('/api/bookmarks/{sid}')
def unbookmark(sid: int,db: DB,user: USER):
    db.execute(delete(Bookmark).where(Bookmark.user_id==user.id,Bookmark.service_id==sid));save(db);return {'saved':False}
@app.get('/api/recent')
def recent(db: DB,user: USER):
    return [service_json(s,db) for s in db.scalars(select(Service).join(Recent,Recent.service_id==Service.id).where(Recent.user_id==user.id,Service.active.is_(True)).order_by(Recent.viewed_at.desc(),Recent.id.desc()).limit(10))]

@app.post('/api/chat')
def chat(body: Question,db: DB,user: USER):
    clean=ai.redact(body.text,user.name)
    history=[{'question':ai.redact(t.question,user.name),'answer':ai.redact(t.answer,user.name)} for t in body.history]
    result=ai.answer_question(db,clean,history)
    chosen=[s for s,_ in result['services']];reasons=[r for _,r in result.pop('services')];mode=result['mode']
    answer_id=str(uuid.uuid4())
    # Redirect answers (off-topic, small talk) suggest offices but never present one as "Go to".
    suggest_only=mode in {'out_of_scope','greeting','boundary'}
    db.add(ChatLog(id=answer_id,service_id=chosen[0].id if chosen and not suggest_only else None,mode=mode))
    if chosen and not suggest_only: db.add(UsageEvent(kind='chat',category_id=chosen[0].category_id))
    save(db)
    return result|{'answer_id':answer_id,'recommendations':[service_json(s,db)|{'reason':reason,'role':'recommended' if i==0 and not suggest_only else 'alternative'} for i,(s,reason) in enumerate(zip(chosen,reasons))]}
@app.post('/api/chat/{answer_id}/feedback')
def feedback(answer_id: str,body: Feedback,db: DB,user: USER):
    entry=db.get(ChatLog,answer_id)
    if not entry: raise HTTPException(404,'Answer not found or retention period ended')
    if entry.helpful is not None: raise HTTPException(409,'This answer has already been rated')
    entry.helpful=body.helpful;save(db);return {'recorded':True}

@app.get('/api/admin/services')
def admin_services(db: DB,user: ADMIN): return [service_json(s,db) for s in db.scalars(select(Service).order_by(Service.name))]
def assign_service(s,body,db):
    if not db.get(Category,body.category_id): raise HTTPException(422,'Select an existing category')
    for key,value in body.model_dump().items(): setattr(s,key,value)
    s.updated_at=now();ai.embed(s)
@app.post('/api/admin/services',status_code=201)
def create_service(body: ServiceInput,db: DB,user: ADMIN):
    s=Service();assign_service(s,body,db);db.add(s);db.flush()
    from .knowledge import sync_directory
    sync_directory(db,s);save(db);return service_json(s,db)
@app.put('/api/admin/services/{sid}')
def edit_service(sid: int,body: ServiceInput,db: DB,user: ADMIN):
    s=db.get(Service,sid)
    if not s: raise HTTPException(404,'Service not found')
    assign_service(s,body,db)
    from .knowledge import sync_directory
    sync_directory(db,s);save(db);return service_json(s,db)
@app.patch('/api/admin/services/{sid}/active')
def archive(sid: int,body: ActiveInput,db: DB,user: ADMIN):
    s=db.get(Service,sid)
    if not s: raise HTTPException(404,'Service not found')
    s.active=body.active;s.updated_at=now();save(db);return service_json(s,db)
@app.post('/api/admin/categories',status_code=201)
def create_category(body: CategoryInput,db: DB,user: ADMIN):
    c=Category(name=body.name);db.add(c);save(db);return {'id':c.id,'name':c.name}
@app.put('/api/admin/categories/{cid}')
def edit_category(cid: int,body: CategoryInput,db: DB,user: ADMIN):
    c=db.get(Category,cid)
    if not c: raise HTTPException(404,'Category not found')
    c.name=body.name;save(db);return {'id':c.id,'name':c.name}
@app.delete('/api/admin/categories/{cid}')
def delete_category(cid: int,db: DB,user: ADMIN):
    if db.scalar(select(Service.id).where(Service.category_id==cid)): raise HTTPException(409,'Reassign services before deleting their category')
    c=db.get(Category,cid)
    if not c: raise HTTPException(404,'Category not found')
    if db.scalar(select(UsageEvent.id).where(UsageEvent.category_id==cid)): raise HTTPException(409,'Category still referenced by retained analytics')
    db.delete(c);save(db);return {'deleted':True}
@app.get('/api/admin/notices')
def admin_notices(db: DB,user: ADMIN):
    return [{k:getattr(n,k) for k in ['id','service_id','title','body','starts_at','ends_at']} for n in db.scalars(select(Notice).order_by(Notice.starts_at.desc()))]
@app.post('/api/admin/notices',status_code=201)
def create_notice(body: NoticeInput,db: DB,user: ADMIN):
    active_service(db,body.service_id);n=Notice(**body.model_dump());db.add(n);save(db);return {'id':n.id}
@app.put('/api/admin/notices/{nid}')
def edit_notice(nid: int,body: NoticeInput,db: DB,user: ADMIN):
    n=db.get(Notice,nid)
    if not n: raise HTTPException(404,'Notice not found')
    active_service(db,body.service_id)
    for k,v in body.model_dump().items(): setattr(n,k,v)
    save(db);return {'id':n.id}
@app.delete('/api/admin/notices/{nid}')
def delete_notice(nid: int,db: DB,user: ADMIN):
    n=db.get(Notice,nid)
    if not n: raise HTTPException(404,'Notice not found')
    db.delete(n);save(db);return {'deleted':True}
@app.get('/api/admin/analytics')
def analytics(db: DB,user: ADMIN,start: datetime | None=None,end: datetime | None=None):
    start=start or now()-timedelta(days=30);end=end or now()
    if start.tzinfo is None or end.tzinfo is None or end<=start: raise HTTPException(422,'Provide a valid timezone-aware date range')
    rows=list(db.scalars(select(UsageEvent).where(UsageEvent.created_at>=start,UsageEvent.created_at<=end)))
    def count(kind,key,label):
        totals=defaultdict(int)
        for r in rows:
            if r.kind==kind and getattr(r,key) is not None: totals[getattr(r,key)]+=1
        return [{'label':label(k),'count':v} for k,v in sorted(totals.items(),key=lambda v:(-v[1],str(v[0])))[:10]]
    ratings=list(db.scalars(select(ChatLog.helpful).where(ChatLog.created_at>=start,ChatLog.created_at<=end,ChatLog.helpful.is_not(None))))
    days=defaultdict(lambda:{'searches':0,'views':0,'chats':0})
    for r in rows:
        key={'search':'searches','view':'views','chat':'chats'}.get(r.kind)
        if key: days[r.created_at.date().isoformat()][key]+=1
    totals={k:sum(1 for r in rows if r.kind==kind) for k,kind in [('searches','search'),('views','view'),('chats','chat')]}
    return {'start':start,'end':end,'totals':totals,'daily':[{'date':d}|v for d,v in sorted(days.items())],'searches':count('search','term',lambda x:x),'views':count('view','service_id',lambda x:db.get(Service,x).name),'chat_categories':count('chat','category_id',lambda x:db.get(Category,x).name),'feedback':{'total':len(ratings),'helpful':sum(ratings),'helpful_percent':round(100*sum(ratings)/len(ratings),1) if ratings else None}}
