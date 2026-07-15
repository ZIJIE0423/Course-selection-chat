document.addEventListener('DOMContentLoaded',()=>{
 const panels=[...document.querySelectorAll('.setup-panel')],steps=[...document.querySelectorAll('.step')];let current=0;function show(i){current=i;panels.forEach((p,n)=>p.classList.toggle('active',n===i));steps.forEach((s,n)=>s.classList.toggle('active',n===i))}
 document.querySelector('#matchBtn').onclick=()=>{const required=['grade','college','major'];for(const n of required){if(!document.querySelector(`[name=${n}]`).value)return toast('请先完成年级、学院和专业信息')}const btn=document.querySelector('#matchBtn');btn.disabled=true;btn.textContent='正在匹配培养方案…';setTimeout(()=>show(1),900)};
 document.querySelectorAll('[data-back-setup]').forEach(b=>b.onclick=()=>show(0));document.querySelector('#confirmPlan').onclick=()=>{localStorage.setItem('weoucProfileConfirmed','true');location.href='index.html?welcome=1'};
 const transfer=document.querySelectorAll('[name=transfer]'),extra=document.querySelector('#transferFields');transfer.forEach(r=>r.onchange=()=>extra.classList.toggle('hidden',r.value!=='是'));
 window.addEventListener('beforeunload',()=>localStorage.setItem('weoucSetupDraft','true'));
});
