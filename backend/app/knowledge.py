"""Persist reviewed passages separately from directory cards; no live URL fetching/SSRF."""
import json
from pathlib import Path
from pydantic import Field, field_validator
from sqlalchemy import select
from .db import KnowledgeChunk, Service
from .schemas import Input

class PassageInput(Input):
    key: str = Field(min_length=2,max_length=180)
    service_name: str = Field(min_length=2,max_length=160)
    title: str = Field(min_length=2,max_length=200)
    content: str = Field(min_length=10,max_length=5000)
    steps: list[str] = Field(default_factory=list,max_length=3)
    keywords: list[str] = Field(default_factory=list,max_length=30)
    source_url: str = Field(max_length=500)
    reviewed_at: str | None = None
    @field_validator('source_url')
    @classmethod
    def https(cls,v):
        from urllib.parse import urlparse
        u=urlparse(v)
        if u.scheme!='https' or not u.hostname or u.username or u.password: raise ValueError('Use a public HTTPS citation URL without credentials')
        return v
    @field_validator('reviewed_at')
    @classmethod
    def review_date(cls,v):
        if v:
            from datetime import date
            date.fromisoformat(v)
        return v

def import_passages(db,path):
    from .ai import embed_chunk
    rows=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(rows,list) or len(rows)>1000: raise ValueError('Expected at most 1000 passage objects')
    validated=[PassageInput.model_validate(row) for row in rows]
    # Validate every service first so a bad import cannot partially commit.
    services={s.name:s for s in db.scalars(select(Service))}
    if any(row.service_name not in services for row in validated): raise ValueError('Every service_name must match an existing directory service')
    for row in validated:
        data=row.model_dump();service=services[data.pop('service_name')]
        chunk=db.scalar(select(KnowledgeChunk).where(KnowledgeChunk.key==row.key))
        if not chunk: chunk=KnowledgeChunk();db.add(chunk)
        for key,value in data.items(): setattr(chunk,key,value)
        chunk.service_id=service.id;embed_chunk(chunk)
    db.commit();return len(validated)

def seed_knowledge(db):
    from .ai import embed_chunk
    for s in db.scalars(select(Service)):
        key=f'directory-{s.id}'
        if db.scalar(select(KnowledgeChunk.id).where(KnowledgeChunk.key==key)): continue
        c=KnowledgeChunk(key=key,service_id=s.id,title=s.name+' — directory overview',content=s.description,steps=s.next_steps,keywords=s.tags,source_url=s.source_url,reviewed_at=s.updated_at.date().isoformat() if s.verified and s.updated_at else None)
        embed_chunk(c);db.add(c)
    db.commit()
    # Preserve imported/edited reviewed content; built-in passages are inserted only once.
    path=Path(__file__).with_name('knowledge_seed.json')
    rows=json.loads(path.read_text(encoding='utf-8'))
    missing=[r for r in rows if not db.scalar(select(KnowledgeChunk.id).where(KnowledgeChunk.key==r['key']))]
    if missing:
        from .ai import embed_chunk
        services={s.name:s for s in db.scalars(select(Service))}
        for raw in missing:
            data=PassageInput.model_validate(raw).model_dump();s=services[data.pop('service_name')]
            c=KnowledgeChunk(**data,service_id=s.id);embed_chunk(c);db.add(c)
        db.commit()

def sync_directory(db,service):
    from .ai import embed_chunk
    c=db.scalar(select(KnowledgeChunk).where(KnowledgeChunk.key==f'directory-{service.id}'))
    if not c: c=KnowledgeChunk(key=f'directory-{service.id}',service_id=service.id);db.add(c)
    c.title=service.name+' — directory overview';c.content=service.description;c.steps=service.next_steps
    c.keywords=service.tags;c.source_url=service.source_url
    # A directory card counts as reviewed only when an administrator marked its official source verified.
    c.reviewed_at=service.updated_at.date().isoformat() if service.verified and service.updated_at else None
    embed_chunk(c)
