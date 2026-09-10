export const session={user:null,csrf:'',timezone:'Asia/Kolkata'};
export async function api(path,method='GET',body){
 const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await response.json().catch(()=>({detail:'The server returned an unreadable response.'}));
 if(!response.ok){if(response.status===401&&path!='/auth/login')window.dispatchEvent(new Event('session-expired'));const detail=Array.isArray(data.detail)?data.detail.map(e=>`${e.loc.slice(1).join('.')}: ${e.msg}`).join('\n'):data.detail;throw new Error(detail||`Request failed (${response.status})`)}
 return data;
}
export async function establish(){const data=await api('/auth/me');Object.assign(session,data);return data}
export function localInputToISO(value){return new Date(value).toISOString()}
export function localInput(value){const d=value?new Date(value):new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16)}
