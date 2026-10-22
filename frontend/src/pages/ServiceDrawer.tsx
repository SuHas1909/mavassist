import {useEffect, useRef} from 'react';
import {Bookmark, CircleAlert, ExternalLink, ShieldCheck, X} from 'lucide-react';
import {dateLabel, Service} from '../api';
import {CategoryIcon, ContactLines, iconProps} from '../ui';

export default function ServiceDrawer({service:s,saved,onClose,onSave}:{service:Service;saved:boolean;onClose:()=>void;onSave:()=>void}){
  const ref=useRef<HTMLDialogElement>(null);
  useEffect(()=>{const d=ref.current;d?.showModal();return ()=>d?.close();},[]);
  return <dialog ref={ref} onCancel={onClose} onClick={e=>{if(e.target===ref.current)onClose();}} aria-labelledby="resource-title" className="drawer">
    <div className="drawer-body">
      <div className="drawer-top">
        <span className="drawer-cat"><CategoryIcon name={s.category} size={17}/>{s.category}</span>
        <button className="icon-btn" aria-label="Close resource" onClick={onClose}><X {...iconProps}/></button>
      </div>
      <h2 id="resource-title">{s.name}</h2>
      <p className="drawer-desc">{s.description}</p>
      <p className={'verify '+(s.verified?'verify-ok':'verify-warn')}>
        {s.verified?<ShieldCheck {...iconProps}/>:<CircleAlert {...iconProps}/>}
        {s.verified?`Details checked against the official page, ${dateLabel(s.updated_at)}.`:'Not yet verified by an administrator. Confirm details on the official page.'}
      </p>
      {s.notices?.map(n=><div className="notice" role="note" key={n.id}><strong>{n.title}</strong><p>{n.body}</p></div>)}
      <dl className="facts">
        <div><dt>Where</dt><dd>{s.location}</dd></div>
        <div><dt>When</dt><dd>{s.hours}</dd></div>
        <div><dt>Contact</dt><dd><ContactLines value={s.contact}/></dd></div>
        <div><dt>Last updated</dt><dd>{dateLabel(s.updated_at)}</dd></div>
      </dl>
      <h3 className="steps-title">Your next steps</h3>
      <ol className="route-steps">{s.next_steps.map((step,i)=><li key={i}>{step}</li>)}</ol>
    </div>
    <div className="drawer-actions">
      <a className="btn btn-primary" href={s.source_url} target="_blank" rel="noopener noreferrer">Official resource<ExternalLink size={16} aria-hidden="true"/></a>
      <button className="btn btn-secondary" onClick={onSave}><Bookmark {...iconProps} fill={saved?'currentColor':'none'}/>{saved?'Remove bookmark':'Save resource'}</button>
    </div>
  </dialog>;
}
