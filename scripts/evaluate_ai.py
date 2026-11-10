"""Run the 100-case review-required routing dataset against the real API."""
import argparse
import json
import os
from pathlib import Path
import time
import httpx
parser=argparse.ArgumentParser()
parser.add_argument('--api',default='http://127.0.0.1:8000')
parser.add_argument('--dataset',default=str(Path(__file__).parents[1]/'docs'/'ai-evaluation-100.json'))
parser.add_argument('--output',default='ai-evaluation-results.json')
parser.add_argument('--require-rag',action='store_true',help='Fail if any answer uses offline/fallback instead of hosted RAG')
args=parser.parse_args()
token=os.getenv('MAVASSIST_TOKEN','')
if not token: parser.error('Set MAVASSIST_TOKEN to a student bearer token. Do not put it in source control.')
dataset=json.loads(Path(args.dataset).read_text(encoding='utf-8'));results=[];known_names=set()
with httpx.Client(base_url=args.api,headers={'Authorization':'Bearer '+token},timeout=60) as client:
    offset=0
    while True:
        response=client.get('/api/services',params={'limit':100,'offset':offset});response.raise_for_status();catalog=response.json()
        known_names.update(s['name'] for s in catalog['items']);offset+=len(catalog['items'])
        if offset>=catalog['total'] or not catalog['items']: break
    for case in dataset['cases']:
        start=time.monotonic()
        try:
            response=client.post('/api/chat',json={'text':case['question']});response.raise_for_status();data=response.json()
            names=[s['name'] for s in data['recommendations']]
            results.append({'case_id':case['id'],'expected':case['expected_service'],'returned':names,'top1':bool(names and names[0]==case['expected_service']),'top3':case['expected_service'] in names[:3],'mode':data['mode'],'latency_ms':round((time.monotonic()-start)*1000)})
        except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
            # One bad request must not stop the run: record it as a wrong answer (never as hosted RAG).
            results.append({'case_id':case['id'],'expected':case['expected_service'],'returned':[],'top1':False,'top3':False,'mode':'error','error':type(exc).__name__,'latency_ms':round((time.monotonic()-start)*1000)})
        if os.getenv('EVAL_NO_DELAY')!='true': time.sleep(3.2) # Respect the demo's chat rate limit.
summary={'dataset_status':dataset['status'],'cases':len(results),'top1_accuracy':sum(r['top1'] for r in results)/len(results),'top3_accuracy':sum(r['top3'] for r in results)/len(results),'unknown_offices':sum(n not in known_names for r in results for n in r['returned']),'all_hosted_rag':all(r['mode']=='rag' for r in results),'errors':sum(r['mode']=='error' for r in results),'results':results}
Path(args.output).write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='results'},indent=2))
if args.require_rag and (not summary['all_hosted_rag'] or summary['top1_accuracy']<.8 or summary['top3_accuracy']<.95 or summary['unknown_offices']): raise SystemExit(1)
