import {FormEvent, useEffect, useRef, useState} from 'react';
import {ExternalLink, Send, ShieldCheck, ThumbsDown, ThumbsUp} from 'lucide-react';
import {Answer, api, dateLabel, json} from '../api';
import {Citations, ContactLines, ErrorBox, iconProps} from '../ui';

const EXAMPLES=[
  'I paid extra tuition. How do I get a refund?',
  'I need a travel signature on my I-20',
  'I’m failing calculus and need help',
  'I lost my student ID card',
  'I feel really stressed and anxious',
  'How do I buy a parking permit?',
];
const MODE_LABEL:Record<string,string>={rag:'AI answer with sources',grounded:'Answer from official sources',fallback:'Answer from official sources (AI unavailable)',clarification:'Needs a detail'};

export default function Assistant({onOpen}:{onOpen:(id:number)=>void}){
  const [question,setQuestion]=useState(''),[answers,setAnswers]=useState<Answer[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const latest=useRef<HTMLElement>(null);
  useEffect(()=>{latest.current?.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});},[answers.length]);

  async function ask(e?:FormEvent,preset?:string){
    e?.preventDefault();const q=(preset??question).trim();if(!q||busy)return;setBusy(true);setError('');
    // Only the last three turns travel with a follow-up; nothing is stored server-side.
    const history=answers.slice(-3).map(a=>({question:a.question,answer:[a.message,...(a.answer||[]).map(p=>p.text)].join(' ').slice(0,4000)}));
    try{const answer=await api<Omit<Answer,'question'>>('/api/chat',json('POST',{text:q,history}));setAnswers(a=>[...a,{...answer,question:q}]);setQuestion('');}
    catch(err){setError((err as Error).message);}
    finally{setBusy(false);}
  }
  async function rate(a:Answer,helpful:boolean){
    try{await api('/api/chat/'+a.answer_id+'/feedback',json('POST',{helpful}));setAnswers(all=>all.map(x=>x.answer_id===a.answer_id?{...x,rated:true}:x));}
    catch(err){setError((err as Error).message);}
  }

  return <>
    <section className="page-head" aria-labelledby="page-title"><div className="container">
      <h1 id="page-title">What do you need help with?</h1>
      <p className="muted">Ask in your own words. You’ll get the office to go to, why, and the steps to take, with links to the official UTA pages.</p>
    </div></section>
    <div className="container assistant">
      <div className="chat-column">
        {answers.length===0&&<div className="chat-empty">
          <h2>Start with one of these, or type your own.</h2>
          <div className="examples">{EXAMPLES.map(q=><button key={q} className="example" onClick={()=>ask(undefined,q)}>{q}</button>)}</div>
        </div>}
        <div className="conversation" aria-live="polite">{answers.map((a,i)=><article key={a.answer_id} ref={i===answers.length-1?latest:undefined}>
          <p className="question-bubble"><span className="sr-only">You asked: </span>{a.question}</p>
          <AnswerCard answer={a} onOpen={onOpen} onPick={name=>ask(undefined,name)} onRate={v=>rate(a,v)}/>
        </article>)}</div>
        {busy&&<p className="thinking" role="status"><span/>Finding the right office…</p>}
        <ErrorBox text={error}/>
        <form className="composer" onSubmit={ask}>
          <label className="sr-only" htmlFor="question">Your campus question</label>
          <textarea id="question" rows={1} value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void ask();}}}
            placeholder={answers.length?'Ask a follow-up or a new question…':'Describe what you need…'} minLength={3} maxLength={1000} required/>
          <button className="btn btn-primary" disabled={busy}><Send size={17} aria-hidden="true"/>Send question</button>
        </form>
      </div>
      <aside className="chat-aside">
        <section className="aside-block privacy">
          <h2><ShieldCheck {...iconProps}/>Before you ask</h2>
          <p>Leave out your name, student ID, health details and anything else personal. MavAssist explains published guidance; it can’t see your account or approve a request. Questions aren’t stored.</p>
        </section>
        <section className="aside-block">
          <h2>How answers are built</h2>
          <ol className="how">
            <li>Your question is matched against 50 curated UTA offices.</li>
            <li>The answer uses only that office’s official guidance, with numbered sources.</li>
            <li>If nothing matches confidently, MavAssist asks you for a detail instead of guessing.</li>
          </ol>
        </section>
      </aside>
    </div>
  </>;
}

function AnswerCard({answer:a,onOpen,onPick,onRate}:{answer:Answer;onOpen:(id:number)=>void;onPick:(q:string)=>void;onRate:(v:boolean)=>void}){
  const [main,...alternatives]=a.recommendations;
  return <div className="answer">
    <div className="answer-head"><strong>MavAssist</strong><span className={'mode mode-'+a.mode}>{MODE_LABEL[a.mode]||'Answer'}</span></div>
    {a.mode==='clarification'?<>
      <p className="answer-intro">{a.message}</p>
      {!!a.options?.length&&<div className="examples">{a.options.map(o=><button key={o} className="example" onClick={()=>onPick(o)}>{o}</button>)}</div>}
    </>:<>
      {main&&<section className="slip" aria-label="Recommended office">
        <p className="slip-label">Go to</p>
        <h3><button className="slip-name" onClick={()=>onOpen(main.id)}>{main.name}</button></h3>
        <p className="slip-reason">{main.reason}</p>
        <dl className="slip-facts">
          <div><dt>Where</dt><dd>{main.location}</dd></div>
          <div><dt>When</dt><dd>{main.hours}</dd></div>
          <div><dt>Contact</dt><dd><ContactLines value={main.contact}/></dd></div>
          <div><dt>Last updated</dt><dd>{dateLabel(main.updated_at)}</dd></div>
        </dl>
      </section>}
      {(a.answer||[]).map((p,i)=><p className="answer-paragraph" key={i}>{p.text}<Citations ids={p.source_ids} sources={a.sources||[]}/></p>)}
      {!!a.steps?.length&&<><h3 className="answer-sub">What to do next</h3><ol className="route-steps">{a.steps.map((p,i)=><li key={i}>{p.text}<Citations ids={p.source_ids} sources={a.sources||[]}/></li>)}</ol></>}
      {alternatives.length>0&&<div className="alternatives"><h3 className="answer-sub">Also worth a look</h3><ul>{alternatives.map(s=><li key={s.id}>
        <button className="link-button" onClick={()=>onOpen(s.id)}>{s.name}</button><span>{s.reason}</span>
      </li>)}</ul></div>}
      {!!a.sources?.length&&<div className="sources"><h3 className="answer-sub">Sources</h3><ol>{a.sources.map(src=><li key={src.id}>
        <a href={src.url} target="_blank" rel="noopener noreferrer">{src.title}<ExternalLink size={12} aria-hidden="true"/></a>
        <small>{src.reviewed_at?'Checked '+dateLabel(src.reviewed_at+'T12:00:00'):'Not yet verified by an administrator'}</small>
      </li>)}</ol></div>}
    </>}
    <div className="feedback"><span>{a.rated?'Thanks for your feedback.':'Was this helpful?'}</span>
      <button className="icon-btn" aria-label="Helpful answer" disabled={a.rated} onClick={()=>onRate(true)}><ThumbsUp size={16} aria-hidden="true"/></button>
      <button className="icon-btn" aria-label="Not helpful answer" disabled={a.rated} onClick={()=>onRate(false)}><ThumbsDown size={16} aria-hidden="true"/></button>
    </div>
  </div>;
}
