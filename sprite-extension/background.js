// background.js (MV3 service worker) — smart metric v2 w/ coach hint

function parseRepoFromUrl(url) {
  const m = url.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  if (!m) return null;
  return `${m[1]}/${m[2]}`;
}

// --- Metrics helpers ---
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
    const day = new Date();
    day.setHours(0,0,0,0);
    day.setDate(day.getDate() - i);
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

function makeFeedback(commits) {
  const m = computeMetrics(commits);

  // Defaults
  let showCoach = false;
  let why = "";

  if (m.daysSinceLast > 3) {
    showCoach = true;
    why = `Repo quiet for ${m.daysSinceLast} days → a tiny PR with a clear message can restart momentum.`;
    return {
      text: `It's been ${m.daysSinceLast} days since the last commit. Ship a tiny PR—one file, one line. I added templates below.`,
      mood: "nudging",
      showCoach, why, metrics: m
    };
  }
  if (m.streak >= 3 && m.avgMsgLen < 20) {
    showCoach = true;
    why = `You're on a ${m.streak}-day streak, but messages average ${m.avgMsgLen} chars → templates help clarity.`;
    return {
      text: `🔥 ${m.streak}-day streak. Your messages are short (avg ${m.avgMsgLen}). Try a template for future-you.`,
      mood: "thinking",
      showCoach, why, metrics: m
    };
  }
  if (m.pctConventional < 30 && m.avgMsgLen >= 20) {
    showCoach = true;
    why = `Only ${m.pctConventional}% of recent commits use Conventional Commits → templates speed consistent messages.`;
    return {
      text: `Good detail (avg ${m.avgMsgLen}). Boost consistency with a "feat:" or "fix:" template below.`,
      mood: "encouraging",
      showCoach, why, metrics: m
    };
  }

  const last = commits[0];
  const msg = (last?.commit?.message || "").trim();
  const teaser = msg.length > 30 ? msg.slice(0, 30) + "..." : msg || "your last commit";
  return {
    text: `Nice push on "${teaser}". Keep the rhythm: one focused change, one clear message.`,
    mood: "celebrating",
    showCoach, why, metrics: m
  };
}

function speak(text) {
  if (!chrome.tts) return;
  chrome.tts.speak(text, { rate: 0.95, pitch: 1.05, voiceName: 'Google US English' });
}

async function analyzeRepoFromUrl(url) {
  const repo = parseRepoFromUrl(url);
  if (!repo) throw new Error("Not on a GitHub repo page.");
  const res = await fetch(`https://api.github.com/repos/${repo}/commits?per_page=50`);
  if (!res.ok) throw new Error(`GitHub API error: ${res.status}`);
  const commits = await res.json();
  return makeFeedback(commits);
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === 'ANALYZE_CURRENT_REPO') {
    (async () => {
      try {
        const feedback = await analyzeRepoFromUrl(msg.url);
        speak(feedback.text);
        sendResponse({ ok: true, ...feedback });
      } catch (e) {
        const fallback = {
          text: "I’m having trouble reading this repo right now, but you can still ship a tiny improvement.",
          mood: "encouraging",
          showCoach: true,
          why: "API error or rate limit → keep moving with a template commit.",
          metrics: { daysSinceLast: null, streak: null, avgMsgLen: null, pctConventional: null }
        };
        speak(fallback.text);
        sendResponse({ ok: false, error: String(e), ...fallback });
      }
    })();
    return true;
  }
});
