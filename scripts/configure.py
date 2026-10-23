"""Generate local environment files without fixed credentials. Never overwrites an existing value.

Run:  python scripts/configure.py
It asks (hidden input) for an optional OpenRouter API key and stores it only in backend/.env,
which is git-ignored. Press Enter to skip and use offline source-based answers.
"""
from pathlib import Path
import getpass
import secrets
import sys

root=Path(__file__).resolve().parents[1]
target=root/'backend'/'.env'

def ask_key():
    if not sys.stdin.isatty(): return ''
    try: return getpass.getpass('OpenRouter API key (sk-or-..., input hidden; Enter to skip): ').strip()
    except (EOFError,KeyboardInterrupt): return ''

if target.exists():
    text=target.read_text(encoding='utf-8')
    if 'OPENROUTER_API_KEY=' not in text or 'OPENROUTER_API_KEY=\n' in text:
        key=ask_key()
        if key:
            text=text.replace('OPENROUTER_API_KEY=\n','')
            text=text.rstrip('\n')+f'\nOPENROUTER_API_KEY={key}\nOPENROUTER_MODEL=openai/gpt-4o-mini\nLLM_TIMEOUT=12\n'
            target.write_text(text,encoding='utf-8');print('Added OpenRouter settings to backend/.env.')
        else: print('backend/.env already exists; left unchanged.')
    else: print('backend/.env already has an OpenRouter key; left unchanged.')
else:
    key=ask_key()
    target.write_text('APP_ENV=development\nDATABASE_URL=sqlite:///./mavassist.db\nJWT_SECRET='+secrets.token_urlsafe(48)+
        '\nCORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\nAI_MODE=keyword\n'
        f'OPENROUTER_API_KEY={key}\nOPENROUTER_MODEL=openai/gpt-4o-mini\nLLM_TIMEOUT=12\n'
        'OPENAI_API_KEY=\nOPENAI_MODEL=\nSIMILARITY_THRESHOLD=0.28\nRATE_LIMIT=true\n',encoding='utf-8')
    print('Created backend/.env with a unique JWT secret'+(' and your OpenRouter key.' if key else ' (no AI key: offline source-based answers).'))
compose=root/'.env'
if not compose.exists():
    compose.write_text('POSTGRES_PASSWORD='+secrets.token_urlsafe(30)+'\nJWT_SECRET='+secrets.token_urlsafe(48)+'\nINSTALL_AI=true\nAI_MODE=rag\nOPENROUTER_API_KEY=\nOPENROUTER_MODEL=openai/gpt-4o-mini\nOPENAI_API_KEY=\nOPENAI_MODEL=\n',encoding='utf-8')
    print('Created root .env for Docker Compose. Add OPENROUTER_API_KEY there to enable AI answers in Docker.')
