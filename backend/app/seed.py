"""Idempotent directory seed built from services_seed.json (public UTA pages, see DATA_SOURCES.md)."""
import json
from pathlib import Path
from sqlalchemy import select
from .db import Category, Service, SessionLocal, now
from .ai import embed

DATA=json.loads(Path(__file__).with_name('services_seed.json').read_text(encoding='utf-8'))
# Placeholder text used by the first Sprint 1 seed. Rows still carrying it are upgraded in place;
# rows an administrator has edited are never overwritten.
PLACEHOLDER='Check the official resource page'
FIELDS=['description','location','hours','contact','source_url','tags','next_steps','verified']

def seed(db):
    from .knowledge import sync_directory
    added=0;changed=[]
    for category,entries in DATA['categories'].items():
        c=db.scalar(select(Category).where(Category.name==category))
        if not c: c=Category(name=category);db.add(c);db.flush()
        for row in entries:
            s=db.scalar(select(Service).where(Service.name==row['name']))
            if s and s.location!=PLACEHOLDER: continue
            if not s: s=Service(name=row['name'],category_id=c.id,active=True);db.add(s);added+=1
            for key in FIELDS: setattr(s,key,row[key])
            s.updated_at=now();embed(s);db.flush();changed.append(s)
    for s in changed: sync_directory(db,s)
    db.commit()
    from .knowledge import seed_knowledge
    seed_knowledge(db)
    return added
if __name__=='__main__':
    with SessionLocal() as db: print(f'Added {seed(db)} services.')
