import {FormEvent, useState} from 'react';
import {api, json, Session} from '../api';
import {ErrorBox, Field, Wordmark} from '../ui';

export default function Auth({onSession}:{onSession:(s:Session)=>void}){
  const [register,setRegister]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function submit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();setError('');setBusy(true);
    const data=new FormData(e.currentTarget);
    try{onSession(await api<Session>(register?'/api/auth/register':'/api/auth/login',json('POST',Object.fromEntries(data))));}
    catch(err){setError((err as Error).message);}
    finally{setBusy(false);}
  }
  return <main className="auth">
    <section className="auth-story">
      <Wordmark inverse/>
      <div className="auth-story-body">
        <h1>Every office at UTA, one clear place to start.</h1>
        <p>Describe what you need in your own words. MavAssist points you to the office that handles it, where it is, when it’s open and what to do next.</p>
      </div>
      <dl className="auth-facts">
        <div><dt>50</dt><dd>campus offices and services, with location, hours and contact details</dd></div>
        <div><dt>1 link</dt><dd>to the official UTA page behind every answer</dd></div>
        <div><dt>0</dt><dd>questions stored with your name or email</dd></div>
      </dl>
      <p className="auth-disclaimer">An independent CSE 6324 course project by Team 3. Not an official UTA service.</p>
    </section>
    <section className="auth-panel" aria-labelledby="auth-title">
      <div className="auth-card">
        <h2 id="auth-title">{register?'Create your account.':'Welcome back.'}</h2>
        <p className="muted">{register?'Student accounts take less than a minute.':'Sign in to pick up where you left off.'}</p>
        <form onSubmit={submit} className="stack">
          {register&&<Field label="Full name"><input name="name" autoComplete="name" minLength={2} maxLength={100} required/></Field>}
          <Field label="Email address"><input name="email" type="email" autoComplete="email" maxLength={254} required/></Field>
          <Field label="Password" hint={register?'At least 10 characters. Don’t reuse your university password.':undefined}>
            <input name="password" type="password" autoComplete={register?'new-password':'current-password'} minLength={register?10:1} maxLength={72} required/>
          </Field>
          <ErrorBox text={error}/>
          <button className="btn btn-primary btn-block" disabled={busy}>{busy?'Please wait…':register?'Create student account':'Sign in'}</button>
        </form>
        <p className="auth-switch">{register?'Already have an account?':'New to MavAssist?'}{' '}
          <button type="button" className="link-button" onClick={()=>{setRegister(!register);setError('');}}>{register?'Sign in':'Create an account'}</button>
        </p>
        <p className="fine-print">Demo accounts only. Administrator accounts are created by the project team.</p>
      </div>
    </section>
  </main>;
}
