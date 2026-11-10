"""Run the review-required routing dataset (100 questions, or the 50-question holdout) against the real API.

Accuracy (top-1 / top-3) is scored over hosted answers (mode "rag") only; fallback, safety and error answers are
counted separately. --sample N picks N questions spread evenly over the set, so a free-tier key (50 requests/day)
can still be evaluated. The run stops at the first HTTP 429 or 402, from the API or (with --server-log) from the
provider, and saves what finished.
"""
import argparse
import json
import os
from pathlib import Path
import re
import time
import httpx
parser=argparse.ArgumentParser()
parser.add_argument('--api',default='http://127.0.0.1:8000')
parser.add_argument('--dataset',default=str(Path(__file__).parents[1]/'docs'/'ai-evaluation-100.json'))
parser.add_argument('--output',default='ai-evaluation-results.json')
parser.add_argument('--require-rag',action='store_true',help='Fail if any answer uses offline/fallback instead of hosted RAG')
parser.add_argument('--sample',type=int,default=0,help='Evaluate N questions spread evenly over the set (0 = all)')
parser.add_argument('--server-log',help="API stderr log; stop when it reports a provider 429 or 402")
parser.add_argument('--label',default='',help='Free-text label stored in the results file (e.g. offline, hosted sample)')
args=parser.parse_args()
token=os.getenv('MAVASSIST_TOKEN','')
if not token: parser.error('Set MAVASSIST_TOKEN to a student bearer token. Do not put it in source control.')
dataset=json.loads(Path(args.dataset).read_text(encoding='utf-8'));results=[];known_names=set()
cases=dataset['cases']
if 0<args.sample<len(cases): cases=[cases[round(i*len(cases)/args.sample)] for i in range(args.sample)]  # deterministic spread
QUOTA=re.compile(r'Hosted AI request failed \((429|402)\)')
log_offset=Path(args.server_log).stat().st_size if args.server_log and Path(args.server_log).exists() else 0
def provider_quota_status():
    """Return '429'/'402' if the API log gained a provider quota failure since the last check."""
    global log_offset
    if not args.server_log or not Path(args.server_log).exists(): return None
    with open(args.server_log,'rb') as f: f.seek(log_offset);new=f.read();log_offset+=len(new)
    m=QUOTA.search(new.decode('utf-8','replace'));return m.group(1) if m else None
stop_reason=None
with httpx.Client(base_url=args.api,headers={'Authorization':'Bearer '+token},timeout=60) as client:
    offset=0
    while True:
        response=client.get('/api/services',params={'limit':100,'offset':offset});response.raise_for_status();catalog=response.json()
        known_names.update(s['name'] for s in catalog['items']);offset+=len(catalog['items'])
        if offset>=catalog['total'] or not catalog['items']: break
    for n,case in enumerate(cases):
        if n and os.getenv('EVAL_NO_DELAY')!='true': time.sleep(3.2) # 20 requests/min (free tier and the demo's chat rate limit)
        start=time.monotonic()
        try:
            response=client.post('/api/chat',json={'text':case['question']})
            if response.status_code in (429,402): stop_reason=f'API HTTP {response.status_code} at {case["id"]}';break
            response.raise_for_status();data=response.json()
            names=[s['name'] for s in data['recommendations']]
            results.append({'case_id':case['id'],'expected':case['expected_service'],'returned':names,'top1':bool(names and names[0]==case['expected_service']),'top3':case['expected_service'] in names[:3],'mode':data['mode'],'latency_ms':round((time.monotonic()-start)*1000)})
        except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
            # One bad request must not stop the run: record it as a wrong answer (never as hosted RAG).
            results.append({'case_id':case['id'],'expected':case['expected_service'],'returned':[],'top1':False,'top3':False,'mode':'error','error':type(exc).__name__,'latency_ms':round((time.monotonic()-start)*1000)})
        if results[-1]['mode']!='rag':
            status=provider_quota_status()
            if status: results[-1]['provider_status']=int(status);stop_reason=f'provider HTTP {status} at {case["id"]}';break
hosted=[r for r in results if r['mode']=='rag']
count=lambda mode:sum(r['mode']==mode for r in results)
rate=lambda rows,key:(sum(r[key] for r in rows)/len(rows)) if rows else None
summary={'label':args.label,'dataset_status':dataset['status'],'cases_planned':len(cases),'cases':len(results),'sampled':0<args.sample<len(dataset['cases']),
  'stopped_early':stop_reason is not None,'stop_reason':stop_reason,
  'hosted_answers':len(hosted),'fallback_answers':count('fallback'),'grounded_answers':count('grounded'),'safety_answers':count('safety'),'errors':count('error'),
  'top1_accuracy':rate(hosted,'top1'),'top3_accuracy':rate(hosted,'top3'),  # hosted (mode rag) answers only
  'all_answers_top1_accuracy':rate(results,'top1'),'all_answers_top3_accuracy':rate(results,'top3'),
  'unknown_offices':sum(n not in known_names for r in results for n in r['returned']),
  'all_hosted_rag':bool(results) and len(hosted)==len(results),'results':results}
Path(args.output).write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='results'},indent=2))
if args.require_rag and (not summary['all_hosted_rag'] or stop_reason or (summary['top1_accuracy'] or 0)<.8 or (summary['top3_accuracy'] or 0)<.95 or summary['unknown_offices']): raise SystemExit(1)
