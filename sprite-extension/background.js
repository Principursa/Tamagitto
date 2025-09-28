// background.js - smart metric v4.1: AI pattern learning + deterministic cycling + heuristic fallback
console.log("[CC Background] Loading smart-metric v4.1 with AI learning + cycling...");

// ------------------------------
// AI Pattern Learning Engine (yours, unchanged except logs)
// ------------------------------
class PatternLearningEngine {
  constructor() {
    this.patterns = { productivity: [], sprintSuccess: [], repoEngagement: [], userFeedback: [] };
    this.insights = { bestProductivityHours: [], optimalSprintDuration: 5, preferredMoodStyle: 'encouraging', repoPreferences: {}, engagementPatterns: {} };
    this.confidence = { productivity: 0, sprints: 0, mood: 0, overall: 0 };
    this.initialized = false;
  }
  async initialize() {
    if (this.initialized) return;
    await this.loadPatterns();
    this.initialized = true;
    console.log("[CC AI] Pattern engine initialized with confidence:", this.confidence);
  }
  async recordPattern(type, data) {
    if (!this.initialized) await this.initialize();
    const pattern = Object.assign({}, data, { timestamp: Date.now() });
    if (this.patterns[type]) {
      this.patterns[type].push(pattern);
      if (this.patterns[type].length > 100) this.patterns[type] = this.patterns[type].slice(-100);
      await this.savePatterns();
      this.analyzePatterns(type);
    }
  }
  analyzePatterns(type) {
    switch(type) {
      case 'productivity': this.analyzeProductivityPatterns(); break;
      case 'sprintSuccess': this.analyzeSprintPatterns(); break;
      case 'userFeedback': this.analyzeFeedbackPatterns(); break;
    }
    this.updateOverallConfidence();
  }
  analyzeProductivityPatterns() {
    const data = this.patterns.productivity;
    if (data.length < 5) return;
    const hourlyData = {};
    data.forEach(p => {
      const hour = new Date(p.timestamp).getHours();
      if (!hourlyData[hour]) hourlyData[hour] = [];
      hourlyData[hour].push(p.productivity_score);
    });
    this.insights.bestProductivityHours = Object.entries(hourlyData)
      .map(([hour, scores]) => ({
        hour: parseInt(hour, 10),
        avgScore: scores.reduce((a,b)=>a+b,0) / scores.length,
        confidence: Math.min(scores.length / 5, 1)
      }))
      .filter(h => h.confidence > 0.2)
      .sort((a,b) => b.avgScore - a.avgScore)
      .slice(0, 3);
    this.confidence.productivity = Math.min(data.length / 20, 1);
  }
  analyzeSprintPatterns() {
    const data = this.patterns.sprintSuccess;
    if (data.length < 3) return;
    const durationSuccess = {};
    data.forEach(s => {
      if (!durationSuccess[s.duration]) durationSuccess[s.duration] = { successes: 0, total: 0 };
      durationSuccess[s.duration].total++;
      if (s.success) durationSuccess[s.duration].successes++;
    });
    let bestDuration = 5, bestRate = 0;
    Object.entries(durationSuccess).forEach(([duration, stats]) => {
      const rate = stats.successes / stats.total;
      if (rate > bestRate && stats.total >= 2) { bestRate = rate; bestDuration = parseInt(duration, 10); }
    });
    this.insights.optimalSprintDuration = bestDuration;
    this.confidence.sprints = Math.min(data.length / 10, 1);
  }
  analyzeFeedbackPatterns() {
    const data = this.patterns.userFeedback;
    if (data.length < 5) return;
    const moodEffectiveness = {};
    data.forEach(f => {
      if (!moodEffectiveness[f.mood_shown]) moodEffectiveness[f.mood_shown] = { positive: 0, total: 0 };
      moodEffectiveness[f.mood_shown].total++;
      if (f.user_reaction === 'positive') moodEffectiveness[f.mood_shown].positive++;
    });
    let bestMood = 'encouraging', bestRate = 0;
    Object.entries(moodEffectiveness).forEach(([mood, stats]) => {
      const rate = stats.positive / stats.total;
      if (rate > bestRate && stats.total >= 3) { bestRate = rate; bestMood = mood; }
    });
    this.insights.preferredMoodStyle = bestMood;
    this.confidence.mood = Math.min(data.length / 15, 1);
  }
  updateOverallConfidence() {
    const vals = Object.values(this.confidence).filter(c => c > 0);
    this.confidence.overall = vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : 0;
  }
  generatePredictions() {
    if (!this.initialized) return {};
    const now = new Date(), currentHour = now.getHours();
    const predictions = {};
    if (this.confidence.productivity > 0.3) {
      const currentHourData = this.insights.bestProductivityHours.find(h => h.hour === currentHour);
      predictions.currentProductivity = currentHourData ? currentHourData.avgScore : 0.5;
      if (this.insights.bestProductivityHours.length > 0) {
        predictions.bestUpcomingHour = this.insights.bestProductivityHours[0];
      }
    }
    if (this.confidence.sprints > 0.2) predictions.recommendedSprintDuration = this.insights.optimalSprintDuration;
    if (this.confidence.mood > 0.2) predictions.preferredMoodStyle = this.insights.preferredMoodStyle;
    // Expose confidence alongside predictions for the UI
    predictions.confidence = this.confidence;
    return predictions;
  }
  async savePatterns() {
    try {
      await chrome.storage.local.set({
        cc_ai_patterns: this.patterns,
        cc_ai_insights: this.insights,
        cc_ai_confidence: this.confidence
      });
    } catch (e) { console.error("[CC AI] Failed to save patterns:", e); }
  }
  async loadPatterns() {
    try {
      const data = await chrome.storage.local.get(['cc_ai_patterns','cc_ai_insights','cc_ai_confidence']);
      if (data.cc_ai_patterns) this.patterns = data.cc_ai_patterns;
      if (data.cc_ai_insights) this.insights = data.cc_ai_insights;
      if (data.cc_ai_confidence) this.confidence = data.cc_ai_confidence;
      const totalPts = Object.values(this.patterns).reduce((a,b)=>a+b.length,0);
      console.log("[CC AI] Loaded patterns with", totalPts, "total data points");
    } catch (e) { console.error("[CC AI] Failed to load patterns:", e); }
  }
}
const aiEngine = new PatternLearningEngine();

// ------------------------------
// Smart metrics + variety pools
// ------------------------------
function parseRepoFromUrl(url) {
  const m = url.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  return m ? (m[1] + "/" + m[2]) : null;
}
function dateOnly(iso) {
  const d = new Date(iso);
  return new Date(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
}
function computeMetrics(commits) {
  if (!Array.isArray(commits) || commits.length === 0) {
    return { daysSinceLast: Infinity, streak: 0, avgMsgLen: 0, pctConventional: 0 };
  }
  commits = commits.slice().sort((a,b) => new Date(b.commit.author.date) - new Date(a.commit.author.date));
  const lastDate = new Date(commits[0].commit.author.date);
  const now = new Date();
  const daysSinceLast = Math.floor((now - lastDate) / (1000*60*60*24));

  const byDay = new Set(commits.map(c => dateOnly(c.commit.author.date).getTime()));
  let streak = 0;
  for (let i = 0; i < 30; i++) {
    const day = new Date(); day.setHours(0,0,0,0); day.setDate(day.getDate() - i);
    if (byDay.has(day.getTime())) streak++;
    else { if (i === 0) continue; break; }
  }

  const msgs = commits.slice(0, 20).map(c => (c.commit.message || '').trim());
  const avgMsgLen = msgs.length ? Math.round(msgs.reduce((a,b)=>a+b.length,0) / msgs.length) : 0;
  const cc = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?:\s/i;
  const conventionalHits = msgs.filter(m => cc.test(m)).length;
  const pctConventional = msgs.length ? Math.round(100 * conventionalHits / msgs.length) : 0;

  return { daysSinceLast, streak, avgMsgLen, pctConventional };
}

const POOLS = {
  QUIET: {
    mood: "nudging",
    lines: [
      "Repo’s been quiet—ship a tiny PR today. One file, one line.",
      "Momentum hack: a 5-minute doc or test counts. Push something small.",
      "Silence ≠ rest. Make a micro-commit to reopen the loop."
    ],
    why: (m) => `Repo quiet for ${m.daysSinceLast} days → tiny PR restarts momentum.`
  },
  STREAK_SHORT_MSG: {
    mood: "thinking",
    lines: [
      "🔥 Streak going, but messages are terse. Add a verb + object.",
      "Keep shipping—write one line about *why* the change exists.",
      "Future-you will thank you: 8–12 words beats “update”."
    ],
    why: (m) => `You're on a ${m.streak}-day streak, avg message ${m.avgMsgLen} chars → templates help clarity.`
  },
  LOW_CONVENTIONAL: {
    mood: "encouraging",
    lines: [
      "Good detail—try a Conventional header like “feat:” or “fix:”.",
      "Boost consistency: start with “docs:” or “refactor:”.",
      "Team-friendly format: type(scope): summary."
    ],
    why: (m) => `Only ${m.pctConventional}% use Conventional Commits → templates speed consistency.`
  },
  DEFAULT: {
    mood: "celebrating",
    lines: [
      "Nice push. Keep the rhythm: one focused change, one clear message.",
      "Solid pace—aim for a tiny PR before you leave this page.",
      "Ship it small, ship it clear. You’re close."
    ],
    why: () => ""
  }
};
async function pickLine(repo, caseKey, pool) {
  const key = `cc-cycle-${repo}-${caseKey}`;
  const { [key]: idx = 0 } = await chrome.storage.local.get(key);
  const line = pool.lines[idx % pool.lines.length];
  await chrome.storage.local.set({ [key]: (idx + 1) % pool.lines.length });
  return line;
}
function classifyCase(m) {
  if (m.daysSinceLast > 3) return "QUIET";
  if (m.streak >= 3 && m.avgMsgLen < 20) return "STREAK_SHORT_MSG";
  if (m.pctConventional < 30 && m.avgMsgLen >= 20) return "LOW_CONVENTIONAL";
  return "DEFAULT";
}

// ------------------------------
// Analysis + AI override + fallback w/ cycling
// ------------------------------
async function analyzeRepoFromUrl(url) {
  const repo = parseRepoFromUrl(url);
  if (!repo) throw new Error("Not on a GitHub repo page.");

  if (!aiEngine.initialized) await aiEngine.initialize();

  const res = await fetch(`https://api.github.com/repos/${repo}/commits?per_page=50`);
  if (!res.ok) throw new Error("GitHub API error: " + res.status);

  const commits = await res.json();
  const metrics = computeMetrics(commits);

  // Minimal predictions from your learning engine
  const predictions = aiEngine.generatePredictions();
  // Record interaction for learning
  await recordInteractionForLearning(repo, metrics, predictions);

  // Try AI-driven override first
  const aiOverride = await checkAIOverride(metrics, predictions);
  if (aiOverride) {
    const mood = sanitizeMood(aiOverride.mood || predictions.preferredMoodStyle || "encouraging");
    return {
      text: aiOverride.text,
      mood,
      showCoach: true,
      why: aiOverride.why,
      metrics,
      predictions,
      caseType: "AI_PERSONALIZED",
      confidence: aiEngine.confidence
    };
  }

  // Heuristic fallback with deterministic variety
  const caseKey = classifyCase(metrics);
  const pool = POOLS[caseKey];
  let text = await pickLine(repo, caseKey, pool);
  if (caseKey === "DEFAULT") {
    const msg = (commits[0]?.commit?.message || "").trim();
    const teaser = msg.length > 30 ? msg.slice(0, 30) + "..." : (msg || "your last commit");
    text = `“${teaser}” — ${text}`;
  }
  const mood = sanitizeMood(predictions.preferredMoodStyle || pool.mood);
  return {
    text,
    mood,
    showCoach: caseKey !== "DEFAULT",
    why: pool.why(metrics),
    metrics,
    predictions,
    caseType: "HEURISTIC",
    confidence: aiEngine.confidence
  };
}

function sanitizeMood(mood) {
  const allowed = new Set(["encouraging","celebrating","excited","thinking","nudging"]);
  return allowed.has(mood) ? mood : "encouraging";
}

async function checkAIOverride(metrics, predictions) {
  if (aiEngine.confidence.overall < 0.3) return null;

  if (predictions.currentProductivity && predictions.currentProductivity > 0.7) {
    return {
      text: "Perfect timing! Your productivity peaks around now. Ready for a focused session?",
      mood: "excited",
      why: `AI detected ${Math.round(predictions.currentProductivity * 100)}% productivity potential based on your patterns`
    };
  }
  if (predictions.recommendedSprintDuration && predictions.recommendedSprintDuration !== 5) {
    return {
      text: `Try a ${predictions.recommendedSprintDuration}-minute sprint—that's your sweet spot!`,
      mood: "encouraging",
      why: `AI learned you succeed more with ${predictions.recommendedSprintDuration}-minute focus sessions`
    };
  }
  return null;
}

async function recordInteractionForLearning(repo, metrics, predictions) {
  const now = new Date();
  let productivityScore = 0.5;
  if (metrics.daysSinceLast < 1) productivityScore += 0.2;
  if (metrics.avgMsgLen > 15) productivityScore += 0.1;
  if (metrics.pctConventional > 50) productivityScore += 0.1;
  productivityScore = Math.min(productivityScore, 1.0);

  await aiEngine.recordPattern('productivity', {
    hour: now.getHours(),
    dayOfWeek: now.getDay(),
    productivity_score: productivityScore,
    repo_activity: metrics.daysSinceLast < 1 ? 'active' : 'quiet',
    repo
  });
}

// ------------------------------
// TTS helper
// ------------------------------
function speak(text) {
  if (chrome.tts) chrome.tts.speak(text, { rate: 0.95, pitch: 1.05 });
}

// ------------------------------
// Message router (ANALYZE + logs)
// ------------------------------
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "ANALYZE_CURRENT_REPO") {
    analyzeRepoFromUrl(msg.url)
      .then(feedback => { speak(feedback.text); sendResponse(Object.assign({ ok: true }, feedback)); })
      .catch(e => {
        const fallback = {
          text: "Trouble talking to GitHub, but you can still ship a tiny improvement.",
          mood: "encouraging",
          showCoach: true,
          why: "API error",
          metrics: {},
          predictions: {},
          caseType: "ERROR",
          confidence: aiEngine.confidence
        };
        speak(fallback.text);
        sendResponse(Object.assign({ ok: false, error: String(e) }, fallback));
      });
    return true;
  }

  if (msg && msg.type === "RECORD_USER_FEEDBACK") {
    (async () => {
      await aiEngine.recordPattern('userFeedback', {
        mood_shown: msg.mood || '',
        user_reaction: msg.reaction || 'neutral',
        context: msg.context || {}
      });
      // Optional local log ring buffer (handy for debugging)
      try {
        const data = await chrome.storage.local.get({ cc_feedback: [] });
        const arr = data.cc_feedback; arr.push({ ts: Date.now(), mood: msg.mood, reaction: msg.reaction, context: msg.context });
        await chrome.storage.local.set({ cc_feedback: arr.slice(-500) });
      } catch {}
      sendResponse({ success: true });
    })();
    return true;
  }

  if (msg && msg.type === "RECORD_SPRINT_RESULT") {
    (async () => {
      await aiEngine.recordPattern('sprintSuccess', {
        duration: msg.duration || 5,
        success: !!msg.success,
        time_of_day: new Date().getHours(),
        day_type: new Date().getDay() < 5 ? 'weekday' : 'weekend'
      });
      // Optional local log
      try {
        const data = await chrome.storage.local.get({ cc_sprints: [] });
        const arr = data.cc_sprints; arr.push({ ts: Date.now(), duration: msg.duration || 5, success: !!msg.success });
        await chrome.storage.local.set({ cc_sprints: arr.slice(-200) });
      } catch {}
      sendResponse({ success: true });
    })();
    return true;
  }
});

console.log("[CC Background] Smart-metric v4.1 loaded successfully");

