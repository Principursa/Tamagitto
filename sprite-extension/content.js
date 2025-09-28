// content.js - v8.0: AI learning integration + existing features
console.log("[CC] content.js v8.0 loaded - AI Learning Edition");

let ccState = { efMode: false, mounted: false };
let sprintTimer = null;
let sprintSecs = 0;
let currentAnalysisData = null;

// AI Feedback System
class AIFeedbackTracker {
  constructor() {
    this.interactionCount = 0;
  }

  async recordFeedback(type, data) {
    this.interactionCount++;
    
    chrome.runtime.sendMessage({
      type: 'RECORD_USER_FEEDBACK',
      mood: data.mood || '',
      reaction: data.reaction || 'neutral',
      context: { type, ...data }
    });

    if (this.interactionCount < 15 && Math.random() < 0.3) {
      this.showLearningIndicator();
    }
  }

  showLearningIndicator() {
    const sprite = document.getElementById('coding-companion');
    if (!sprite) return;

    const indicator = document.createElement('div');
    indicator.style.cssText = 'position: absolute; top: -8px; left: -8px; font-size: 12px; background: linear-gradient(45deg, #667eea, #764ba2); color: white; border-radius: 10px; padding: 2px 6px; animation: pulse 2s ease-in-out; pointer-events: none; z-index: 2147483648;';
    indicator.textContent = '🧠 Learning';
    
    sprite.style.position = 'relative';
    sprite.appendChild(indicator);
    
    setTimeout(() => {
      if (indicator.parentNode) {
        indicator.parentNode.removeChild(indicator);
      }
    }, 2000);
  }
}

const aiFeedback = new AIFeedbackTracker();

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
  const sprite = document.getElementById('coding-companion');
  const bubble = document.getElementById('cc-bubble');
  if (sprite) sprite.remove();
  if (bubble) bubble.remove();
  stopSprint();
  ccState.mounted = false;
}

function getRepoScopeFromUrl() {
  const m = window.location.href.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  return m ? m[2].toLowerCase() : "repo";
}

function clampPos(pos){
  const margin = 8;
  const maxLeft = Math.max(margin, window.innerWidth - 40);
  const maxTop = Math.max(margin, window.innerHeight - 40);
  return { left: Math.min(maxLeft, Math.max(margin, pos.left)), top: Math.min(maxTop, Math.max(margin, pos.top)) };
}

function loadPos(key) { 
  try { 
    const raw = localStorage.getItem(key); 
    if (!raw) return null; 
    const p = JSON.parse(raw); 
    if (typeof p.left === 'number' && typeof p.top === 'number') return clampPos(p); 
  } catch(e) {} 
  return null; 
}

function savePos(key, pos){ 
  try{ 
    localStorage.setItem(key, JSON.stringify(clampPos(pos))); 
  } catch(e) {} 
}

function resetPos(key){ 
  try{ 
    localStorage.removeItem(key); 
  } catch(e) {} 
}

function escapeHtml(s) {
  if (!s) return '';
  return s.replace(/[&<>"']/g, function(c) {
    return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
  });
}

function ensureBadge(sprite){
  let b = document.getElementById('cc-badge');
  if (!b) {
    b = document.createElement('div');
    b.id = 'cc-badge';
    b.style.cssText = 'position:absolute; bottom:-2px; right:-2px; min-width:18px; height:18px; padding:0 4px; background:#111; color:#fff; border-radius:9px; font-size:11px; display:none; align-items:center; justify-content:center; box-shadow: 0 2px 8px rgba(0,0,0,.3);';
    sprite.appendChild(b);
  }
  return b;
}

function stopSprint(){
  if (sprintTimer) { 
    clearInterval(sprintTimer); 
    sprintTimer = null; 
  }
  
  if (sprintSecs > 0) {
    const wasSuccess = sprintSecs <= 0;
    const duration = currentAnalysisData?.predictions?.recommendedSprintDuration || 5;
    
    chrome.runtime.sendMessage({
      type: 'RECORD_SPRINT_RESULT',
      duration: duration,
      success: wasSuccess
    });
    
    aiFeedback.recordFeedback('sprint_ended', {
      success: wasSuccess,
      duration: duration
    });
  }
  
  sprintSecs = 0;
  const badge = document.getElementById('cc-badge');
  if (badge) badge.style.display = 'none';
}

function createFloatingSprite(efMode) {
  // Create sprite
  const sprite = document.createElement('div');
  sprite.id = 'coding-companion';
  const spriteStart = loadPos('cc-sprite-pos');
  
  if (spriteStart) {
    sprite.style.cssText = 'position: fixed; top:' + spriteStart.top + 'px; left:' + spriteStart.left + 'px; width: 60px; height: 60px; background: linear-gradient(45deg,#4facfe 0%,#00f2fe 100%); border-radius: 50%; display:flex; align-items:center; justify-content:center; font-size: 30px; cursor: grab; z-index: 2147483647; animation: gentle-bounce 3s ease-in-out infinite; box-shadow: 0 4px 20px rgba(0,0,0,0.3); user-select:none;';
  } else {
    sprite.style.cssText = 'position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background: linear-gradient(45deg,#4facfe 0%,#00f2fe 100%); border-radius: 50%; display:flex; align-items:center; justify-content:center; font-size: 30px; cursor: grab; z-index: 2147483647; animation: gentle-bounce 3s ease-in-out infinite; box-shadow: 0 4px 20px rgba(0,0,0,0.3); user-select:none;';
  }
  
  const face = document.createElement('span');
  face.id = 'cc-face';
  face.textContent = '🧙‍♂️';
  sprite.appendChild(face);

  const badge = ensureBadge(sprite);

  // Create bubble
  const bubble = document.createElement('div');
  bubble.id = 'cc-bubble';
  const bubbleStart = loadPos('cc-bubble-pos');
  
  if (bubbleStart) {
    bubble.style.cssText = 'position: fixed; top:' + bubbleStart.top + 'px; left:' + bubbleStart.left + 'px; max-width: 340px; background:#111; color:#fff; padding:12px 14px; border-radius:12px; box-shadow: 0 8px 24px rgba(0,0,0,.25); font-size:13px; line-height:1.35; z-index:2147483647; user-select:none;';
  } else {
    bubble.style.cssText = 'position: fixed; bottom: 90px; right: 20px; max-width: 340px; background:#111; color:#fff; padding:12px 14px; border-radius:12px; box-shadow: 0 8px 24px rgba(0,0,0,.25); font-size:13px; line-height:1.35; z-index:2147483647; user-select:none;';
  }

  // Bubble content
  const header = document.createElement('div');
  header.style.cssText = 'display:flex; align-items:center; gap:8px; margin:-6px -8px 8px -8px; padding:6px 8px 0 8px; cursor: grab; background: linear-gradient(90deg, rgba(255,255,255,.10), rgba(255,255,255,.05)); border-top-left-radius:10px; border-top-right-radius:10px;';
  
  const grip = document.createElement('div'); 
  grip.style.cssText = 'width:36px; height:6px; border-radius:3px; background:rgba(255,255,255,.3); margin:2px 0;';
  
  const closeBtn = document.createElement('button'); 
  closeBtn.textContent = '×'; 
  closeBtn.setAttribute('aria-label','Close');
  closeBtn.style.cssText = 'margin-left:auto; width:20px; height:20px; background:transparent; color:#bbb; border:0; font-size:16px; cursor:pointer;';
  closeBtn.addEventListener('click', function() {
    bubble.style.display = 'none';
    aiFeedback.recordFeedback('bubble_closed', { method: 'close_button' });
  });
  
  header.appendChild(grip); 
  header.appendChild(closeBtn);

  const msgWrap = document.createElement('div'); 
  msgWrap.id = 'cc-message';
  msgWrap.textContent = efMode ? 'Ready for a smart sprint?' : 'Hi! I can analyze this repo with AI insights.';
  
  const aiWrap = document.createElement('div');
  aiWrap.id = 'cc-ai-insights';
  aiWrap.style.cssText = 'margin-top:8px; display:none;';
  
  const coachWrap = document.createElement('div'); 
  coachWrap.id = 'cc-coach'; 
  coachWrap.style.cssText = 'margin-top:8px; display:none;';
  
  const whyWrap = document.createElement('div'); 
  whyWrap.id = 'cc-why';   
  whyWrap.style.cssText = 'margin-top:6px; font-size:12px; color:#aaa; display:none;';

  const efWrap = document.createElement('div');
  if (efMode) {
    efWrap.style.cssText = 'margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;';
    efWrap.innerHTML = '<button id="cc-sprint" class="cc-btn">Smart Sprint</button><button id="cc-stuck" class="cc-btn">I\'m stuck</button>';
  }

  const feedbackWrap = document.createElement('div');
  feedbackWrap.id = 'cc-feedback';
  feedbackWrap.style.cssText = 'margin-top:8px; display:none;';

  // Add styles
  const style = document.createElement('style');
  style.textContent = '@keyframes gentle-bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-10px)} } @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } } #coding-companion:hover { transform: scale(1.08) !important; } .cc-chip{background:#fff;color:#111;border:none;border-radius:10px;padding:6px 10px;cursor:pointer;font-size:12px} .cc-small{font-size:11px;opacity:.8;margin-top:6px} .cc-link{color:#9ad; text-decoration:underline; cursor:pointer; font-size:12px; margin-left:6px} .cc-btn{background:#fff;color:#111;border:none;border-radius:10px;padding:8px 10px;cursor:pointer;font-size:12px} .cc-ai-badge{background:linear-gradient(45deg,#667eea,#764ba2);color:#fff;font-size:10px;padding:2px 6px;border-radius:8px;margin-left:6px;} .cc-feedback-btn{background:#333;color:#fff;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px;margin-right:4px;} .cc-feedback-btn:hover{background:#555;} .cc-feedback-btn.positive{background:#28a745;} .cc-feedback-btn.negative{background:#dc3545;}';
  document.head.appendChild(style);

  bubble.appendChild(header);
  bubble.appendChild(msgWrap);
  bubble.appendChild(aiWrap);
  bubble.appendChild(coachWrap);
  bubble.appendChild(whyWrap);
  if (efMode) bubble.appendChild(efWrap);
  bubble.appendChild(feedbackWrap);

  // Sprite click handler with AI integration
  sprite.addEventListener('click', function(e) {
    if (e.shiftKey) { 
      resetPos('cc-bubble-pos'); 
      bubble.style.bottom = '90px'; 
      bubble.style.right = '20px'; 
      bubble.style.top = 'auto'; 
      bubble.style.left = 'auto'; 
      return;
    }
    
    face.textContent = '🤔';
    msgWrap.textContent = 'Analyzing with AI patterns...';
    aiWrap.style.display = 'none';
    coachWrap.style.display = 'none'; 
    whyWrap.style.display = 'none'; 
    feedbackWrap.style.display = 'none';
    bubble.style.display = 'block';

    aiFeedback.recordFeedback('analysis_requested', {});

    setTimeout(function() {
      chrome.runtime.sendMessage({ type: 'ANALYZE_CURRENT_REPO', url: window.location.href }, function(resp) {
        if (!resp) { 
          face.textContent = '💀'; 
          msgWrap.textContent = 'No response from AI engine. Try reloading the extension.'; 
          return; 
        }
        
        currentAnalysisData = resp;
        
        const moodToEmoji = { 
          encouraging: '😊', 
          celebrating: '🎉', 
          excited: '🤩', 
          thinking: '🤔', 
          nudging: '👀' 
        };
        
        face.textContent = moodToEmoji[resp.mood] || '🧙‍♂️';
        msgWrap.textContent = resp.text || 'All set.';
        
        // Show AI insights
        if (resp.predictions && Object.keys(resp.predictions).length > 0) {
          displayAIInsights(aiWrap, resp.predictions, resp.confidence);
        }
        
        // Update EF controls with AI data
        if (efMode) {
          updateEFControls(efWrap, resp);
        }
        
        // Show why explanation
        if (resp.why) {
          const aiIndicator = resp.caseType === 'AI_PERSONALIZED' ? '<span class="cc-ai-badge">AI</span>' : '';
          whyWrap.innerHTML = '<span class="cc-link" id="cc-why-toggle">Why this?</span>' + aiIndicator + '<span id="cc-why-text" style="display:none;"> ' + escapeHtml(resp.why) + '</span>';
          whyWrap.style.display = 'block';
          
          const tgl = whyWrap.querySelector('#cc-why-toggle');
          const txt = whyWrap.querySelector('#cc-why-text');
          tgl.addEventListener('click', function() { 
            txt.style.display = (txt.style.display === 'inline') ? 'none' : 'inline'; 
            aiFeedback.recordFeedback('why_clicked', { caseType: resp.caseType });
          });
        } else { 
          whyWrap.style.display = 'none'; 
        }
        
        // Show feedback buttons
        showFeedbackButtons(feedbackWrap, resp);
        
        setTimeout(function() { face.textContent = '🧙‍♂️'; }, 4000);
        
        aiFeedback.recordFeedback('analysis_completed', {
          caseType: resp.caseType,
          mood: resp.mood,
          hasAI: resp.caseType === 'AI_PERSONALIZED'
        });
      });
    }, 200);
  });

  // EF button handlers
  if (efMode) {
    const sprintBtn = bubble.querySelector('#cc-sprint');
    const stuckBtn = bubble.querySelector('#cc-stuck');
    
    if (sprintBtn) {
      sprintBtn.addEventListener('click', function() {
        const duration = currentAnalysisData?.predictions?.recommendedSprintDuration || 5;
        startSprint(sprite, face, msgWrap, duration);
        aiFeedback.recordFeedback('sprint_started', { 
          duration, 
          aiRecommended: currentAnalysisData?.caseType === 'AI_PERSONALIZED' 
        });
      });
    }
    
    if (stuckBtn) {
      stuckBtn.addEventListener('click', function() {
        showStuck(msgWrap, coachWrap, getRepoScopeFromUrl());
        aiFeedback.recordFeedback('stuck_help_used', {});
      });
    }
  }

  document.body.appendChild(sprite);
  document.body.appendChild(bubble);
}

function displayAIInsights(container, predictions, confidence) {
  if (!predictions || Object.keys(predictions).length === 0) return;
  
  const overallConfidence = confidence.overall || 0;
  const confidencePercent = Math.round(overallConfidence * 100);
  
  let html = '<div style="background:rgba(255,255,255,0.1); padding:8px; border-radius:6px; margin-bottom:8px;">';
  
  if (confidencePercent < 30) {
    html += '<div style="font-size:11px; color:#ffc107;">🧠 AI Learning Mode: Building your pattern profile...</div>';
  } else {
    html += '<div style="font-size:11px; color:#28a745;">✨ AI Insights (' + confidencePercent + '% confidence):</div>';
    
    if (predictions.currentProductivity) {
      const score = Math.round(predictions.currentProductivity * 100);
      html += '<div style="font-size:11px; margin-top:4px;">📈 Current productivity: ' + score + '%</div>';
    }
    
    if (predictions.bestUpcomingHour) {
      html += '<div style="font-size:11px; margin-top:4px;">⏰ Peak time: ' + predictions.bestUpcomingHour.hour + ':00</div>';
    }
    
    if (predictions.recommendedSprintDuration && predictions.recommendedSprintDuration !== 5) {
      html += '<div style="font-size:11px; margin-top:4px;">🎯 Optimal sprint: ' + predictions.recommendedSprintDuration + ' min</div>';
    }
  }
  
  html += '</div>';
  container.innerHTML = html;
  container.style.display = 'block';
}

function updateEFControls(container, analysisData) {
  const sprintBtn = container.querySelector('#cc-sprint');
  if (sprintBtn && analysisData.predictions?.recommendedSprintDuration) {
    const duration = analysisData.predictions.recommendedSprintDuration;
    sprintBtn.textContent = duration + '-min Sprint 🧠';
  }
}

function showFeedbackButtons(container, analysisData) {
  container.innerHTML = '<div style="font-size:11px; color:#aaa; margin-bottom:4px;">Was this helpful?</div><div><button class="cc-feedback-btn positive" data-reaction="positive">👍 Yes</button><button class="cc-feedback-btn negative" data-reaction="negative">👎 No</button><button class="cc-feedback-btn" data-reaction="neutral">😐 Okay</button></div>';
  
  container.querySelectorAll('.cc-feedback-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      const reaction = btn.dataset.reaction;
      aiFeedback.recordFeedback('feedback_given', {
        reaction,
        mood: analysisData.mood,
        caseType: analysisData.caseType
      });
      
      btn.textContent = reaction === 'positive' ? '✅ Thanks!' : 
                       reaction === 'negative' ? '📝 Noted' : '👌 Got it';
      btn.disabled = true;
      
      setTimeout(function() {
        container.style.display = 'none';
      }, 1500);
    });
  });
  
  container.style.display = 'block';
}

function startSprint(sprite, face, msgWrap, duration) {
  duration = duration || 5;
  const badge = ensureBadge(sprite);

  if (sprintTimer) clearInterval(sprintTimer);
  sprintSecs = duration * 60;
  face.textContent = '💪';
  badge.style.display = 'flex';
  updateBadge(badge);

  sprintTimer = setInterval(function() {
    sprintSecs--;
    updateBadge(badge);
    if (sprintSecs <= 0) {
      stopSprint();
      face.textContent = '🎉';
      msgWrap.textContent = duration + '-minute sprint complete! Make a tiny commit.';
      setTimeout(function() { face.textContent = '🧙‍♂️'; }, 4000);
      
      chrome.runtime.sendMessage({
        type: 'RECORD_SPRINT_RESULT',
        duration: duration,
        success: true
      });
    }
  }, 1000);
}

function updateBadge(badge) {
  const m = Math.floor(sprintSecs / 60);
  const s = sprintSecs % 60;
  badge.textContent = m + ':' + s.toString().padStart(2, '0');
}

function showStuck(msgWrap, coachWrap, scope) {
  const ideas = [
    "Add one sentence to README about setup or purpose.",
    "Rename one vague variable to something clearer.",
    "Write one TODO comment above a tricky block.",
    "Add a docstring/JSDoc to one function.",
    "Run formatter on one file and commit."
  ].sort(function() { return Math.random() - 0.5; }).slice(0, 3);
  
  msgWrap.innerHTML = '<div>Pick one 1-minute action:</div><ul style="margin:6px 0 0 16px">' + ideas.map(function(i) { return '<li>' + escapeHtml(i) + '</li>'; }).join('') + '</ul><div style="font-size:11px; color:#aaa; margin-top:6px;">🧠 AI will learn which actions work best for you</div>';
  coachWrap.style.display = 'block';
}

chrome.runtime.onMessage.addListener(function(msg) {
  if (msg && msg.type === 'TRIGGER_ANALYZE_FROM_POPUP') {
    const sprite = document.getElementById('coding-companion');
    if (sprite) sprite.click();
  }
});