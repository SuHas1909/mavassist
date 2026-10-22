import {FormEvent, useCallback, useEffect, useMemo, useState} from 'react';
import {Check, Plus, Search} from 'lucide-react';
import {api, Category, dateLabel, json, Notice, Service} from '../api';
import {ErrorBox, Field, iconProps} from '../ui';

type Tab='services'|'categories'|'notices';
type Status='all'|'active'|'archived'|'review';
const PAGE=12;
function localDate(s:string){const d=new Date(s);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}

export default function Manage({categories,reloadCategories}:{categories:Category[];reloadCategories:()=>void}){
  const [items,setItems]=useState<Service[]>([]),[notices,setNotices]=useState<Notice[]>([]),[error,setError]=useState(''),[message,setMessage]=useState('');
  const [tab,setTab]=useState<Tab>('services'),[editing,setEditing]=useState<Service|null|undefined>(undefined),[busy,setBusy]=useState(false),[noticeEdit,setNoticeEdit]=useState<Notice|null>(null);
  const [filter,setFilter]=useState(''),[category,setCategory]=useState(0),[status,setStatus]=useState<Status>('all'),[sort,setSort]=useState<'name'|'recent'>('name'),[page,setPage]=useState(0);

  const load=useCallback(async()=>{
    try{const [s,n]=await Promise.all([api<Service[]>('/api/admin/services'),api<Notice[]>('/api/admin/notices')]);setItems(s);setNotices(n);}
    catch(err){setError((err as Error).message);}
  },[]);
  useEffect(()=>{void load();},[load]);

  async function action(fn:()=>Promise<unknown>,success:string){
    setError('');setMessage('');setBusy(true);
    try{await fn();setMessage(success);await load();reloadCategories();}
    catch(err){setError((err as Error).message);}
    finally{setBusy(false);}
  }
  function serviceSubmit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();const f=new FormData(e.currentTarget);
    const body={...Object.fromEntries(f),category_id:Number(f.get('category_id')),
      tags:String(f.get('tags')).split(',').map(x=>x.trim()).filter(Boolean),
      next_steps:String(f.get('next_steps')).split('\n').map(x=>x.trim()).filter(Boolean),
      active:f.get('active')==='on',verified:f.get('verified')==='on'};
    void action(async()=>{await api(editing?'/api/admin/services/'+editing.id:'/api/admin/services',json(editing?'PUT':'POST',body));setEditing(undefined);setSort('recent');setPage(0);setFilter('');setStatus('all');setCategory(0);},'Service saved.');
  }

  const stats=useMemo(()=>({total:items.length,active:items.filter(s=>s.active).length,archived:items.filter(s=>!s.active).length,review:items.filter(s=>s.active&&!s.verified).length}),[items]);
  const rows=useMemo(()=>{
    const q=filter.trim().toLowerCase();
    return items.filter(s=>(!q||s.name.toLowerCase().includes(q)||s.location.toLowerCase().includes(q))&&(!category||s.category_id===category)
      &&(status==='all'||(status==='active'&&s.active)||(status==='archived'&&!s.active)||(status==='review'&&s.active&&!s.verified)))
      .sort((a,b)=>sort==='name'?a.name.localeCompare(b.name):b.updated_at.localeCompare(a.updated_at));
  },[items,filter,category,status,sort]);
  const pages=Math.max(1,Math.ceil(rows.length/PAGE)),current=Math.min(page,pages-1),visible=rows.slice(current*PAGE,current*PAGE+PAGE);

  return <>
    <section className="page-head" aria-labelledby="page-title"><div className="container">
      <h1 id="page-title">Resource management</h1>
      <p className="muted">Keep office details accurate, organize categories and publish time-limited notices.</p>
      <div className="tabs" role="group" aria-label="Management views">{(['services','categories','notices'] as Tab[]).map(t=><button key={t} aria-pressed={tab===t} className={tab===t?'tab tab-on':'tab'} onClick={()=>{setTab(t);setEditing(undefined);setNoticeEdit(null);setMessage('');}}>{t[0].toUpperCase()+t.slice(1)}</button>)}</div>
    </div></section>
    <div className="container admin">
      <ErrorBox text={error}/>{message&&<p role="status" className="alert alert-ok"><Check size={17} aria-hidden="true"/>{message}</p>}

      {tab==='services'&&(editing===undefined?<>
        <dl className="kpis">
          {([['all','Total services',stats.total],['active','Shown to students',stats.active],['archived','Archived',stats.archived],['review','Need source review',stats.review]] as [Status,string,number][]).map(([key,label,value])=>
            <div key={key} className={status===key?'kpi kpi-on':'kpi'}><dt><button className="kpi-button" aria-pressed={status===key} onClick={()=>{setStatus(key);setPage(0);}}>{label}</button></dt><dd>{value}</dd></div>)}
        </dl>
        <div className="toolbar">
          <div className="toolbar-search"><Search {...iconProps}/><label className="sr-only" htmlFor="admin-filter">Filter services</label><input id="admin-filter" placeholder="Filter by name or location" value={filter} onChange={e=>{setFilter(e.target.value);setPage(0);}}/></div>
          <label className="sr-only" htmlFor="admin-category">Category</label>
          <select id="admin-category" value={category} onChange={e=>{setCategory(Number(e.target.value));setPage(0);}}><option value={0}>All categories</option>{categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
          <label className="sr-only" htmlFor="admin-sort">Sort</label>
          <select id="admin-sort" value={sort} onChange={e=>setSort(e.target.value as 'name'|'recent')}><option value="name">Name A–Z</option><option value="recent">Recently updated</option></select>
          <button className="btn btn-primary" onClick={()=>setEditing(null)}><Plus {...iconProps}/>Add service</button>
        </div>
        <div className="table-wrap"><table>
          <caption className="sr-only">Services, {rows.length} shown</caption>
          <thead><tr><th scope="col">Service</th><th scope="col">Category</th><th scope="col">Source</th><th scope="col">Status</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>{visible.map(s=><tr key={s.id}>
            <td><strong>{s.name}</strong><small>Updated {dateLabel(s.updated_at)}</small></td>
            <td>{s.category}</td>
            <td><span className={s.verified?'tag tag-ok':'tag tag-warn'}>{s.verified?'Verified':'Needs review'}</span></td>
            <td><span className={s.active?'tag tag-live':'tag tag-off'}>{s.active?'Active':'Archived'}</span></td>
            <td className="row-actions">
              <button className="link-button" onClick={()=>setEditing(s)}>Edit<span className="sr-only"> {s.name}</span></button>
              <button className="link-button" disabled={busy} onClick={()=>void action(()=>api('/api/admin/services/'+s.id+'/active',json('PATCH',{active:!s.active})),s.active?'Service archived.':'Service restored.')}>{s.active?'Archive':'Restore'}<span className="sr-only"> {s.name}</span></button>
            </td>
          </tr>)}{visible.length===0&&<tr><td colSpan={5} className="muted">No services match these filters.</td></tr>}</tbody>
        </table></div>
        {pages>1&&<nav className="pager" aria-label="Service pages">
          <button className="btn btn-secondary" disabled={current===0} onClick={()=>setPage(current-1)}>Previous</button>
          <span>Page {current+1} of {pages}</span>
          <button className="btn btn-secondary" disabled={current>=pages-1} onClick={()=>setPage(current+1)}>Next</button>
        </nav>}
      </>:<form className="panel editor" onSubmit={serviceSubmit} key={editing?.id||'new'}>
        <div className="panel-head"><h2>{editing?'Edit '+editing.name:'Add a service'}</h2><button type="button" className="btn btn-secondary" onClick={()=>setEditing(undefined)}>Cancel</button></div>
        <div className="form-grid">
          <Field label="Service name"><input name="name" defaultValue={editing?.name} required minLength={2} maxLength={160}/></Field>
          <Field label="Category"><select name="category_id" defaultValue={editing?.category_id||categories[0]?.id} required>{categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <Field label="Location"><input name="location" defaultValue={editing?.location} required maxLength={250}/></Field>
          <Field label="Operating hours"><input name="hours" defaultValue={editing?.hours} required maxLength={250}/></Field>
          <Field label="Contact information" hint="Separate phone and email with “ · ”."><input name="contact" defaultValue={editing?.contact} required maxLength={250}/></Field>
          <Field label="Official source URL"><input name="source_url" type="url" placeholder="https://www.uta.edu/…" defaultValue={editing?.source_url} required maxLength={500}/></Field>
        </div>
        <Field label="Description"><textarea name="description" defaultValue={editing?.description} required minLength={10} maxLength={3000}/></Field>
        <Field label="Search tags (comma separated)" hint="Words students actually use, such as “I-20”, “bill”, “tutor”."><input name="tags" defaultValue={editing?.tags.join(', ')} maxLength={2000}/></Field>
        <Field label="Next steps (2 or 3 lines; one step per line)"><textarea name="next_steps" defaultValue={editing?.next_steps.join('\n')} required/></Field>
        <div className="checks">
          <label><input name="active" type="checkbox" defaultChecked={editing?.active??true}/>Show in the student directory and assistant</label>
          <label><input name="verified" type="checkbox" defaultChecked={editing?.verified??false}/>I checked these details against the official source</label>
        </div>
        <button className="btn btn-primary" disabled={busy}>Save service</button>
      </form>)}

      {tab==='categories'&&<div className="panel">
        <h2>Categories</h2>
        <form className="inline-form" onSubmit={e=>{e.preventDefault();const f=e.currentTarget;const name=String(new FormData(f).get('name'));void action(async()=>{await api('/api/admin/categories',json('POST',{name}));f.reset();},'Category added.');}}>
          <Field label="New category"><input name="name" required minLength={2} maxLength={80}/></Field>
          <button className="btn btn-primary" disabled={busy}>Add category</button>
        </form>
        <ul className="category-list">{categories.map(c=><li key={c.id}><form className="inline-form" onSubmit={e=>{e.preventDefault();void action(()=>api('/api/admin/categories/'+c.id,json('PUT',{name:new FormData(e.currentTarget).get('name')})),'Category renamed.');}}>
          <label className="sr-only" htmlFor={'category-'+c.id}>Rename {c.name}</label>
          <input id={'category-'+c.id} name="name" defaultValue={c.name} required minLength={2} maxLength={80}/>
          <span className="muted category-count">{items.filter(s=>s.category_id===c.id).length} services</span>
          <button className="btn btn-secondary" disabled={busy}>Rename</button>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={()=>void action(()=>api('/api/admin/categories/'+c.id,{method:'DELETE'}),'Category deleted.')}>Delete<span className="sr-only"> {c.name}</span></button>
        </form></li>)}</ul>
      </div>}

      {tab==='notices'&&<div className="notices-layout">
        <div className="panel"><h2>{noticeEdit?'Edit notice':'Publish a service notice'}</h2>
          <p className="muted">Notices appear on the service’s detail page only between the start and end times.</p>
          <form key={noticeEdit?.id||'new-notice'} onSubmit={e=>{e.preventDefault();const f=e.currentTarget;const d=new FormData(f);void action(async()=>{await api('/api/admin/notices'+(noticeEdit?'/'+noticeEdit.id:''),json(noticeEdit?'PUT':'POST',{service_id:Number(d.get('service_id')),title:d.get('title'),body:d.get('body'),starts_at:new Date(String(d.get('starts_at'))).toISOString(),ends_at:new Date(String(d.get('ends_at'))).toISOString()}));setNoticeEdit(null);f.reset();},'Notice saved.');}}>
            <Field label="Related service"><select name="service_id" defaultValue={noticeEdit?.service_id} required>{items.filter(s=>s.active).map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></Field>
            <Field label="Notice title"><input name="title" defaultValue={noticeEdit?.title} required minLength={2} maxLength={160}/></Field>
            <div className="form-grid">
              <Field label="Starts (your local time)"><input name="starts_at" type="datetime-local" defaultValue={noticeEdit?localDate(noticeEdit.starts_at):undefined} required/></Field>
              <Field label="Ends (your local time)"><input name="ends_at" type="datetime-local" defaultValue={noticeEdit?localDate(noticeEdit.ends_at):undefined} required/></Field>
            </div>
            <Field label="Notice text"><textarea name="body" defaultValue={noticeEdit?.body} required minLength={2} maxLength={2000}/></Field>
            <div className="actions"><button className="btn btn-primary" disabled={busy}>{noticeEdit?'Update notice':'Publish notice'}</button>{noticeEdit&&<button className="btn btn-secondary" type="button" onClick={()=>setNoticeEdit(null)}>Cancel edit</button>}</div>
          </form>
        </div>
        <div className="notice-list"><h2>Scheduled and past notices</h2>{notices.length===0&&<p className="muted">No notices yet.</p>}{notices.map(n=>{
          const live=new Date(n.starts_at)<=new Date()&&new Date(n.ends_at)>=new Date();
          return <article className="notice" key={n.id}>
            <div className="notice-head"><strong>{n.title}</strong><span className={live?'tag tag-live':'tag tag-off'}>{live?'Live now':new Date(n.starts_at)>new Date()?'Scheduled':'Ended'}</span></div>
            <p>{n.body}</p><small>{items.find(s=>s.id===n.service_id)?.name} · {dateLabel(n.starts_at)} to {dateLabel(n.ends_at)}</small>
            <div className="actions"><button className="link-button" onClick={()=>setNoticeEdit(n)}>Edit notice<span className="sr-only"> {n.title}</span></button><button className="link-button" disabled={busy} onClick={()=>void action(()=>api('/api/admin/notices/'+n.id,{method:'DELETE'}),'Notice removed.')}>Remove<span className="sr-only"> {n.title}</span></button></div>
          </article>;})}</div>
      </div>}
    </div>
  </>;
}
