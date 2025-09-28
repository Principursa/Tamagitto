// content.js — v7.2: sprint survives sprite clicks; restartable; badge safe; EF live toggle; draggable
console.log("[CC] content.js v7.2 loaded");

let ccState = { efMode: false, mounted: false };
let sprintTimer = null;
let sprintSecs = 0;

if (window.location.hostname === 'github.com') {
  boot();
}

async function boot() {
  ccState.efMode = await getEfMode();
  mount(ccState.efMode);

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'sync' && changes.efMode) {
      ccState.efMode = !!changes.efMode.newValue;
      unmount();
      mount(ccState.efMode);
    }
  });
}

function getEfMode() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ efMode: false }, (vals) => resolve(!!vals.efMode));
  });
}

function mount(efMode) {
  if (ccState.mounted) return;
  createFloatingSprite(efMode);
  ccState.mounted = true;
}

function unmount() {
  document.getElementById('coding-companion')?.remove();
  document.getElementById('cc-bubble')?.remove();
  stopSprint(); // clean up
  ccState.mounted = false;
}

function getRepoScopeFromUrl() {
  const m = window.location.href.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  return m ? m[2].toLowerCase() : "repo";
}

// ---------- position utils ----------
function clampPos(pos){
  const margin = 8;
  const maxLeft = Math.max(margin, window.innerWidth  - 40);
  const maxTop  = Math.max(margin, window.innerHeight - 40);
  return { left: Math.min(maxLeft, Math.max(margin, pos.left)), top: Math.min(maxTop, Math.max(margin, pos.top)) };
}
function loadPos(key) { try { const raw = localStorage.getItem(key); if (!raw) return null; const p=JSON.parse(raw); if (typeof p.left==='number'&&typeof p.top==='number') return clampPos(p); } catch{} return null; }
function savePos(key,pos){ try{ localStorage.setItem(key, JSON.stringify(clampPos(pos))); }catch{} }
function resetPos(key){ try{ localStorage.removeItem(key); }catch{} }

// ---------- tiny helpers ----------
function escapeHtml(s=''){ return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function ensureBadge(sprite){
  let b = document.getElementById('cc-badge');
  if (!b) {
    b = document.createElement('div');
    b.id = 'cc-badge';
    b.style.cssText = `position:absolute; bottom:-2px; right:-2px; min-width:18px; height:18px; padding:0 4px;
      background:#111; color:#fff; border-radius:9px; font-size:11px; display:none; align-items:center; justify-content:center;
      box-shadow: 0 2px 8px rgba(0,0,0,.3);`;
    sprite.appendChild(b);
  }
  return b;
}
function stopSprint(){
  if (sprintTimer) { clearInterval(sprintTimer); sprintTimer = null; }
  sprintSecs = 0;
  const badge = document.getElementById('cc-badge');
  if (badge) badge.style.display = 'none';
}

// ---------- main UI ----------
function createFloatingSprite(efMode) {
  const scope = getRepoScopeFromUrl();

  // SPRITE (draggable) with inner face span to avoid nuking children
  const sprite = document.createElement('div');
  sprite.id = 'coding-companion';
  const spriteStart = loadPos('cc-sprite-pos');
  sprite.style.cssText = `
    position: fixed; ${spriteStart ? `top:${spriteStart.top}px; left:${spriteStart.left}px;` : `bottom: 20px; right: 20px;`}
    width: 60px; height: 60px; background: linear-gradient(45deg,#4facfe 0%,#00f2fe 100%);
    border-radius: 50%; display:flex; align-items:center; justify-content:center;
    font-size: 30px; cursor: grab; z-index: 2147483647; animation: gentle-bounce 3s ease-in-out infinite;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3); -webkit-user-select:none; user-select:none; position:fixed;
  `;
  const face = document.createElement('span');
  face.id = 'cc-face';
  face.textContent = '🧙‍♂️';
  sprite.appendChild(face);

  // countdown badge (kept as child; never removed)
  const badge = ensureBadge(sprite);

  // BUBBLE (draggable)
  const bubble = document.createElement('div');
  bubble.id = 'cc-bubble';
  const bubbleStart = loadPos('cc-bubble-pos');
  bubble.style.cssText = `
    position: fixed; ${bubbleStart ? `top:${bubbleStart.top}px; left:${bubbleStart.left}px;` : `bottom: 90px; right: 20px;`}
    max-width: 340px; background:#111; color:#fff; padding:12px 14px; border-radius:12px;
    box-shadow: 0 8px 24px rgba(0,0,0,.25); font-size:13px; line-height:1.35; z-index:2147483647; -webkit-user-select:none; user-select:none;
  `;

  // header (drag) + close
  const header = document.createElement('div');
  header.style.cssText = `display:flex; align-items:center; gap:8px; margin:-6px -8px 8px -8px; padding:6px 8px 0 8px;
    cursor: grab; background: linear-gradient(90deg, rgba(255,255,255,.10), rgba(255,255,255,.05)); border-top-left-radius:10px; border-top-right-radius:10px;`;
  const grip = document.createElement('div'); grip.style.cssText = `width:36px; height:6px; border-radius:3px; background:rgba(255,255,255,.3); margin:2px 0;`;
  const closeBtn = document.createElement('button'); closeBtn.textContent='×'; closeBtn.setAttribute('aria-label','Close');
  closeBtn.style.cssText = `margin-left:auto; width:20px; height:20px; background:transparent; color:#bbb; border:0; font-size:16px; cursor:pointer;`;
  closeBtn.addEventListener('click', ()=> bubble.style.display='none');
  header.appendChild(grip); header.appendChild(closeBtn);

  const msgWrap = document.createElement('div'); msgWrap.id='cc-message';
  msgWrap.textContent = efMode ? 'Ready for a 5-min sprint?' : 'Hi! I can analyze this repo.';
  const coachWrap = document.createElement('div'); coachWrap.id='cc-coach'; coachWrap.style.cssText=`margin-top:8px; display:none;`;
  const whyWrap   = document.createElement('div'); whyWrap.id='cc-why';   whyWrap.style.cssText=`margin-top:6px; font-size:12px; color:#aaa; display:none;`;

  // EF controls
  const efWrap = document.createElement('div');
  if (efMode) {
    efWrap.style.cssText = 'margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;';
    efWrap.innerHTML = `
      <button id="cc-sprint" class="cc-btn">5-min Sprint</button>
      <button id="cc-stuck"  class="cc-btn">I’m stuck</button>
    `;
  }

  // styles
  const style = document.createElement('style');
  style.textContent = `
    @keyframes gentle-bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-10px)} }
    #coding-companion:hover { transform: scale(1.08) !important; }
    .cc-chip{background:#fff;color:#111;border:none;border-radius:10px;padding:6px 10px;cursor:pointer;font-size:12px}
    .cc-small{font-size:11px;opacity:.8;margin-top:6px}
    .cc-link{color:#9ad; text-decoration:underline; cursor:pointer; font-size:12px; margin-left:6px}
    .cc-btn{background:#fff;color:#111;border:none;border-radius:10px;padding:8px 10px;cursor:pointer;font-size:12px}
  `;
  document.head.appendChild(style);

  bubble.appendChild(header);
  bubble.appendChild(msgWrap);
  bubble.appendChild(coachWrap);
  bubble.appendChild(whyWrap);
  if (efMode) bubble.appendChild(efWrap);

  // analyze on sprite click — only swap the emoji span, never innerHTML
  sprite.addEventListener('click', (e) => {
    if (e.shiftKey) { resetPos('cc-bubble-pos'); bubble.style.bottom='90px'; bubble.style.right='20px'; bubble.style.top='auto'; bubble.style.left='auto'; }
    face.textContent = '🤔';
    msgWrap.textContent = efMode ? 'Quick check…' : 'Analyzing recent commits…';
    coachWrap.style.display = 'none'; whyWrap.style.display = 'none'; bubble.style.display = 'block';

    setTimeout(() => {
      chrome.runtime.sendMessage({ type: 'ANALYZE_CURRENT_REPO', url: window.location.href }, (resp) => {
        if (!resp) { face.textContent='👀'; msgWrap.textContent='No response from helper. Try reloading the extension.'; return; }
        const moodToEmoji = { encouraging:'😊', celebrating:'🎉', excited:'🤩', thinking:'🤔', nudging:'👀' };
        face.textContent = moodToEmoji[resp.mood] || '🧙‍♂️';
        msgWrap.textContent = resp.text || (efMode ? 'Let’s do a tiny step.' : 'All set.');
        coachWrap.innerHTML = ''; coachWrap.appendChild(buildCoach(getRepoScopeFromUrl()));
        if (resp.showCoach) coachWrap.style.display = 'block';
        if (resp.why) {
          whyWrap.innerHTML = `<span class="cc-link" id="cc-why-toggle">Why this?</span><span id="cc-why-text" style="display:none;"> ${escapeHtml(resp.why)}</span>`;
          whyWrap.style.display = 'block';
          const tgl = whyWrap.querySelector('#cc-why-toggle');
          const txt = whyWrap.querySelector('#cc-why-text');
          tgl.addEventListener('click', ()=> { txt.style.display = (txt.style.display==='inline') ? 'none':'inline'; });
        } else { whyWrap.style.display = 'none'; }
        setTimeout(()=>{ face.textContent='🧙‍♂️'; }, 4000);
      });
    }, 200);
  });

  // EF actions
  if (efMode) {
    const sprintBtn = bubble.querySelector('#cc-sprint');
    const stuckBtn  = bubble.querySelector('#cc-stuck');
    sprintBtn?.addEventListener('click', () => startSprint(sprite, face, msgWrap));
    stuckBtn?.addEventListener('click', () => showStuck(msgWrap, coachWrap, getRepoScopeFromUrl()));
  }

  // enable dragging
  dragEnable(sprite, 'cc-sprite-pos');
  dragEnable(bubble, 'cc-bubble-pos', header);

  document.body.appendChild(sprite);
  document.body.appendChild(bubble);
}

// ---- drag util ----
function dragEnable(el, storageKey, handle) {
  let dragging=false, dx=0, dy=0;
  const target = handle || el;
  const onStart = (x,y) => {
    const r = el.getBoundingClientRect();
    el.style.top=r.top+'px'; el.style.left=r.left+'px'; el.style.bottom='auto'; el.style.right='auto';
    dx=x-r.left; dy=y-r.top; dragging=true; (handle||el).style.cursor='grabbing';
  };
  const onMove = (x,y) => {
    if (!dragging) return;
    const left = Math.max(8, Math.min(window.innerWidth-40, x - dx));
    const top  = Math.max(8, Math.min(window.innerHeight-40, y - dy));
    el.style.left = left+'px'; el.style.top = top+'px';
  };
  const onEnd = () => {
    if (!dragging) return;
    dragging=false; (handle||el).style.cursor='grab';
    const r = el.getBoundingClientRect();
    savePos(storageKey, { top: Math.round(r.top), left: Math.round(r.left) });
  };
  target.addEventListener('pointerdown', e=>{ e.preventDefault(); onStart(e.clientX,e.clientY); });
  window.addEventListener('pointermove', e=> onMove(e.clientX,e.clientY));
  window.addEventListener('pointerup', onEnd);
  target.addEventListener('mousedown', e=>{ e.preventDefault(); onStart(e.clientX,e.clientY); });
  window.addEventListener('mousemove', e=> onMove(e.clientX,e.clientY));
  window.addEventListener('mouseup', onEnd);
  target.addEventListener('touchstart', e=>{ const t=e.touches[0]; if(!t) return; onStart(t.clientX,t.clientY); }, {passive:false});
  window.addEventListener('touchmove', e=>{ const t=e.touches?.[0]; if(!t) return; onMove(t.clientX,t.clientY); }, {passive:false});
  window.addEventListener('touchend', onEnd);
}

// ---- EF features ----
function startSprint(sprite, face, msgWrap) {
  // rebuild badge if user clicked sprite earlier
  const badge = ensureBadge(sprite);

  // (Re)start the sprint fresh
  if (sprintTimer) clearInterval(sprintTimer);
  sprintSecs = 5 * 60;
  face.textContent = '💪';
  badge.style.display = 'flex';
  updateBadge(badge);

  sprintTimer = setInterval(() => {
    sprintSecs--;
    updateBadge(badge);
    if (sprintSecs <= 0) {
      stopSprint();
      face.textContent = '🎉';
      msgWrap.textContent = "Sprint complete. Make a tiny commit (templates below).";
      setTimeout(()=> face.textContent='🧙‍♂️', 4000);
    }
  }, 1000);
}

function updateBadge(badge) {
  const m = Math.floor(sprintSecs/60), s = sprintSecs%60;
  badge.textContent = `${m}:${s.toString().padStart(2,'0')}`;
}

function showStuck(msgWrap, coachWrap, scope) {
  const ideas = [
    "Add one sentence to README about setup or purpose.",
    "Rename one vague variable to something clearer.",
    "Write one TODO comment above a tricky block.",
    "Add a docstring/JSDoc to one function.",
    "Run formatter on one file and commit."
  ].sort(()=>Math.random()-0.5).slice(0,3);
  msgWrap.innerHTML = `<div>Pick one 1-minute action:</div>
    <ul style="margin:6px 0 0 16px">${ideas.map(i=>`<li>${escapeHtml(i)}</li>`).join('')}</ul>`;
  coachWrap.style.display = 'block';
}

function buildCoach(scope){
  const wrap = document.createElement('div');
  wrap.innerHTML = `
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="cc-chip" data-template="feat(${scope}): ">feat(${scope}): …</button>
      <button class="cc-chip" data-template="fix(${scope}): ">fix(${scope}): …</button>
      <button class="cc-chip" data-template="docs(${scope}): ">docs(${scope}): …</button>
      <button class="cc-chip" data-template="refactor(${scope}): ">refactor(${scope}): …</button>
    </div>
    <div class="cc-small">Click a chip to copy a Conventional Commit starter to your clipboard.</div>
  `;
  wrap.querySelectorAll('[data-template]').forEach(btn=>{
    const label = btn.textContent;
    btn.addEventListener('click', async (e)=>{
      const text = e.currentTarget.getAttribute('data-template');
      try { await navigator.clipboard.writeText(text); e.currentTarget.textContent = 'Copied ✓'; setTimeout(()=>{ e.currentTarget.textContent = label; }, 1200); }
      catch { prompt('Copy this commit message start:', text); }
    });
  });
  return wrap;
}

// popup → Analyze
chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type === 'TRIGGER_ANALYZE_FROM_POPUP') {
    document.getElementById('coding-companion')?.click();
  }
});
