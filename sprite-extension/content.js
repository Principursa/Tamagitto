// content.js — v5.2: clamp position, easy reset (Shift+click sprite), robust drag
console.log("[CC] content.js v5.2 loaded");

if (window.location.hostname === 'github.com') {
  createFloatingSprite();
}

function getRepoScopeFromUrl() {
  const m = window.location.href.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  return m ? m[2].toLowerCase() : "repo";
}

// ---- position helpers ----
function clampPos(pos){
  const margin = 8;
  const maxLeft = Math.max(margin, window.innerWidth  - 40);
  const maxTop  = Math.max(margin, window.innerHeight - 40);
  return {
    left: Math.min(maxLeft, Math.max(margin, pos.left)),
    top:  Math.min(maxTop,  Math.max(margin, pos.top))
  };
}
function loadBubblePos() {
  try {
    const raw = localStorage.getItem('cc-bubble-pos');
    if (!raw) return null;
    const p = JSON.parse(raw);
    if (typeof p.top === 'number' && typeof p.left === 'number') {
      return clampPos(p);
    }
  } catch {}
  return null;
}
function saveBubblePos(pos) {
  try { localStorage.setItem('cc-bubble-pos', JSON.stringify(clampPos(pos))); } catch {}
}
function resetBubblePos() {
  try { localStorage.removeItem('cc-bubble-pos'); } catch {}
}

// ---- UI ----
function createFloatingSprite() {
  const scope = getRepoScopeFromUrl();

  const sprite = document.createElement('div');
  sprite.id = 'coding-companion';
  sprite.innerHTML = '🧙‍♂️';
  sprite.style.cssText = `
    position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px;
    background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 30px; cursor: pointer; z-index: 2147483647;
    animation: gentle-bounce 3s ease-in-out infinite;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3); transition: transform 0.2s ease;
  `;

  const bubble = document.createElement('div');
  bubble.id = 'cc-bubble';
  const startPos = loadBubblePos();
  bubble.style.cssText = `
    position: fixed; ${startPos ? `top:${startPos.top}px; left:${startPos.left}px;` : `bottom: 90px; right: 20px;`}
    max-width: 320px; background: #111; color: #fff; padding: 12px 14px; border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25); font-size: 13px; line-height: 1.35; z-index: 2147483647;
    -webkit-user-select: none; user-select: none; display: block;
  `;

  // Header (drag area)
  const header = document.createElement('div');
  header.id = 'cc-header';
  header.style.cssText = `
    display:flex; align-items:center; gap:8px; margin:-6px -8px 8px -8px; padding:6px 8px 0 8px;
    cursor: grab; background: linear-gradient(90deg, rgba(255,255,255,.10), rgba(255,255,255,.05));
    border-top-left-radius:10px; border-top-right-radius:10px; pointer-events:auto;
  `;
  const grip = document.createElement('div');
  grip.style.cssText = `width:36px; height:6px; border-radius:3px; background:rgba(255,255,255,.3); margin:2px 0; flex:0 0 auto;`;

  const closeBtn = document.createElement('button');
  closeBtn.setAttribute('aria-label', 'Close helper');
  closeBtn.textContent = '×';
  closeBtn.style.cssText = `
    margin-left:auto; width:20px; height:20px; background:transparent; color:#bbb;
    border:none; font-size:16px; cursor:pointer; flex:0 0 auto;
  `;
  closeBtn.addEventListener('click', ()=> { bubble.style.display = 'none'; });

  header.appendChild(grip);
  header.appendChild(closeBtn);

  const msgWrap   = document.createElement('div'); msgWrap.id = 'cc-message'; msgWrap.textContent = 'Hi! I can analyze this repo.';
  const coachWrap = document.createElement('div'); coachWrap.id = 'cc-coach'; coachWrap.style.cssText = `margin-top: 8px; display: none;`;
  const whyWrap   = document.createElement('div'); whyWrap.id   = 'cc-why';   whyWrap.style.cssText   = `margin-top: 6px; font-size: 12px; color: #aaa; display: none;`;

  bubble.appendChild(header);
  bubble.appendChild(msgWrap);
  bubble.appendChild(coachWrap);
  bubble.appendChild(whyWrap);

  // Styles
  const style = document.createElement('style');
  style.textContent = `
    @keyframes gentle-bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    #coding-companion:hover { transform: scale(1.08) !important; }
    .cc-chip{background:#fff;color:#111;border:none;border-radius:10px;padding:6px 10px;cursor:pointer;font-size:12px}
    .cc-small{font-size:11px;opacity:.8;margin-top:6px}
    .cc-link{color:#9ad; text-decoration:underline; cursor:pointer; font-size:12px; margin-left:6px}
  `;
  document.head.appendChild(style);

  // Shift+click sprite = reset position & show bubble
  sprite.addEventListener('click', (e) => {
    if (e.shiftKey) {
      resetBubblePos();
      bubble.style.bottom = '90px'; bubble.style.right = '20px';
      bubble.style.top = 'auto'; bubble.style.left = 'auto';
    }
    sprite.innerHTML = '🤔';
    msgWrap.textContent = 'Analyzing recent commits…';
    coachWrap.style.display = 'none';
    whyWrap.style.display = 'none';
    bubble.style.display = 'block';

    setTimeout(() => {
      chrome.runtime.sendMessage(
        { type: 'ANALYZE_CURRENT_REPO', url: window.location.href },
        (resp) => {
          if (!resp) { sprite.innerHTML = '👀'; msgWrap.textContent = 'No response from helper. Try reloading the extension.'; return; }
          const moodToEmoji = { encouraging: '😊', celebrating: '🎉', excited: '🤩', thinking: '🤔', nudging: '👀' };
          sprite.innerHTML = moodToEmoji[resp.mood] || '🧙‍♂️';
          msgWrap.textContent = resp.text || 'All set.';
          coachWrap.innerHTML = ''; coachWrap.appendChild(buildCoach(scope));
          if (resp.showCoach) coachWrap.style.display = 'block';
          if (resp.why) {
            whyWrap.innerHTML = `<span class="cc-link" id="cc-why-toggle">Why this?</span><span id="cc-why-text" style="display:none;"> ${escapeHtml(resp.why)}</span>`;
            whyWrap.style.display = 'block';
            const tgl = whyWrap.querySelector('#cc-why-toggle');
            const txt = whyWrap.querySelector('#cc-why-text');
            tgl.addEventListener('click', ()=> { txt.style.display = (txt.style.display==='inline') ? 'none':'inline'; });
          } else { whyWrap.style.display = 'none'; }
          setTimeout(() => { sprite.innerHTML = '🧙‍♂️'; }, 4000);
        }
      );
    }, 300);
  });

  // Dragging (header area)
  let dragging = false, offsetX = 0, offsetY = 0;
  function startDrag(x, y) {
    const r = bubble.getBoundingClientRect();
    bubble.style.top  = r.top + 'px';
    bubble.style.left = r.left + 'px';
    bubble.style.bottom = 'auto';
    bubble.style.right  = 'auto';
    offsetX = x - r.left;
    offsetY = y - r.top;
    dragging = true;
    header.style.cursor = 'grabbing';
  }
  function moveDrag(x, y) {
    if (!dragging) return;
    const left = Math.max(8, Math.min(window.innerWidth  - 40, x - offsetX));
    const top  = Math.max(8, Math.min(window.innerHeight - 40, y - offsetY));
    bubble.style.left = left + 'px';
    bubble.style.top  = top + 'px';
  }
  function endDrag() {
    if (!dragging) return;
    dragging = false;
    header.style.cursor = 'grab';
    const r = bubble.getBoundingClientRect();
    saveBubblePos({ top: Math.round(r.top), left: Math.round(r.left) });
  }

  header.addEventListener('pointerdown', (e)=>{ e.preventDefault(); header.setPointerCapture?.(e.pointerId); startDrag(e.clientX, e.clientY); });
  window.addEventListener('pointermove', (e)=> moveDrag(e.clientX, e.clientY));
  window.addEventListener('pointerup', endDrag);

  // Mouse/touch fallbacks
  header.addEventListener('mousedown',  (e)=>{ e.preventDefault(); startDrag(e.clientX, e.clientY); });
  window.addEventListener('mousemove',  (e)=> moveDrag(e.clientX, e.clientY));
  window.addEventListener('mouseup',    endDrag);
  header.addEventListener('touchstart', (e)=>{ const t=e.touches[0]; if (!t) return; startDrag(t.clientX, t.clientY); }, {passive:false});
  window.addEventListener('touchmove',  (e)=>{ const t=e.touches?.[0]; if (!t||!dragging) return; moveDrag(t.clientX, t.clientY); }, {passive:false});
  window.addEventListener('touchend',   endDrag);

  document.body.appendChild(sprite);
  document.body.appendChild(bubble);

  // If a saved position is off-screen due to resize, snap it back on first render
  if (startPos) {
    const r = bubble.getBoundingClientRect();
    if (r.right < 0 || r.bottom < 0 || r.left > window.innerWidth || r.top > window.innerHeight) {
      resetBubblePos();
      bubble.style.bottom = '90px'; bubble.style.right = '20px';
      bubble.style.top = 'auto'; bubble.style.left = 'auto';
    }
  }
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

function escapeHtml(s=''){ return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
