// content.js — v3 with "Coach me"
console.log("[CC] content.js v3 loaded");

if (window.location.hostname === 'github.com') {
  createFloatingSprite();
}

function getRepoScopeFromUrl() {
  const m = window.location.href.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  return m ? m[2].toLowerCase() : "repo";
}

function createFloatingSprite() {
  const scope = getRepoScopeFromUrl();

  // Sprite
  const sprite = document.createElement('div');
  sprite.id = 'coding-companion';
  sprite.innerHTML = '🧙‍♂️';
  sprite.style.cssText = `
    position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px;
    background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 30px; cursor: pointer; z-index: 10000;
    animation: gentle-bounce 3s ease-in-out infinite;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3); transition: transform 0.2s ease;
  `;

  // Bubble
  const bubble = document.createElement('div');
  bubble.id = 'cc-bubble';
  bubble.style.cssText = `
    position: fixed; bottom: 90px; right: 20px; max-width: 300px;
    background: #111; color: #fff; padding: 10px 12px; border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25); font-size: 13px; line-height: 1.3; z-index: 10000;
  `;
  bubble.textContent = 'Hi! I can analyze this repo.';

  // Coach me container
  const coach = document.createElement('div');
  coach.id = 'cc-coach';
  coach.style.cssText = `margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap;`;
  coach.innerHTML = `
    <button data-cc="coach" style="background:#fff;color:#111;border:none;border-radius:10px;padding:6px 10px;cursor:pointer;font-size:12px">
      Coach me
    </button>
  `;
  bubble.appendChild(coach);

  // Styles
  const style = document.createElement('style');
  style.textContent = `
    @keyframes gentle-bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    #coding-companion:hover { transform: scale(1.08) !important; }
    .cc-chip{background:#fff;color:#111;border:none;border-radius:10px;padding:6px 10px;cursor:pointer;font-size:12px}
    .cc-small{font-size:11px;opacity:.8;margin-top:6px}
  `;
  document.head.appendChild(style);

  // Sprite click → analyze
  sprite.addEventListener('click', () => {
    sprite.innerHTML = '🤔';
    bubble.firstChild?.nodeType === 3 ? bubble.firstChild.nodeValue = 'Analyzing recent commits…' : (bubble.textContent = 'Analyzing recent commits…');

    setTimeout(() => {
      chrome.runtime.sendMessage(
        { type: 'ANALYZE_CURRENT_REPO', url: window.location.href },
        (resp) => {
          if (!resp) {
            sprite.innerHTML = '👀';
            bubble.textContent = 'No response from helper. Try reloading the extension.';
            return;
          }
          const moodToEmoji = { encouraging: '😊', celebrating: '🎉', excited: '🤩', thinking: '🤔', nudging: '👀' };
          sprite.innerHTML = moodToEmoji[resp.mood] || '🧙‍♂️';
          // Keep existing nodes, just update first text
          bubble.innerHTML = `<div>${resp.text || 'All set.'}</div>`;
          bubble.appendChild(buildCoach(scope));
          setTimeout(() => { sprite.innerHTML = '🧙‍♂️'; }, 4000);
        }
      );
    }, 300);
  });

  document.body.appendChild(sprite);
  document.body.appendChild(bubble);
}

function buildCoach(scope){
  // Buttons with commit message templates; click copies to clipboard
  const wrap = document.createElement('div');
  wrap.style.marginTop = '8px';
  wrap.innerHTML = `
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="cc-chip" data-template="feat(${scope}): ">
        feat(${scope}): …
      </button>
      <button class="cc-chip" data-template="fix(${scope}): ">
        fix(${scope}): …
      </button>
      <button class="cc-chip" data-template="docs(${scope}): ">
        docs(${scope}): …
      </button>
      <button class="cc-chip" data-template="refactor(${scope}): ">
        refactor(${scope}): …
      </button>
    </div>
    <div class="cc-small">Click a chip to copy a Conventional Commit starter to your clipboard.</div>
  `;

  wrap.querySelectorAll('[data-template]').forEach(btn=>{
    btn.addEventListener('click', async (e)=>{
      const text = e.currentTarget.getAttribute('data-template');
      try {
        await navigator.clipboard.writeText(text);
        e.currentTarget.textContent = 'Copied ✓';
        setTimeout(()=>{ e.currentTarget.textContent = text.trim(); }, 1200);
      } catch (err){
        // Fallback if clipboard not allowed
        prompt('Copy this commit message start:', text);
      }
    });
  });

  return wrap;
}
