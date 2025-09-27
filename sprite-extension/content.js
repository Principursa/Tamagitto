// content.js — inject sprite + on-click analysis via background service worker

if (window.location.hostname === 'github.com') {
  createFloatingSprite();
}

function createFloatingSprite() {
  // Sprite
  const sprite = document.createElement('div');
  sprite.id = 'coding-companion';
  sprite.innerHTML = '🧙‍♂️';
  sprite.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 60px;
    height: 60px;
    background: linear-gradient(45deg, #4facfe 0%, #00f2fe 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    cursor: pointer;
    z-index: 10000;
    animation: gentle-bounce 3s ease-in-out infinite;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    transition: transform 0.2s ease;
  `;

  // Bubble
  const bubble = document.createElement('div');
  bubble.id = 'cc-bubble';
  bubble.textContent = 'Hi! I can analyze this repo.';
  bubble.style.cssText = `
    position: fixed;
    bottom: 90px;
    right: 20px;
    max-width: 280px;
    background: #111;
    color: #fff;
    padding: 10px 12px;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    font-size: 13px;
    line-height: 1.3;
    z-index: 10000;
  `;

  // Gentle bounce keyframes
  const style = document.createElement('style');
  style.textContent = `
    @keyframes gentle-bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    #coding-companion:hover { transform: scale(1.08) !important; }
  `;
  document.head.appendChild(style);

  sprite.addEventListener('click', () => {
    // Visual "thinking"
    sprite.innerHTML = '🤔';
    bubble.textContent = 'Analyzing recent commits…';

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
        bubble.textContent = resp.text || 'All set.';
        // Reset face after a few seconds
        setTimeout(() => { sprite.innerHTML = '🧙‍♂️'; }, 4000);
      }
    );
  });

  document.body.appendChild(sprite);
  document.body.appendChild(bubble);
}
