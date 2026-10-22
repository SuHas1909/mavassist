import {useEffect, useMemo, useState} from 'react';
import {Bookmark, Check, Search, Sparkles} from 'lucide-react';
import {api, Category, Service} from '../api';
import {CategoryIcon, ErrorBox, iconProps} from '../ui';

export type ListMode='directory'|'bookmarks'|'recent';
const POPULAR=['tuition','visa','tutoring','parking','counseling','transcript'];
// Frequent first questions, each mapped to the office that answers it.
const FIRST_STOPS:[string,string][]=[
  ['Set up a tuition payment plan','Student Accounts'],['Get a travel signature on an I-20','International Student & Scholar Services'],
  ['Find free tutoring','Tutoring & Academic Success'],['Talk to a counselor','Counseling & Psychological Services'],
  ['Reset a NetID password','OIT Help Desk'],['Replace a lost Mav ID','Mav Express']];

type Props={mode:ListMode;categories:Category[];bookmarkIds:number[];onOpen:(id:number)=>void;onSave:(s:Service)=>void;onAsk:()=>void;onBrowse:()=>void};

export default function Directory({mode,categories,bookmarkIds,onOpen,onSave,onAsk,onBrowse}:Props){
  const [items,setItems]=useState<Service[]>([]),[all,setAll]=useState<Service[]>([]),[busy,setBusy]=useState(true),[error,setError]=useState('');
  const [query,setQuery]=useState(''),[searchQuery,setSearchQuery]=useState(''),[filters,setFilters]=useState<number[]>([]);

  // Full active list once, for category counts.
  useEffect(()=>{if(mode==='directory')api<{items:Service[]}>('/api/services?limit=100').then(r=>setAll(r.items)).catch(()=>{});},[mode]);

  useEffect(()=>{
    let cancelled=false;setBusy(true);setError('');
    const params=new URLSearchParams({q:searchQuery,limit:'100'});filters.forEach(x=>params.append('category_ids',String(x)));
    const request=mode==='directory'?api<{items:Service[]}>('/api/services?'+params).then(r=>r.items):api<Service[]>(mode==='bookmarks'?'/api/bookmarks':'/api/recent');
    request.then(x=>{if(!cancelled)setItems(x);}).catch(e=>{if(!cancelled)setError(e.message);}).finally(()=>{if(!cancelled)setBusy(false);});
    return ()=>{cancelled=true;};
  },[mode,searchQuery,filters,mode==='bookmarks'?bookmarkIds.length:0]);

  const counts=useMemo(()=>{const c:Record<number,number>={};all.forEach(s=>{c[s.category_id]=(c[s.category_id]||0)+1;});return c;},[all]);
  const filtered=!!searchQuery||filters.length>0;
  function reset(){setFilters([]);setQuery('');setSearchQuery('');}
  function runSearch(term:string){setQuery(term);setSearchQuery(term);}

  return <>
    {mode==='directory'?<section className="hero" aria-labelledby="page-title">
      <div className="hero-inner"><div className="hero-main">
        <h1 id="page-title">Find your next step.</h1>
        <p className="hero-lede">Search 50 UTA offices and services by what you need, not by office name.</p>
        <form className="hero-search" role="search" onSubmit={e=>{e.preventDefault();setSearchQuery(query.trim());}}>
          <Search size={22} aria-hidden="true"/>
          <label className="sr-only" htmlFor="search">Search campus services</label>
          <input id="search" placeholder="Try “payment plan”, “I-20”, or “free tutoring”" value={query} onChange={e=>setQuery(e.target.value)} maxLength={200}/>
          <button className="btn btn-orange">Search</button>
        </form>
        <div className="hero-popular"><span>Popular searches</span>{POPULAR.map(t=><button type="button" key={t} onClick={()=>runSearch(t)}>{t}</button>)}</div>
      </div>
      {all.length>0&&<aside className="first-stops" aria-labelledby="first-stops-title">
        <h2 id="first-stops-title">Common first stops</h2>
        <ul>{FIRST_STOPS.map(([task,name])=>{const s=all.find(x=>x.name===name);return s&&<li key={task}>
          <button onClick={()=>onOpen(s.id)}><span className="stop-task">{task}</span><span className="stop-office">{name}</span></button>
        </li>;})}</ul>
      </aside>}
      </div>
    </section>:<section className="page-head" aria-labelledby="page-title">
      <div className="container">
        <h1 id="page-title">{mode==='bookmarks'?'Saved resources':'Recently viewed'}</h1>
        <p className="muted">{mode==='bookmarks'?'The offices you saved, ready when you need them.':'Your last 10 opened services, newest first.'}</p>
      </div>
    </section>}

    <div className="container directory">
      {mode==='directory'&&<nav className="signs" aria-label="Filter by category">
        {categories.map(c=>{const on=filters.includes(c.id);return <button key={c.id} className={'sign'+(on?' sign-on':'')} aria-pressed={on} onClick={()=>setFilters(f=>on?f.filter(x=>x!==c.id):[...f,c.id])}>
          <span className="sign-icon"><CategoryIcon name={c.name}/></span>
          <span className="sign-name">{c.name}</span>
          <span className="sign-count">{on?<Check size={16} aria-label="Selected"/>:(counts[c.id]??'')}</span>
        </button>;})}
      </nav>}

      <ErrorBox text={error}/>
      <div className="results-bar">
        <h2>{mode==='directory'?(filtered?'Matching offices':'All offices and services'):mode==='bookmarks'?'Your saved offices':'Opened recently'}</h2>
        <span className="results-count" role="status">{busy?'Loading…':`${items.length} ${items.length===1?'result':'results'}${searchQuery?` for “${searchQuery}”`:''}`}</span>
        {mode==='directory'&&filtered&&<button className="link-button" onClick={reset}>Clear search and filters</button>}
      </div>

      {busy?<div className="skeleton-list" aria-hidden="true">{[0,1,2,3].map(i=><div key={i} className="skeleton-row"/>)}</div>
      :items.length?<ol className="office-list">{items.map(s=><OfficeRow key={s.id} service={s} saved={bookmarkIds.includes(s.id)} onOpen={()=>onOpen(s.id)} onSave={()=>onSave(s)}/>)}</ol>
      :<div className="empty">
        <h2>{mode==='bookmarks'?'Nothing saved yet.':mode==='recent'?'No recent offices yet.':'No offices match that search.'}</h2>
        <p>{mode==='bookmarks'?'Use the bookmark on any office to keep it here.':mode==='recent'?'Offices you open will show up here.':'Try a different word, or describe the problem to the assistant.'}</p>
        <div className="empty-actions">
          {mode==='directory'?<button className="btn btn-secondary" onClick={reset}>Clear search and filters</button>:<button className="btn btn-secondary" onClick={onBrowse}>Explore resources</button>}
          <button className="btn btn-primary" onClick={onAsk}><Sparkles {...iconProps}/>Ask MavAssist</button>
        </div>
      </div>}

      {mode==='directory'&&!busy&&<aside className="ask-strip">
        <div><h2>Not sure what the office is called?</h2><p>Describe the problem. The assistant routes you to the right office and explains the next steps.</p></div>
        <button className="btn btn-primary" onClick={onAsk}><Sparkles {...iconProps}/>Ask MavAssist</button>
      </aside>}
    </div>
  </>;
}

function OfficeRow({service:s,saved,onOpen,onSave}:{service:Service;saved:boolean;onOpen:()=>void;onSave:()=>void}){
  return <li className="office">
    <div className="office-cat"><CategoryIcon name={s.category} size={18}/><span>{s.category}</span></div>
    <div className="office-main">
      <h3><button className="office-name" onClick={onOpen}>{s.name}</button></h3>
      <p>{s.description}</p>
    </div>
    <dl className="office-facts">
      <div><dt>Where</dt><dd>{s.location}</dd></div>
      <div><dt>When</dt><dd>{s.hours}</dd></div>
    </dl>
    <button className={'icon-btn bookmark'+(saved?' is-saved':'')} aria-label={(saved?'Remove bookmark for ':'Bookmark ')+s.name} aria-pressed={saved} onClick={onSave}>
      <Bookmark size={19} aria-hidden="true" fill={saved?'currentColor':'none'}/>
    </button>
  </li>;
}
