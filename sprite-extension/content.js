// content.js – v8.1: fix sprint tick; keep sprite fixed; add buildCoach; EF + AI hooks
console.log("[CC] content.js v8.1 loaded");

let ccState = { efMode: false, mounted: false };
let sprintTimer = null;
let sprintSecs = 0;
let currentAnalysisData = null;

// ---------- AI Feedback System ----------
class AIFeedbackTracker {
  constructor(){ this.interactionCount = 0; }
  async recordFeedback(type, data = {}) {
    this.interactionCount++;
    chrome.runtime.sendMessage({
      type: 'RECORD_USER_FEEDBACK',
      mood: data.mood || '',
      reaction: data.reaction || 'neutral',
      context: { type, ...data }
    });
    // Lightweight "learning" flare (no layout changes)
    if (this.interactionCount < 15 && Math.random() < 0.3) this.showLearningIndicator();
  }
  showLearningIndicator() {
    const sprite = document.getElementById('coding-companion');
    if (!sprite) return;
    const indicator = document.createElement('div');
    indicator.style.cssText = 'position:absolute; top:-8px; left:-8px; font-size:12px; background:linear-gradient(45deg,#667eea,#764ba2); color:#fff; border-radius:10px; padding:2px 6px; animation:pulse 2s ease-in-out; pointer-events:none; z-index:2147483648;';
    indicator.textContent = '🧠 Learning';
    // DO NOT change sprite.position (keep fixed)
    sprite.appendChild(indicator);
    setTimeout(()=>indicator.remove(), 2000);
  }
}
const aiFeedback = new AIFeedbackTracker();

// ---------- Boot ----------
if (window.location.hostname === 'github.com') boot();

async function boot() {
  ccState.efMode = await getEfMode();
  mount(ccState.efMode);
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'sync' && changes.efMode) {
      ccState.efMode = !!changes.efMode.newValue;
      unmount(); mount(ccState.efMode);
    }
  });
}
function getEfMode(){ return new Promise(r => chrome.storage.sync.get({ efMode:false }, v => r(!!v.efMode))); }
function mount(ef){ if (ccState.mounted) return; createFloatingSprite(ef); ccState.mounted = true; }
function unmount(){ document.getElementById('coding-companion')?.remove(); document.getElementById('cc-bubble')?.remove(); stopSprint(true); ccState.mounted = false; }

// ---------- Utils ----------
function getRepoScopeFromUrl(){ const m = location.href.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i); return m ? m[2].toLowerCase() : "repo"; }
function clampPos(pos){ const m=8, maxL=Math.max(m, innerWidth-40), maxT=Math.max(m, innerHeight-40); return { left: Math.min(maxL, Math.max(m,pos.left)), top: Math.min(maxT, Math.max(m,pos.top)) }; }
function loadPos(key){ try{ const raw=localStorage.getItem(key); if(!raw) return null; const p=JSON.parse(raw); if(typeof p.left==='number'&&typeof p.top==='number') return clampPos(p);}catch{} return null; }
function savePos(key,pos){ try{ localStorage.setItem(key, JSON.stringify(clampPos(pos))); }catch{} }
function resetPos(key){ try{ localStorage.removeItem(key); }catch{} }
function escapeHtml(s=''){ return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function ensureBadge(sprite){
  let b = document.getElementById('cc-badge');
  if (!b) {
    b = document.createElement('div');
    b.id = 'cc-badge';
    b.style.cssText = 'position:absolute; bottom:-2px; right:-2px; min-width:18px; height:18px; padding:0 4px; background:#111; color:#fff; border-radius:9px; font-size:11px; display:none; align-items:center; justify-content:center; box-shadow:0 2px 8px rgba(0,0,0,.3);';
    sprite.appendChild(b);
  }
  return b;
}
function stopSprint(fromUnmount=false){
  if (sprintTimer) { clearInterval(sprintTimer); sprintTimer = null; }
  const wasCanceled = sprintSecs > 0; // if >0 when stopped, user canceled / UI remounted
  if (wasCanceled && !fromUnmount) {
    // record a non-success end
    const duration = currentAnalysisData?.predictions?.recommendedSprintDuration || 5;
    chrome.runtime.sendMessage({ type:'RECORD_SPRINT_RESULT', duration, success:false });
    aiFeedback.recordFeedback('sprint_ended', { success:false, duration });
  }
  sprintSecs = 0;
  document.getElementById('cc-badge')?.style && (document.getElementById('cc-badge').style.display='none');
}

// Drag util (mouse + touch)
function dragEnable(el, storageKey, handle){
  let dragging=false, dx=0, dy=0;
  const target = handle || el;
  const onStart=(x,y)=>{ const r=el.getBoundingClientRect(); el.style.top=r.top+'px'; el.style.left=r.left+'px'; el.style.bottom='auto'; el.style.right='auto'; dx=x-r.left; dy=y-r.top; dragging=true; (handle||el).style.cursor='grabbing'; };
  const onMove=(x,y)=>{ if(!dragging) return; const left=Math.max(8,Math.min(innerWidth-40,x-dx)); const top=Math.max(8,Math.min(innerHeight-40,y-dy)); el.style.left=left+'px'; el.style.top=top+'px'; };
  const onEnd=()=>{ if(!dragging) return; dragging=false; (handle||el).style.cursor='grab'; const r=el.getBoundingClientRect(); savePos(storageKey,{ top:Math.round(r.top), left:Math.round(r.left) }); };
  target.addEventListener('mousedown', e=>{ e.preventDefault(); onStart(e.clientX,e.clientY); });
  addEventListener('mousemove', e=> onMove(e.clientX,e.clientY));
  addEventListener('mouseup', onEnd);
  target.addEventListener('touchstart', e=>{ const t=e.touches[0]; if(!t) return; onStart(t.clientX,t.clientY); }, {passive:true});
  addEventListener('touchmove', e=>{ const t=e.touches?.[0]; if(!t) return; onMove(t.clientX,t.clientY); }, {passive:true});
  addEventListener('touchend', onEnd);
}

// Tooltip & fun FX
function showQuickTooltip(message){
  document.querySelector('.cc-tooltip')?.remove();
  const tooltip = document.createElement('div');
  tooltip.className='cc-tooltip'; tooltip.textContent=message;
  document.getElementById('coding-companion')?.appendChild(tooltip);
  setTimeout(()=>tooltip.remove(), 2500);
}
function createCelebrationEffect(){
  const sprite = document.getElementById('coding-companion'); if(!sprite) return;
  for (let i=0;i<5;i++){
    setTimeout(()=>{
      const spark=document.createElement('div');
      spark.style.cssText='position:absolute;width:4px;height:4px;background:#FFD700;border-radius:50%;pointer-events:none;animation:spark-'+i+' 1s ease-out forwards;';
      sprite.appendChild(spark);
      const css='@keyframes spark-'+i+'{0%{transform:translate(0,0) scale(1);opacity:1}100%{transform:translate('+(Math.random()-0.5)*100+'px,'+(Math.random()-0.5)*100+'px) scale(0);opacity:0}}';
      const st=document.createElement('style'); st.textContent=css; document.head.appendChild(st);
      setTimeout(()=>{ spark.remove(); st.remove(); }, 1000);
    }, i*100);
  }
}
function updateSpritePersonality(analysisData){
  const sprite=document.getElementById('coding-companion'); if(!sprite||!analysisData) return;
  const { confidence={}, predictions={} } = analysisData;
  const conf = confidence.overall ?? 0;
  sprite.style.background = conf > .7 ? 'linear-gradient(135deg,#4facfe 0%,#00f2fe 100%)'
                      : conf > .3 ? 'linear-gradient(135deg,#fa709a 0%,#fee140 100%)'
                                  : 'linear-gradient(135deg,#a8edea 0%,#fed6e3 100%)';
  if ((predictions.currentProductivity ?? 0) > .8) sprite.style.animation='energetic-bounce 2s ease-in-out infinite';
  else if ((predictions.currentProductivity ?? 1) < .3) sprite.style.animation='gentle-sway 6s ease-in-out infinite';
  else sprite.style.animation='gentle-float 4s ease-in-out infinite';
}

// ---------- Main UI ----------
function createFloatingSprite(efMode){
  // SPRITE
  const sprite=document.createElement('div'); sprite.id='coding-companion';
  const start=loadPos('cc-sprite-pos');
  sprite.style.cssText=`position:fixed; ${start?`top:${start.top}px; left:${start.left}px;`:`bottom:20px; right:20px;`} width:70px; height:70px; background:linear-gradient(135deg,#667eea 0%, #764ba2 100%); border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:32px; cursor:grab; z-index:2147483647; box-shadow:0 8px 25px rgba(102,126,234,.4); transition:all .3s cubic-bezier(.4,0,.2,1); user-select:none; animation:gentle-float 4s ease-in-out infinite;`;
  const face=document.createElement('span'); face.id='cc-face'; face.textContent='🧙‍♂️'; face.style.cssText='transition:all .3s ease; transform-origin:center;'; sprite.appendChild(face);
  const particles=document.createElement('div'); particles.className='cc-particles'; particles.style.cssText='position:absolute; top:-10px; left:-10px; right:-10px; bottom:-10px; pointer-events:none; border-radius:50%; opacity:0; background:radial-gradient(circle, rgba(102,126,234,.3) 0%, transparent 70%); animation:particle-pulse 2s ease-in-out infinite;'; sprite.appendChild(particles);
  const badge = ensureBadge(sprite);
  sprite.addEventListener('mouseenter', ()=>{ sprite.style.transform='scale(1.15) translateY(-5px)'; sprite.style.boxShadow='0 15px 35px rgba(102,126,234,.6)'; particles.style.opacity='1'; face.style.transform='rotate(10deg)'; const em=['🚀','⚡','💡','🎯','🔥','✨','💪','🎨']; const r=em[Math.floor(Math.random()*em.length)]; setTimeout(()=>face.textContent=r,100); setTimeout(()=>face.textContent='🧙‍♂️',800); });
  sprite.addEventListener('mouseleave', ()=>{ sprite.style.transform='scale(1) translateY(0)'; sprite.style.boxShadow='0 8px 25px rgba(102,126,234,.4)'; particles.style.opacity='0'; face.style.transform='rotate(0deg)'; });

  // BUBBLE
  const bubble=document.createElement('div'); bubble.id='cc-bubble';
  const bStart=loadPos('cc-bubble-pos');
  bubble.style.cssText=`position:fixed; ${bStart?`top:${bStart.top}px; left:${bStart.left}px;`:`bottom:90px; right:20px;`} max-width:340px; background:#111; color:#fff; padding:12px 14px; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,.25); font-size:13px; line-height:1.35; z-index:2147483647; user-select:none;`;
  const header=document.createElement('div'); header.style.cssText='display:flex; align-items:center; gap:8px; margin:-6px -8px 8px -8px; padding:6px 8px 0 8px; cursor:grab; background:linear-gradient(90deg,rgba(255,255,255,.10),rgba(255,255,255,.05)); border-top-left-radius:10px; border-top-right-radius:10px;';
  const grip=document.createElement('div'); grip.style.cssText='width:36px; height:6px; border-radius:3px; background:rgba(255,255,255,.3); margin:2px 0;'; 
  const closeBtn=document.createElement('button'); closeBtn.textContent='×'; closeBtn.setAttribute('aria-label','Close'); closeBtn.style.cssText='margin-left:auto; width:20px; height:20px; background:transparent; color:#bbb; border:0; font-size:16px; cursor:pointer;'; closeBtn.addEventListener('click',()=>{ bubble.style.display='none'; aiFeedback.recordFeedback('bubble_closed',{ method:'close_button' }); });
  header.appendChild(grip); header.appendChild(closeBtn);

  const msgWrap=document.createElement('div'); msgWrap.id='cc-message'; msgWrap.textContent = ccState.efMode ? 'Ready for a smart sprint?' : 'Hi! I can analyze this repo with AI insights.';
  const aiWrap=document.createElement('div'); aiWrap.id='cc-ai-insights'; aiWrap.style.cssText='margin-top:8px; display:none;';
  const coachWrap=document.createElement('div'); coachWrap.id='cc-coach'; coachWrap.style.cssText='margin-top:8px; display:none;';
  const whyWrap=document.createElement('div'); whyWrap.id='cc-why'; whyWrap.style.cssText='margin-top:6px; font-size:12px; color:#aaa; display:none;';
  const efWrap=document.createElement('div'); if (ccState.efMode) { efWrap.style.cssText='margin-top:8px; display:flex; gap:6px; flex-wrap:wrap;'; efWrap.innerHTML=`<button id="cc-sprint" class="cc-btn">Smart Sprint</button><button id="cc-stuck" class="cc-btn">I'm stuck</button>`; }
  const feedbackWrap=document.createElement('div'); feedbackWrap.id='cc-feedback'; feedbackWrap.style.cssText='margin-top:8px; display:none;';

  // Styles
  const style=document.createElement('style');
  style.textContent=`@keyframes gentle-float{0%,100%{transform:translateY(0) rotate(0)}25%{transform:translateY(-8px) rotate(1deg)}50%{transform:translateY(-4px) rotate(0)}75%{transform:translateY(-12px) rotate(-1deg)}}@keyframes click-bounce{0%{transform:scale(1)}50%{transform:scale(.9)}100%{transform:scale(1.05)}}@keyframes energetic-bounce{0%,100%{transform:translateY(0)}25%{transform:translateY(-15px) rotate(5deg)}50%{transform:translateY(-8px)}75%{transform:translateY(-20px) rotate(-5deg)}}@keyframes gentle-sway{0%,100%{transform:translateX(0) rotate(0)}33%{transform:translateX(3px) rotate(2deg)}66%{transform:translateX(-3px) rotate(-2deg)}}@keyframes particle-pulse{0%,100%{transform:scale(1);opacity:0}50%{transform:scale(1.2);opacity:.3}}.cc-tooltip{position:absolute;bottom:80px;right:0;background:rgba(0,0,0,.9);color:#fff;padding:8px 12px;border-radius:8px;font-size:12px;white-space:nowrap;z-index:2147483648;animation:tooltip-appear .3s ease}@keyframes tooltip-appear{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.7}}#coding-companion:hover{transform:scale(1.08)!important}.cc-chip{background:#fff;color:#111;border:none;border-radius:10px;padding:6px 10px;cursor:pointer;font-size:12px}.cc-small{font-size:11px;opacity:.8;margin-top:6px}.cc-link{color:#9ad;text-decoration:underline;cursor:pointer;font-size:12px;margin-left:6px}.cc-btn{background:#fff;color:#111;border:none;border-radius:10px;padding:8px 10px;cursor:pointer;font-size:12px}.cc-ai-badge{background:linear-gradient(45deg,#667eea,#764ba2);color:#fff;font-size:10px;padding:2px 6px;border-radius:8px;margin-left:6px}.cc-feedback-btn{background:#333;color:#fff;border:none;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px;margin-right:4px}.cc-feedback-btn:hover{background:#555}.cc-feedback-btn.positive{background:#28a745}.cc-feedback-btn.negative{background:#dc3545}`;
  document.head.appendChild(style);

  bubble.appendChild(header); bubble.appendChild(msgWrap); bubble.appendChild(aiWrap); bubble.appendChild(coachWrap); bubble.appendChild(whyWrap); if (ccState.efMode) bubble.appendChild(efWrap); bubble.appendChild(feedbackWrap);

  // Click → analyze
  let clickCount=0;
  sprite.addEventListener('click', (e)=>{
    if (e.shiftKey){ resetPos('cc-bubble-pos'); bubble.style.bottom='90px'; bubble.style.right='20px'; bubble.style.top='auto'; bubble.style.left='auto'; return; }
    clickCount++;
    sprite.style.animation='click-bounce .3s ease'; face.style.transform='scale(.8)'; setTimeout(()=>{ face.style.transform='scale(1)'; sprite.style.animation='gentle-float 4s ease-in-out infinite'; },150);
    if (clickCount===1) showQuickTooltip('Analyzing your code patterns...');
    else if (clickCount%5===0) showQuickTooltip('You love clicking me! That shows good engagement 📈');
    else if (clickCount>10) showQuickTooltip('Wow, we are really connecting! 🤝');

    face.textContent='🤔'; msgWrap.textContent='Analyzing with AI patterns...'; aiWrap.style.display='none'; coachWrap.style.display='none'; whyWrap.style.display='none'; feedbackWrap.style.display='none'; bubble.style.display='block';
    aiFeedback.recordFeedback('analysis_requested', {});

    setTimeout(()=>{
      chrome.runtime.sendMessage({ type:'ANALYZE_CURRENT_REPO', url: location.href }, (resp)=>{
        if (!resp){ face.textContent='💀'; msgWrap.textContent='No response from AI engine. Try reloading the extension.'; return; }
        currentAnalysisData = resp;
        const moodToEmoji={ encouraging:'😊', celebrating:'🎉', excited:'🤩', thinking:'🤔', nudging:'👀' };
        face.textContent = moodToEmoji[resp.mood] || '🧙‍♂️';
        msgWrap.textContent = resp.text || 'All set.';
        updateSpritePersonality(resp);

        if (resp.predictions && Object.keys(resp.predictions).length) displayAIInsights(aiWrap, resp.predictions, resp.confidence||{overall:0});

        coachWrap.innerHTML=''; coachWrap.appendChild(buildCoach(getRepoScopeFromUrl())); coachWrap.style.display = resp.showCoach ? 'block':'none';

        if (resp.why){
          const aiIndicator = resp.caseType==='AI_PERSONALIZED' ? '<span class="cc-ai-badge">AI</span>' : '';
          whyWrap.innerHTML = `<span class="cc-link" id="cc-why-toggle">Why this?</span>${aiIndicator}<span id="cc-why-text" style="display:none;"> ${escapeHtml(resp.why)}</span>`;
          whyWrap.style.display='block';
          const tgl=whyWrap.querySelector('#cc-why-toggle'); const txt=whyWrap.querySelector('#cc-why-text');
          tgl.addEventListener('click', ()=>{ txt.style.display = (txt.style.display==='inline') ? 'none':'inline'; aiFeedback.recordFeedback('why_clicked',{ caseType:resp.caseType }); });
        } else { whyWrap.style.display='none'; }

        showFeedbackButtons(feedbackWrap, resp);
        if (resp.caseType==='AI_PERSONALIZED') createCelebrationEffect();
        setTimeout(()=>{ face.textContent='🧙‍♂️'; }, 4000);
        aiFeedback.recordFeedback('analysis_completed', { caseType:resp.caseType, mood:resp.mood, hasAI: resp.caseType==='AI_PERSONALIZED' });
      });
    }, 200);
  });

  // EF buttons
  if (ccState.efMode){
    const sprintBtn=bubble.querySelector('#cc-sprint');
    const stuckBtn=bubble.querySelector('#cc-stuck');
    sprintBtn?.addEventListener('click', ()=>{
      const duration=currentAnalysisData?.predictions?.recommendedSprintDuration || 5;
      startSprint(sprite, face, msgWrap, duration);
      aiFeedback.recordFeedback('sprint_started',{ duration, aiRecommended: currentAnalysisData?.caseType==='AI_PERSONALIZED' });
    });
    stuckBtn?.addEventListener('click', ()=>{
      showStuck(msgWrap, coachWrap, getRepoScopeFromUrl());
      aiFeedback.recordFeedback('stuck_help_used',{});
    });
  }

  // Dragging
  dragEnable(sprite, 'cc-sprite-pos');
  dragEnable(bubble, 'cc-bubble-pos', header);

  document.body.appendChild(sprite); document.body.appendChild(bubble);
}

// ---------- AI panels & EF helpers ----------
function displayAIInsights(container, predictions={}, confidence={overall:0}){
  const pct = Math.round((confidence.overall||0)*100);
  let html = `<div style="background:rgba(255,255,255,0.1); padding:8px; border-radius:6px; margin-bottom:8px;">`;
  if (pct < 30) html += `<div style="font-size:11px; color:#ffc107;">🧠 AI Learning Mode: Building your pattern profile...</div>`;
  else {
    html += `<div style="font-size:11px; color:#28a745;">✨ AI Insights (${pct}% confidence):</div>`;
    if (typeof predictions.currentProductivity === 'number') html += `<div style="font-size:11px; margin-top:4px;">📈 Current productivity: ${Math.round(predictions.currentProductivity*100)}%</div>`;
    if (predictions.bestUpcomingHour?.hour != null) html += `<div style="font-size:11px; margin-top:4px;">⏰ Peak time: ${predictions.bestUpcomingHour.hour}:00</div>`;
    if (predictions.recommendedSprintDuration && predictions.recommendedSprintDuration !== 5) html += `<div style="font-size:11px; margin-top:4px;">🎯 Optimal sprint: ${predictions.recommendedSprintDuration} min</div>`;
  }
  html += `</div>`;
  container.innerHTML = html; container.style.display='block';
}
function updateEFControls(container, analysisData){
  const sprintBtn = container.querySelector('#cc-sprint');
  if (sprintBtn && analysisData?.predictions?.recommendedSprintDuration) {
    sprintBtn.textContent = `${analysisData.predictions.recommendedSprintDuration}-min Sprint 🧠`;
  }
}
function showFeedbackButtons(container, analysisData){
  container.innerHTML = `<div style="font-size:11px; color:#aaa; margin-bottom:4px;">Was this helpful?</div>
    <div>
      <button class="cc-feedback-btn positive" data-reaction="positive">👍 Yes</button>
      <button class="cc-feedback-btn negative" data-reaction="negative">👎 No</button>
      <button class="cc-feedback-btn" data-reaction="neutral">😐 Okay</button>
    </div>`;
  container.querySelectorAll('.cc-feedback-btn').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const reaction = btn.dataset.reaction;
      aiFeedback.recordFeedback('feedback_given', { reaction, mood:analysisData.mood, caseType:analysisData.caseType });
      btn.textContent = reaction==='positive' ? '✅ Thanks!' : reaction==='negative' ? '📝 Noted' : '👌 Got it';
      btn.disabled = true;
      setTimeout(()=>{ container.style.display='none'; }, 1500);
    });
  });
  container.style.display='block';
}
function startSprint(sprite, face, msgWrap, duration=5){
  const badge = ensureBadge(sprite);
  if (sprintTimer) clearInterval(sprintTimer);
  sprintSecs = duration * 60;
  face.textContent = '💪';
  badge.style.display='flex'; updateBadge(badge);
  // FIX: decrement only ONCE per tick
  sprintTimer = setInterval(()=>{
    sprintSecs--;
    updateBadge(badge);
    if (sprintSecs <= 0){
      clearInterval(sprintTimer); sprintTimer=null;
      face.textContent='🎉'; msgWrap.textContent = `${duration}-minute sprint complete! Make a tiny commit.`;
      setTimeout(()=>{ face.textContent='🧙‍♂️'; }, 4000);
      chrome.runtime.sendMessage({ type:'RECORD_SPRINT_RESULT', duration, success:true });
    }
  }, 1000);
}
function updateBadge(b){ const m=Math.floor(sprintSecs/60), s=sprintSecs%60; b.textContent = `${m}:${s.toString().padStart(2,'0')}`; }
function showStuck(msgWrap, coachWrap, scope){
  const ideas = [
    "Add one sentence to README about setup or purpose.",
    "Rename one vague variable to something clearer.",
    "Write one TODO comment above a tricky block.",
    "Add a docstring/JSDoc to one function.",
    "Run formatter on one file and commit."
  ].sort(()=>Math.random()-0.5).slice(0,3);
  msgWrap.innerHTML = `<div>Pick one 1-minute action:</div><ul style="margin:6px 0 0 16px">${ideas.map(i=>`<li>${escapeHtml(i)}</li>`).join('')}</ul><div style="font-size:11px; color:#aaa; margin-top:6px;">🧠 AI will learn which actions work best for you</div>`;
  coachWrap.style.display='block';
}

// Conventional commits chips
function buildCoach(scope){
  const wrap=document.createElement('div');
  wrap.innerHTML = `
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="cc-chip" data-template="feat(${scope}): ">feat(${scope}): …</button>
      <button class="cc-chip" data-template="fix(${scope}): ">fix(${scope}): …</button>
      <button class="cc-chip" data-template="docs(${scope}): ">docs(${scope}): …</button>
      <button class="cc-chip" data-template="refactor(${scope}): ">refactor(${scope}): …</button>
    </div>
    <div class="cc-small">Click a chip to copy a Conventional Commit starter to your clipboard.</div>`;
  wrap.querySelectorAll('[data-template]').forEach(btn=>{
    const label=btn.textContent;
    btn.addEventListener('click', async (e)=>{
      const text=e.currentTarget.getAttribute('data-template');
      try{ await navigator.clipboard.writeText(text); e.currentTarget.textContent='Copied ✓'; setTimeout(()=>btn.textContent=label,1200); }
      catch{ prompt('Copy this commit message start:', text); }
    });
  });
  return wrap;
}

// Popup → Analyze
chrome.runtime.onMessage.addListener(msg => {
  if (msg?.type === 'TRIGGER_ANALYZE_FROM_POPUP') document.getElementById('coding-companion')?.click();
});
