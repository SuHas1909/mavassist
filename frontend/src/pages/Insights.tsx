import {FormEvent, useEffect, useMemo, useState} from 'react';
import {api} from '../api';
import {ErrorBox, Field} from '../ui';

type Row={label:string;count:number};
type Day={date:string;searches:number;views:number;chats:number};
type Data={totals:{searches:number;views:number;chats:number};daily:Day[];searches:Row[];views:Row[];chat_categories:Row[];feedback:{total:number;helpful:number;helpful_percent:number|null}};
// Validated categorical palette (light surface): UTA blue, darkened UTA orange, green.
const SERIES:{key:keyof Omit<Day,'date'>;label:string;color:string}[]=[
  {key:'searches',label:'Searches',color:'#0064B1'},{key:'views',label:'Office views',color:'#E0701B'},{key:'chats',label:'Assistant questions',color:'#2E8B6A'}];
const iso=(d:Date)=>d.toISOString().slice(0,10);

export default function Insights(){
  const [data,setData]=useState<Data|null>(null),[error,setError]=useState(''),[range,setRange]=useState(()=>{const e=new Date(),s=new Date(Date.now()-29*864e5);return {start:iso(s),end:iso(e)};});
  async function load(start:string,end:string){
    setError('');
    try{setData(await api<Data>('/api/admin/analytics?'+new URLSearchParams({start:new Date(start+'T00:00:00').toISOString(),end:new Date(end+'T23:59:59').toISOString()})));}
    catch(err){setError((err as Error).message);}
  }
  useEffect(()=>{void load(range.start,range.end);},[]);
  function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);const r={start:String(f.get('start')),end:String(f.get('end'))};setRange(r);void load(r.start,r.end);}

  return <>
    <section className="page-head" aria-labelledby="page-title"><div className="container">
      <h1 id="page-title">Usage insights</h1>
      <p className="muted">What students look for, counted anonymously. No profiles and no stored questions.</p>
      <form className="range-form" onSubmit={submit}>
        <Field label="From date"><input name="start" type="date" defaultValue={range.start} required/></Field>
        <Field label="To date"><input name="end" type="date" defaultValue={range.end} required/></Field>
        <button className="btn btn-primary">Apply date range</button>
      </form>
    </div></section>
    <div className="container insights">
      <ErrorBox text={error}/>
      {data&&<>
        <dl className="kpis">
          <div className="kpi"><dt>Directory searches</dt><dd>{data.totals.searches}</dd></div>
          <div className="kpi"><dt>Office views</dt><dd>{data.totals.views}</dd></div>
          <div className="kpi"><dt>Assistant questions</dt><dd>{data.totals.chats}</dd></div>
          <div className="kpi"><dt>Rated helpful</dt><dd>{data.feedback.helpful_percent===null?'–':data.feedback.helpful_percent+'%'}<small>{data.feedback.total} {data.feedback.total===1?'rating':'ratings'}</small></dd></div>
        </dl>
        <section className="panel"><h2>Daily activity</h2><ActivityChart days={fillDays(data.daily,range.start,range.end)}/></section>
        <div className="insight-grid">
          <RankedBars title="Most searched terms" rows={data.searches}/>
          <RankedBars title="Most viewed offices" rows={data.views}/>
          <RankedBars title="What students ask the assistant about" rows={data.chat_categories}/>
        </div>
      </>}
    </div>
  </>;
}

function fillDays(days:Day[],start:string,end:string):Day[]{
  const map=new Map(days.map(d=>[d.date,d]));const out:Day[]=[];
  for(let t=new Date(start+'T00:00:00Z').getTime();t<=new Date(end+'T00:00:00Z').getTime()&&out.length<120;t+=864e5){const k=iso(new Date(t));out.push(map.get(k)||{date:k,searches:0,views:0,chats:0});}
  return out;
}

function ActivityChart({days}:{days:Day[]}){
  const [hover,setHover]=useState<number|null>(null),[table,setTable]=useState(false);
  const max=Math.max(1,...days.flatMap(d=>SERIES.map(s=>d[s.key])));
  const step=niceStep(max),top=Math.ceil(max/step)*step;
  const W=760,H=240,L=14+8*top.toLocaleString().length,R=150,T=12,B=28;
  const x=(i:number)=>L+(days.length<2?0:i*(W-L-R)/(days.length-1)),y=(v:number)=>T+(H-T-B)*(1-v/top);
  const ticks=useMemo(()=>{const t=[];for(let v=0;v<=top;v+=step)t.push(v);return t;},[top,step]);
  const label=(d:string)=>new Date(d+'T12:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric'});
  const every=Math.ceil(days.length/6);
  // Direct end labels, nudged apart so they never collide.
  const endY=useMemo(()=>{const order=SERIES.map((s,i)=>({i,v:y(days[days.length-1][s.key])})).sort((a,b)=>a.v-b.v);const out:number[]=[];let last=-Infinity;
    for(const o of order){const v=Math.max(o.v,last+15);out[o.i]=v;last=v;}return out;},[days,top]);
  return <div className="chart">
    <div className="chart-legend">{SERIES.map(s=><span key={s.key}><i style={{background:s.color}}/>{s.label}</span>)}
      <button className="link-button" onClick={()=>setTable(!table)} aria-pressed={table}>{table?'Show chart':'Show as table'}</button></div>
    {table?<div className="table-wrap"><table><caption className="sr-only">Daily activity</caption><thead><tr><th scope="col">Date</th>{SERIES.map(s=><th scope="col" key={s.key}>{s.label}</th>)}</tr></thead>
      <tbody>{days.filter(d=>d.searches+d.views+d.chats>0).map(d=><tr key={d.date}><td>{label(d.date)}</td>{SERIES.map(s=><td key={s.key}>{d[s.key]}</td>)}</tr>)}</tbody></table></div>
    :<div className="chart-plot" onMouseLeave={()=>setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Daily searches, office views and assistant questions from ${label(days[0].date)} to ${label(days[days.length-1].date)}`}
        onMouseMove={e=>{const r=e.currentTarget.getBoundingClientRect();const px=(e.clientX-r.left)*W/r.width;const i=Math.round((px-L)/((W-L-R)/Math.max(1,days.length-1)));setHover(Math.max(0,Math.min(days.length-1,i)));}}>
        {ticks.map(v=><g key={v}><line x1={L} x2={W-R} y1={y(v)} y2={y(v)} className="grid"/><text x={L-8} y={y(v)+4} className="axis" textAnchor="end">{v.toLocaleString()}</text></g>)}
        {days.map((d,i)=>i%every===0&&<text key={d.date} x={x(i)} y={H-8} className="axis" textAnchor="middle">{label(d.date)}</text>)}
        {hover!==null&&<line x1={x(hover)} x2={x(hover)} y1={T} y2={H-B} className="crosshair"/>}
        {SERIES.map((s,si)=><g key={s.key}>
          <polyline fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" points={days.map((d,i)=>`${x(i)},${y(d[s.key])}`).join(' ')}/>
          <text x={W-R+8} y={endY[si]+4} className="end-label" fill="currentColor">{s.label}</text>
          {hover!==null&&<circle cx={x(hover)} cy={y(days[hover][s.key])} r={4.5} fill={s.color} stroke="#fff" strokeWidth={2}/>}
        </g>)}
      </svg>
      {hover!==null&&<div className="tooltip" style={{left:`${(x(hover)/W)*100}%`}} role="status">
        <strong>{label(days[hover].date)}</strong>{SERIES.map(s=><span key={s.key}><i style={{background:s.color}}/>{s.label}<b>{days[hover][s.key]}</b></span>)}
      </div>}
    </div>}
  </div>;
}
function niceStep(max:number){const raw=max/4;const p=10**Math.floor(Math.log10(raw||1));return [1,2,5,10].map(m=>m*p).find(s=>s>=raw)||p*10;}

function RankedBars({title,rows}:{title:string;rows:Row[]}){
  const max=Math.max(1,...rows.map(r=>r.count));
  return <section className="panel ranked"><h2>{title}</h2>
    {rows.length===0?<p className="muted">No activity in this date range.</p>:<ol>{rows.map(r=><li key={r.label} title={`${r.label}: ${r.count}`}>
      <span className="ranked-label">{r.label}</span>
      <span className="ranked-track" aria-hidden="true"><span className="ranked-bar" style={{width:`${(r.count/max)*100}%`}}/></span>
      <span className="ranked-value">{r.count}</span>
    </li>)}</ol>}
  </section>;
}
