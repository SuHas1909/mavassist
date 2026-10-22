import argparse
import getpass
import bcrypt
from sqlalchemy import select
from .db import KnowledgeChunk, SessionLocal, Service, User
from .seed import seed
from .schemas import Register
from .ai import embed, embed_chunk, MODE

def main():
    parser=argparse.ArgumentParser(description='MavAssist maintenance; run from backend directory.')
    parser.add_argument('command',choices=['seed','create-admin','reindex','prune','import-knowledge'])
    parser.add_argument('--email');parser.add_argument('--name')
    parser.add_argument('--file',help='Reviewed JSON passages for import-knowledge')
    args=parser.parse_args()
    with SessionLocal() as db:
        if args.command=='seed': print('Services added:',seed(db))
        elif args.command=='import-knowledge':
            if not args.file: parser.error('Specify --file with a reviewed JSON passage file')
            from .knowledge import import_passages
            print('Knowledge passages imported:',import_passages(db,args.file))
        elif args.command=='create-admin':
            password=getpass.getpass('New admin password (10+ characters): ')
            if password!=getpass.getpass('Confirm password: '): parser.error('Passwords do not match')
            data=Register(name=args.name or input('Full name: '),email=args.email or input('Email: '),password=password)
            if db.scalar(select(User.id).where(User.email==data.email)): parser.error('Email exists. Use a new email; this command never promotes student accounts.')
            db.add(User(name=data.name,email=data.email,password_hash=bcrypt.hashpw(data.password.encode(),bcrypt.gensalt(12)).decode(),role='administrator'));db.commit();print('Administrator created.')
        elif args.command=='reindex':
            if MODE!='rag': parser.error('Set AI_MODE=rag and install requirements-ai.txt first')
            for s in db.scalars(select(Service)): embed(s)
            for c in db.scalars(select(KnowledgeChunk)): embed_chunk(c)
            db.commit();print('Embeddings refreshed.')
        else:
            from .main import prune
            prune(db);print('Expired anonymous chat/usage records deleted.')
if __name__=='__main__': main()
