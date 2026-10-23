export type User={id:number; name:string; email:string; role:'student'|'administrator'};
export type Category={id:number;name:string};
export type Notice={id:number;service_id:number;title:string;body:string;starts_at:string;ends_at:string};
export type Service={id:number;name:string;description:string;category_id:number;category:string;location:string;hours:string;contact:string;source_url:string;tags:string[];next_steps:string[];active:boolean;verified:boolean;updated_at:string;notices?:Notice[]};
export type Recommendation=Service & {reason:string;role:'recommended'|'alternative'};
export type CitedPart={text:string;source_ids:number[]};
export type Source={id:number;title:string;url:string;reviewed_at:string|null};
export type AnswerMode='grounded'|'rag'|'fallback'|'clarification'|'out_of_scope'|'greeting'|'safety'|'crisis'|'boundary';
export type Action={label:string;href:string};
export type Answer={answer_id:string;mode:AnswerMode;actions?:Action[];confidence:'high'|'medium'|'low';message:string;answer:CitedPart[];steps:CitedPart[];sources:Source[];options:string[];recommendations:Recommendation[];question:string;rated?:boolean};
export type Session={access_token:string;expires_at:string;user:User};
export const BASE=import.meta.env.VITE_API_URL || '';
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
  const token=sessionStorage.getItem('mavassist-token');
  const response=await fetch(BASE+path,{...options,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:`Bearer ${token}`} :{}),...options.headers}});
  if(!response.ok){
    const body=await response.json().catch(()=>({detail:'Unable to complete the request'}));
    if(response.status===401 && !path.includes('/auth/')){sessionStorage.removeItem('mavassist-token');window.dispatchEvent(new Event('session-expired'));}
    throw new Error(typeof body.detail==='string'?body.detail:body.detail?.map((x:{msg:string})=>x.msg).join('; ') || 'Check your input and try again');
  }
  return response.json();
}
export const json=(method:string,body:unknown):RequestInit=>({method,body:JSON.stringify(body)});
export function dateLabel(value:string){return new Date(value).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});}
