
function toast(msg, kind='info', timeout=3000){
  const t=document.getElementById('toast');
  t.textContent=msg; t.hidden=false; t.className='toast';
  if(kind==='error') t.style.borderColor='#ef4444';
  else if(kind==='warn') t.style.borderColor='#f59e0b';
  setTimeout(()=>{t.hidden=true}, timeout);
}

async function apiHealth(){
  try{const r=await fetch('/health'); const j=await r.json(); if(j.ok){toast('Service healthy ✓');} else {toast('Service issue', 'warn');}}
  catch(e){toast('Server unreachable', 'error');}
}

async function loadTitles(){
  const dl=document.getElementById('titles');
  dl.innerHTML='';
  try{
    const res=await fetch('/titles');
    const titles=await res.json();
    titles.slice(0,10000).forEach(t=>{const opt=document.createElement('option'); opt.value=t; dl.appendChild(opt);});
  }catch(e){
    toast('Could not load titles', 'warn');
  }
}

function setLoading(loading){
  const btn=document.getElementById('goBtn');
  const spinner=btn.querySelector('.spinner');
  if(loading){
    btn.setAttribute('disabled',''); spinner.hidden=false;
  }else{
    btn.removeAttribute('disabled'); spinner.hidden=true;
  }
}

function clearResults(){
  document.getElementById('results').innerHTML='';
}

async function recommend(){
  const title=document.getElementById('titleInput').value.trim();
  const k=Number(document.getElementById('kInput').value||10);
  const resultsEl=document.getElementById('results');
  clearResults();
  if(!title){ toast('Please enter a title', 'warn'); return; }
  setLoading(true);
  resultsEl.setAttribute('aria-busy','true');
  try{
    const res=await fetch('/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,k})});
    const data=await res.json();
    if(!res.ok){ toast(data.error||'Error', 'error'); return; }
    if(!data.results||data.results.length===0){ resultsEl.innerHTML='<div class="banner warning">No recommendations found.</div>'; return; }
    data.results.forEach((item,i)=>{
      const div=document.createElement('div');
      div.className='result-item';
      div.innerHTML=`
        <div class="result-head">
          <h3>${i+1}. ${item.title}</h3>
          <span class="badge">${item.score}</span>
        </div>
        <div class="meta">Genres: <strong>${item.main_genre}</strong> / ${item.side_genre}</div>
        <div class="meta">Rating: ${item.rating ?? 'N/A'} • Runtime: ${item.runtime ?? 'N/A'} mins</div>
      `;
      resultsEl.appendChild(div);
    });
  }catch(e){
    toast('Network error', 'error');
  }finally{
    setLoading(false); resultsEl.setAttribute('aria-busy','false');
  }
}

window.addEventListener('DOMContentLoaded',()=>{
  loadTitles();
  document.getElementById('goBtn').addEventListener('click', recommend);
  document.getElementById('clearBtn').addEventListener('click', ()=>{ document.getElementById('titleInput').value=''; clearResults();});
  document.getElementById('healthLink').addEventListener('click', (e)=>{ e.preventDefault(); apiHealth(); });
  // Keyboard shortcuts
  window.addEventListener('keydown',(e)=>{
    if(e.key==='/'){ e.preventDefault(); document.getElementById('titleInput').focus(); }
    if(e.key==='Enter' && document.activeElement===document.getElementById('titleInput')){ recommend(); }
    if(e.key==='Escape'){ document.getElementById('titleInput').blur(); clearResults(); }
  });
});
