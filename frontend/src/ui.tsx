import {cloneElement, isValidElement, useId, type ReactElement, type ReactNode} from 'react';
import {BookOpen, Briefcase, Building2, Compass, Globe2, HeartPulse, Laptop, Wallet} from 'lucide-react';
import type {Source} from './api';

export const iconProps={size:18,'aria-hidden':true as const,strokeWidth:1.8};

export function ErrorBox({text}:{text:string}){
  return text?<p role="alert" className="alert alert-error">{text}</p>:null;
}

export function Field({label,hint,children}:{label:string;hint?:string;children:ReactNode}){
  const id=useId();
  // The hint sits outside the <label> so the accessible name stays exactly the label text.
  const control=hint&&isValidElement(children)?cloneElement(children as ReactElement<{'aria-describedby'?:string}>,{'aria-describedby':id}):children;
  return <div className="field"><label className="field-inner"><span className="field-label">{label}</span>{control}</label>{hint&&<span id={id} className="field-hint">{hint}</span>}</div>;
}

const CATEGORY_ICONS:Record<string,typeof Compass>={
  'Money & aid':Wallet,'Academics':BookOpen,'Health & wellbeing':HeartPulse,'International':Globe2,
  'Technology':Laptop,'Campus life':Building2,'Career & support':Briefcase,
};
export function CategoryIcon({name,size=20}:{name:string;size?:number}){
  const Icon=CATEGORY_ICONS[name]||Compass;
  return <Icon size={size} aria-hidden="true" strokeWidth={1.7}/>;
}

/** Contact strings are stored as "phone · email"; show each method on its own line. */
export function ContactLines({value}:{value:string}){
  return <>{value.split(' · ').map(part=><span className="contact-line" key={part}>{part}</span>)}</>;
}

export function Citations({ids,sources}:{ids:number[];sources:Source[]}){
  return <span className="citations">{ids.map(id=>{
    const index=sources.findIndex(s=>s.id===id);
    if(index<0)return null;
    return <a key={id} href={sources[index].url} target="_blank" rel="noopener noreferrer" aria-label={'Source '+(index+1)+': '+sources[index].title}>{index+1}</a>;
  })}</span>;
}

export function Wordmark({inverse=false}:{inverse?:boolean}){
  return <span className={'wordmark'+(inverse?' wordmark-inverse':'')}>
    <svg className="wordmark-star" viewBox="0 0 40 40" aria-hidden="true"><path d="M20 3l4.9 10.6 11.6 1.3-8.6 7.9 2.4 11.4L20 28.4 9.7 34.2l2.4-11.4-8.6-7.9 11.6-1.3z"/></svg>
    <span className="wordmark-text">MavAssist</span>
  </span>;
}
