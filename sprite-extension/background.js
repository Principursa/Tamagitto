// background.js (MV3 service worker) — smart metric v1

function parseRepoFromUrl(url) {
  const m = url.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  if (!m) return null;
  return `${m[1]}/${m[2]}`;
}

// --- Metrics helpers ---
function dateOnly(iso) {
  const d = new Date(iso);
  return new Date(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()); // local midnight ok for streak logic
}

function computeMetrics(commits) {
  if (!Array.isArray(commits) || commits.length === 0) {
    return { daysSinceLast: Infinity, streak: 0, avgMsgLen: 0, pctConventional: 0 };
  }

  // Sort newest -> oldest (GitHub already does, but be safe)
  commits = commits.slice().sort((a,b) => new Date(b.commit.author.date) - new Date(a.commit.author.date));

  // daysSinceLast
  const lastDate = new Date(commits[0].commit.author.date);
  const now = new Date();
  const daysSinceLast = Math.floor((now - lastDate) / (1000*60*60*24));

  // Build a Set of commit days (date-only)
  const byDay = new Set(commits.map(c => dateOnly(c.commit.author.date).getTime()));

  // streak (consecutive days up to today)
  let streak = 0;
  for (let i = 0; i < 30; i++) { // cap at 30 for sanity
    const day = new Date();
    day.setHours(0,0,0,0);
    day.setDate(day.getDate() - i);
    if (byDay.has(day.getTime())) {
      streak++;
    } else {
      if (i === 0) { /* allow that you might not have committed yet today */ continue; }
      break;
    }
  }

  // avg commit message length (last 20)
  const msgs = commits.slice(0, 20).map(c => (c.commit.message || '').trim());
  const avgMsgLen = msgs.length ? Math.round(msgs.reduce((a,b)=>a+b.length,0) / msgs.length) : 0;

  // % conventional-commit style
  const cc = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?:\s/i;
  const conventionalHits = msgs.filter(m => cc.test(m)).length;
  const pctConventional = msgs.length ? Math.round(100 * conventionalHits / msgs.length) : 0;

  return { daysSinceLast, streak, avgMsgLen, pctConventional };
}

function makeFeedback(commits) {
  const m = computeMetrics(commits);

  // Prioritized, specific nudges
  if (m.daysSinceLast > 3) {
    return {
      text: `Repo's been quiet for ${m.daysSinceLast} days. Ship a tiny PR today—one file, one clear message.`,
      mood: "nudging"
    };
  }
  if (m.streak >= 3 && m.avgMsgLen < 20) {
    return {
      text: `🔥 ${m.streak}-day streak, but commit messages are terse (avg ${m.avgMsgLen} chars). Add a verb + object for future-you.`,
      mood: "thinking"
    };
  }
  if (m.pctConventional < 30 && m.avgMsgLen >= 20) {
    return {
      text: `Good detail (avg ${m.avgMsgLen} chars) but only ${m.pctConventional}% use Conventional Commits. Try "feat: …" or "fix: …".`,
      mood: "encouraging"
    };
  }

  // Nice default praise with teaser
  const last = commits[0];
  const msg = (last?.commit?.message || "").trim();
  const teaser = msg.length > 30 ? msg.slice(0, 30) + "..." : msg || "your last commit";
  return {
    text: `Nice push on "${teaser}". Keep the rhythm: aim for one focused change and a clear message.`,
    mood: "celebrating"
  };
}

// Speak with Chrome TTS if available
function speak(text) {
  if (!chrome.tts) return;
  chrome.tts.speak(text, { rate: 0.95, pitch: 1.05, voiceName: 'Google US English' });
}

async function analyzeRepoFromUrl(url) {
  const repo = parseRepoFromUrl(url);
  if (!repo) throw new Error("Not on a GitHub repo page.");
  // Pull more commits so metrics are meaningful
  const res = await fetch(`https://api.github.com/repos/${repo}/commits?per_page=50`);
  if (!res.ok) throw new Error(`GitHub API error: ${res.status}`);
  const commits = await res.json();
  return makeFeedback(commits);
}

// Message router
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
          mood: "encouraging"
        };
        speak(fallback.text);
        sendResponse({ ok: false, error: String(e), ...fallback });
      }
    })();
    return true; // keep channel open for async response
  }
});
