'use strict';
const $ = id => document.getElementById(id);
let csrf = '', user = null, registering = false, subjects = [], tasks = [], editing = null;
const labels = {pending:'Pending',in_progress:'In progress',completed:'Completed'};
function el(tag, text, cls) { const node=document.createElement(tag); if(text!==undefined) node.textContent=text; if(cls) node.className=cls; return node; }
function notice(text, error=false) { $('notice').textContent=text; $('notice').className=error?'error':''; }
async function api(path, method='GET', data) {
  const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:data===undefined?undefined:JSON.stringify(data)});
  const result=response.status===204?{}:await response.json();
  if(!response.ok) throw Error(result.error || 'Request failed.');
  if(result.csrf_token) csrf=result.csrf_token;
  return result;
}
async function boot() {
  try { const result=await api('/session'); user=result.user; $('auth').hidden=!!user; $('workspace').hidden=!user; $('logout').hidden=!user; if(user) await load(); }
  catch(error) { notice(error.message+' Check that the database has been initialized.',true); }
}
async function load() {
  $('greeting').textContent=`Welcome back, ${user.name}.`;
  const [s,summary]=await Promise.all([api('/subjects'),api('/dashboard')]); subjects=s.subjects;
  const values=Object.fromEntries(new FormData($('filters'))); const previous=values.subject_id;
  for(const [id,all] of [['filter-subject',true],['task-subject',false]]) {
    $(id).replaceChildren(); if(all) $(id).append(new Option('All subjects',''));
    for(const subject of subjects) $(id).append(new Option(subject.name,subject.id));
  }
  if(subjects.some(s=>String(s.id)===previous)) $('filter-subject').value=previous;
  $('subject-count').textContent=subjects.length;
  $('subjects').replaceChildren();
  for(const subject of subjects) {
    const li=el('li'); li.append(el('strong',subject.name)); const actions=el('div',undefined,'actions');
    const rename=el('button','Rename'); rename.onclick=async()=>{ const name=prompt('Subject name',subject.name); if(name===null) return; try {await api('/subjects/'+subject.id,'PATCH',{name});await load();} catch(e){notice(e.message,true);} };
    const remove=el('button','Delete','danger'); remove.onclick=async()=>{if(!confirm(`Delete subject “${subject.name}”?`)) return;try{await api('/subjects/'+subject.id,'DELETE');await load();}catch(e){notice(e.message,true);}};
    actions.append(rename,remove);li.append(actions);$('subjects').append(li);
  }
  $('stats').replaceChildren();
  for(const [title,value] of [['Total tasks',summary.total],['Completed',summary.completed],['Overdue',summary.overdue],['Minutes remaining',summary.remaining_minutes]]) {const card=el('div',undefined,'stat');card.append(el('span',title),el('strong',value));$('stats').append(card);}
  await loadTasks();
}
async function loadTasks() {
  const params=new URLSearchParams(); for(const [key,value] of new FormData($('filters'))) if(value) params.set(key,value);
  tasks=(await api('/tasks?'+params)).tasks; $('tasks').replaceChildren();
  if(!tasks.length) { $('tasks').append(el('div',subjects.length?'No tasks match. Add a task or clear your filters.':'Start by adding your first subject.','empty')); return; }
  for(const task of tasks) {
    const card=el('article',undefined,'card task '+task.status), badges=el('div',undefined,'badges');
    badges.append(el('span',task.subject_name,'badge'),el('span',task.priority+' priority','badge '+task.priority),el('span',labels[task.status],'badge'));
    card.append(badges,el('h3',task.title)); if(task.notes) card.append(el('p',task.notes));
    const bottom=el('div',undefined,'task-bottom'); bottom.append(el('span',`Due ${task.due_date} · ${task.estimated_minutes} min · Score ${task.priority_score}`,'muted'));
    const actions=el('div',undefined,'actions'), complete=el('button',task.status==='completed'?'Reopen':'Complete');
    complete.onclick=async()=>{try{await api('/tasks/'+task.id,'PATCH',{status:task.status==='completed'?'pending':'completed'});await load();}catch(e){notice(e.message,true);}};
    const edit=el('button','Edit');edit.onclick=()=>openTask(task);
    const remove=el('button','Delete','danger');remove.onclick=async()=>{if(!confirm(`Delete task “${task.title}”?`))return;try{await api('/tasks/'+task.id,'DELETE');await load();}catch(e){notice(e.message,true);}};
    actions.append(complete,edit,remove);bottom.append(actions);card.append(bottom);$('tasks').append(card);
  }
}
function openTask(task=null) {
  if(!subjects.length){notice('Add a subject before creating a task.',true);return;}
  editing=task?.id||null;$('task-form').reset();$('task-heading').textContent=editing?'Edit task':'New task';$('task-error').textContent='';
  if(task) {
    for(const [key,value] of Object.entries(task)) {
      const field = $('task-form').elements.namedItem(key);
      if(field) field.value=value;
    }
  }
  $('task-dialog').showModal();
}
$('auth-toggle').onclick=()=>{registering=!registering;$('name-label').hidden=!registering;$('auth-form').elements.name.required=registering;$('auth-submit').textContent=registering?'Create account':'Sign in';$('auth-toggle').textContent=registering?'Already registered? Sign in':'New here? Create an account';$('auth-form').elements.password.autocomplete=registering?'new-password':'current-password';};
$('auth-form').onsubmit=async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(event.target));if(!registering)delete data.name;const button=$('auth-submit');button.disabled=true;try{const result=await api('/auth/'+(registering?'register':'login'),'POST',data);user=result.user;notice('');await boot();event.target.reset();}catch(e){notice(e.message,true);}finally{button.disabled=false;}};
$('logout').onclick=async()=>{try{await api('/auth/logout','POST');notice('Signed out.');await boot();}catch(e){notice(e.message,true);}};
$('edit-profile').onclick=async()=>{const name=prompt('Your display name',user.name);if(name===null)return;try{user=(await api('/users/me','PATCH',{name})).user;await load();}catch(e){notice(e.message,true);}};
$('subject-form').onsubmit=async event=>{event.preventDefault();try{await api('/subjects','POST',{name:$('subject-name').value});event.target.reset();notice('Subject added.');await load();}catch(e){notice(e.message,true);}};
$('filters').onsubmit=async event=>{event.preventDefault();try{await loadTasks();}catch(e){notice(e.message,true);}};
$('clear-filters').onclick=async()=>{$('filters').reset();try{await loadTasks();}catch(e){notice(e.message,true);}};
$('new-task').onclick=()=>openTask();$('close-dialog').onclick=()=>$('task-dialog').close();
$('task-form').onsubmit=async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(event.target));data.subject_id=Number(data.subject_id);data.estimated_minutes=Number(data.estimated_minutes);const button=event.submitter;button.disabled=true;try{await api('/tasks'+(editing?'/'+editing:''),editing?'PATCH':'POST',data);$('task-dialog').close();notice(editing?'Task updated.':'Task created.');await load();}catch(e){$('task-error').textContent=e.message;}finally{button.disabled=false;}};
boot();
