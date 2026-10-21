import {useCallback, useEffect, useState} from 'react';
import {LogOut} from 'lucide-react';
import {api, Category, Service, Session, User} from './api';
import {ErrorBox, Wordmark} from './ui';
import Auth from './pages/Auth';
import Directory, {ListMode} from './pages/Directory';
import ServiceDrawer from './pages/ServiceDrawer';
import Assistant from './pages/Assistant';
import Manage from './pages/Manage';
import Insights from './pages/Insights';

type Page=ListMode|'assistant'|'manage'|'analytics';
const TOKEN='mavassist-token';

export default function App(){
  const [user,setUser]=useState<User|null>(null),[initializing,setInitializing]=useState(!!sessionStorage.getItem(TOKEN));
  const [page,setPage]=useState<Page>('directory'),[categories,setCategories]=useState<Category[]>([]),[bookmarks,setBookmarks]=useState<Service[]>([]);
  const [detail,setDetail]=useState<Service|null>(null),[error,setError]=useState('');

  const logout=useCallback(()=>{sessionStorage.removeItem(TOKEN);setUser(null);setDetail(null);setPage('directory');setBookmarks([]);},[]);
  useEffect(()=>{
    const expired=()=>{logout();setError('Your session expired. Sign in again to continue.');};
    window.addEventListener('session-expired',expired);
    if(sessionStorage.getItem(TOKEN))api<User>('/api/auth/me').then(setUser).catch(logout).finally(()=>setInitializing(false));
    return ()=>window.removeEventListener('session-expired',expired);
  },[logout]);
  const reloadCategories=useCallback(()=>{api<Category[]>('/api/categories').then(setCategories).catch(e=>setError(e.message));},[]);
  const loadBookmarks=useCallback(async()=>{try{setBookmarks(await api<Service[]>('/api/bookmarks'));}catch(e){setError((e as Error).message);}},[]);
  useEffect(()=>{if(user){reloadCategories();void loadBookmarks();}},[user,reloadCategories,loadBookmarks]);

  async function open(id:number){setError('');try{setDetail(await api<Service>('/api/services/'+id));}catch(e){setError((e as Error).message);}}
  async function save(s:Service){
    try{const exists=bookmarks.some(b=>b.id===s.id);await api('/api/bookmarks/'+s.id,{method:exists?'DELETE':'PUT'});await loadBookmarks();}
    catch(e){setError((e as Error).message);}
  }
  function go(p:Page){setPage(p);setError('');window.scrollTo({top:0});}

  if(initializing)return <main className="loading" role="status">Opening MavAssist…</main>;
  if(!user)return <><ErrorBox text={error}/><Auth onSession={s=>{sessionStorage.setItem(TOKEN,s.access_token);setUser(s.user);setError('');window.scrollTo({top:0});}}/></>;

  const nav:[Page,string][]=[['directory','Explore resources'],['assistant','Ask MavAssist'],['bookmarks','Saved resources'],['recent','Recently viewed']];
  if(user.role==='administrator')nav.push(['manage','Manage resources'],['analytics','Usage insights']);
  const bookmarkIds=bookmarks.map(b=>b.id);

  return <div className="shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <div className="utility"><div className="container utility-inner">
      <span>Student services guide for the University of Texas at Arlington</span>
      <span className="utility-user">{user.name}<span className="utility-role">{user.role==='administrator'?'Administrator':'Student'}</span>
        <button className="utility-signout" onClick={logout}><LogOut size={15} aria-hidden="true"/>Sign out</button></span>
    </div></div>
    <header className="masthead"><div className="container masthead-inner">
      <button className="brand-button" onClick={()=>go('directory')} aria-label="MavAssist home"><Wordmark/></button>
      <nav aria-label="Main navigation" className="mainnav">{nav.map(([id,label])=><button key={id} className={page===id?'navlink navlink-on':'navlink'} aria-current={page===id?'page':undefined} onClick={()=>go(id)}>
        {label}{id==='bookmarks'&&bookmarks.length>0&&<span className="nav-count" aria-hidden="true">{bookmarks.length}</span>}
      </button>)}</nav>
    </div></header>
    <main id="main" tabIndex={-1}>
      {error&&<div className="container"><ErrorBox text={error}/></div>}
      {page==='assistant'?<Assistant onOpen={id=>void open(id)}/>
      :page==='manage'?<Manage categories={categories} reloadCategories={reloadCategories}/>
      :page==='analytics'?<Insights/>
      :<Directory key={page} mode={page} categories={categories} bookmarkIds={bookmarkIds} onOpen={id=>void open(id)} onSave={s=>void save(s)} onAsk={()=>go('assistant')} onBrowse={()=>go('directory')}/>}
    </main>
    <footer className="footer"><div className="container footer-inner">
      <div><Wordmark inverse/><p>An independent course project for CSE 6324 Advanced Topics in Software Engineering, Team 3. Not an official UTA service and not connected to MyMav or student records.</p></div>
      <div><h2>Using this guide</h2><p>Office details were collected from public uta.edu pages and show the date they were last checked. Always confirm on the official page before a visit.</p></div>
      <div><h2>In an emergency</h2><p>Call 911 or UTA Police at 817-272-3003. For a mental health crisis, MAVS TALK is available 24/7 at 817-272-8255.</p></div>
    </div></footer>
    {detail&&<ServiceDrawer service={detail} onClose={()=>setDetail(null)} saved={bookmarkIds.includes(detail.id)} onSave={()=>void save(detail)}/>}
  </div>;
}
