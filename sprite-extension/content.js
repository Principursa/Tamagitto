// content.js — v5: close button, "Why this?", coach auto-expand, DRAG to reposition (with persistence)
console.log("[CC] content.js v5 loaded");

if (window.location.hostname === 'github.com') {
  createFloatingSprite();
}

function getRepoScopeFromUrl() {
  const m = window.location.href.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  return m ? m[2].toLowerCase() : "repo";
}

// --- Drag helpers ---
function loadBubblePos() {
  try {
    const raw = localStorage.getItem('cc-bubble-pos');
    if (!raw) return null;
    const pos = JSON.parse(raw);
    // Validate minimal shape
    if (typeof pos.top === 'number' && typeof pos.left === 'number') return pos;
  } catch {}
  return null;
}
function saveBubblePos(pos) {
  try { localStorage.setItem('cc-bubble-pos', JSON.stringify(pos)); } catch {}
}

function createFloatingSprite() {
  const scope = getRepoScopeFromUrl();

  // Sprite (still bottom-right)
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

  // Bubble (we’ll position with top/left to support drag)
  const bubble = document.createElement('div');
  bubble.id = 'cc-bubble';
  const startPos = loadBubblePos();
  bubble.style.cssText = `
    position: fixed; ${startPos ? `top:${startPos.top}px; left:${startPos.left}px;` : `bottom: 90px; right: 20px;`}
    max-width: 320px; background: #111; color: #fff; padding: 12px 14px; border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25); font-size: 13px; line-height: 1.35; z-index: 2147483647;
  `;

  // Drag handle (thin bar at top of bubble)
  const dragHandle = document.createElement('div');
  dragHandle.id = 'cc-drag';
  dragHandle.title = 'Drag to move';
  dragHandle.style.cssText = `
    position: relative; height: 8px; margin: -6px -8px 6px -8px; cursor: grab;
    border-top-left-radius: 10px; border-top-right-radius: 10px;
    background: linear-gradient(90deg, rgba(255,255,255,.12), rgba(255,255,255,.06));
  `;

  // Close button
  const closeBtn = document.createElement('button');
  closeBtn.setAttribute('aria-label', 'Close helper');
  closeBtn.textContent = '×';
  closeBtn.style.cssText = `
    position: absolute; top: 6px; right: 8px; width: 20px; height: 20px;
    background: transparent; color: #bbb; border: none; font-size: 16px; cursor: pointer;
  `;
  closeBtn.addEventListener('click', ()=> { bubble.style.display = 'none'; });

  // Message, Coach, Why
  const msgWrap = document.createElement('div');
  msgWrap.id = 'cc-message';
  msgWrap.textContent = 'Hi! I can analyze this repo.';

  const coachWrap = document.createElement('div');
  coachWrap.id = 'cc-coach';
  coachWrap.style.cssText = `margin-top: 8px; display: none;`;

  const whyWrap = document.createElement('div');
  whyWrap.id = 'cc-why';
  whyWrap.style.cssText = `margin-top: 6px; font-size: 12px; color: #aaa; display: none;`;

  bubble.appendChild(dragHandle);
  bubble.appendChild(closeBtn);
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

  // Sprite click → analyze
  sprite.addEventListener('click', () => {
    sprite.innerHTML = '🤔';
    msgWrap.textContent = 'Analyzing recent commits…';
    coachWrap.style.display = 'none';
    whyWrap.style.display = 'none';
    bubble.style.display = 'block';

    setTimeout(() => {
      chrome.runtime.sendMessage(
        { type: 'ANALYZE_CURRENT_REPO', url: window.location.href },
        (resp) => {
          if (!resp) {
            sprite.innerHTML = '👀';
            msgWrap.textContent = 'No response from helper. Try reloading the extension.';
            return;
          }
          const moodToEmoji = { encouraging: '😊', celebrating: '🎉', excited: '🤩', thinking: '🤔', nudging: '👀' };
          sprite.innerHTML = moodToEmoji[resp.mood] || '🧙‍♂️';
          msgWrap.textContent = resp.text || 'All set.';

          // Coach section
          coachWrap.innerHTML = '';
          coachWrap.appendChild(buildCoach(scope));
          if (resp.showCoach) coachWrap.style.display = 'block';

          // Why this?
          if (resp.why) {
            whyWrap.innerHTML = `<span class="cc-link" id="cc-why-toggle">Why this?</span><span id="cc-why-text" style="display:none;"> ${escapeHtml(resp.why)}</span>`;
            whyWrap.style.display = 'block';
            const tgl = whyWrap.querySelector('#cc-why-toggle');
            const txt = whyWrap.querySelector('#cc-why-text');
            tgl.addEventListener('click', ()=> {
              const vis = txt.style.display === 'inline';
              txt.style.display = vis ? 'none' : 'inline';
            });
          } else {
            whyWrap.style.display = 'none';
          }

          setTimeout(() => { sprite.innerHTML = '🧙‍♂️'; }, 4000);
        }
      );
    }, 300);
  });

  // Drag logic (pointer events work for mouse + touch)
  let drag = null;
  dragHandle.addEventListener('pointerdown', (e) => {
    dragHandle.setPointerCapture(e.pointerId);
    const rect = bubble.getBoundingClientRect();
    drag = {
      dx: e.clientX - rect.left,
      dy: e.clientY - rect.top
    };
    dragHandle.style.cursor = 'grabbing';
    // Switch to top/left anchoring for consistent math
    bubble.style.top = rect.top + 'px';
    bubble.style.left = rect.left + 'px';
    bubble.style.bottom = 'auto';
    bubble.style.right = 'auto';
  });

  window.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const left = Math.max(8, Math.min(window.innerWidth - 40, e.clientX - drag.dx));
    const top  = Math.max(8, Math.min(window.innerHeight - 40, e.clientY - drag.dy));
    bubble.style.left = left + 'px';
    bubble.style.top  = top + 'px';
  });

  window.addEventListener('pointerup', () => {
    if (!drag) return;
    dragHandle.style.cursor = 'grab';
    drag = null;
    // Save position
    const rect = bubble.getBoundingClientRect();
    saveBubblePos({ top: Math.round(rect.top), left: Math.round(rect.left) });
  });

  document.body.appendChild(sprite);
  document.body.appendChild(bubble);
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
      try {
        await navigator.clipboard.writeText(text);
        e.currentTarget.textContent = 'Copied ✓';
        setTimeout(()=>{ e.currentTarget.textContent = label; }, 1200);
      } catch {
        prompt('Copy this commit message start:', text);
      }
    });
  });

  return wrap;
}

function escapeHtml(s=''){
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
