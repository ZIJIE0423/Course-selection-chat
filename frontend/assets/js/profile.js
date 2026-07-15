document.addEventListener('DOMContentLoaded',()=>{
 const auth=document.querySelector('#authBtn'),state=document.querySelector('#authState');let granted=localStorage.getItem('weoucScheduleAuth')==='true';
 function render(){state.textContent=granted?'已授权':'未授权';state.className=`badge ${granted?'success':'risk'}`;auth.textContent=granted?'取消授权':'授权读取课表';auth.className=`btn ${granted?'btn-danger':'btn-primary'} btn-sm`}
 auth.onclick=()=>{granted=!granted;localStorage.setItem('weoucScheduleAuth',granted);render();toast(granted?'课表读取授权已开启':'已取消授权，不再获取新的课表')};render();
 document.querySelectorAll('[data-delete-pref]').forEach(b=>b.onclick=()=>{b.closest('.preference').remove();toast('偏好已删除')});
 const stored=JSON.parse(localStorage.getItem('weoucSubmissions')||'[]'),seed=[{id:'WOC-26070123',course:'大学英语Ⅲ',status:'审核中',date:'2026/7/1'},{id:'WOC-26061108',course:'海洋科学导论',status:'已通过',date:'2026/6/11'},{id:'WOC-26052217',course:'设计思维与创新',status:'需修改',date:'2026/5/22'}];
 document.querySelector('#submissions').innerHTML=`<div class="card-title"><h2>我的投稿</h2><a class="btn btn-secondary btn-sm" href="feedback.html">分享新体验</a></div>`+[...stored,...seed].map(x=>`<div class="submission"><div><h4>${x.course}</h4><div class="muted small">${x.id} · ${x.date}</div></div><div style="text-align:right"><span class="badge ${x.status==='已通过'?'success':x.status==='需修改'?'risk':'official'}">${x.status}</span><div><button class="btn btn-ghost btn-sm" style="margin-top:8px" onclick="toast('${x.status==='审核中'?'已撤回投稿':'已打开投稿详情'}')">${x.status==='审核中'?'撤回':'查看'}</button></div></div></div>`).join('');
});
