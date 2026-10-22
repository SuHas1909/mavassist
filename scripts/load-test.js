import http from 'k6/http';
import {check,sleep} from 'k6';
import {Trend} from 'k6/metrics';
const apiLatency=new Trend('non_ai_latency');
const aiLatency=new Trend('chat_latency');
const fallbackLatency=new Trend('fallback_latency');
const thresholds={non_ai_latency:['p(95)<1000'],chat_latency:['p(95)<5000'],checks:['rate==1'],http_req_failed:['rate<0.01']};
if(__ENV.EXPECT_FALLBACK==='true')thresholds.fallback_latency=['p(95)<3000'];
export const options={vus:__ENV.VUS?Number(__ENV.VUS):50,duration:__ENV.DURATION||"60s",thresholds};
export default function(){
  const base=__ENV.API_URL||'http://localhost:8000';
  const headers={Authorization:`Bearer ${__ENV.MAVASSIST_TOKEN}`,'Content-Type':'application/json'};
  let r=http.get(base+'/api/services?q=tuition',{headers});apiLatency.add(r.timings.duration);check(r,{'directory 200':r=>r.status===200});
  r=http.post(base+'/api/chat',JSON.stringify({text:'I need help with tuition payment'}),{headers});aiLatency.add(r.timings.duration);check(r,{'chat 200':r=>r.status===200});
  if(r.status===200&&r.json('mode')==='fallback')fallbackLatency.add(r.timings.duration);
  if(__ENV.EXPECT_FALLBACK==='true')check(r,{'forced outage uses fallback':r=>r.status===200&&r.json('mode')==='fallback'});
  if(__ENV.EXPECT_RAG==='true')check(r,{'hosted AI succeeded':r=>r.status===200&&r.json('mode')==='rag'});
  sleep(1);
}
