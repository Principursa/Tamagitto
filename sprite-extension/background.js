// background.js — smart metric v3: variety via deterministic cycling

function parseRepoFromUrl(url) {
  const m = url.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  if (!m) return null;
  return `${m[1]}/${m[2]}`;
}

// ---- Metrics helpers ----
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
    if (byDay.has(day.getTime())) streak++; else { if (i === 0) continue; break; }
  }

  const msgs = commits.slice(0, 20).map(c => (c.commit.message || '').trim());
  const avgMsgLen = msgs.length ? Math.round(msgs.reduce((a,b)=>a+b.length,0) / msgs.length) : 0;
  const cc = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?:\s/i;
  const conventionalHits = msgs.filter(m => cc.test(m)).length;
  const pctConventional = msgs.length ? Math.round(100 * conventionalHits / msgs.length) : 0;

  return { daysSinceLast, streak, avgMsgLen, pctConventional };
}

// ---- Variety pools per case (no randomness; we cycle) ----
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
    why: (m) => `Only ${m.pctConventional}% use Conventional Commits → templates speed consistent messages.`
  },
  DEFAULT: {
    mood: "celebrating",
    // We’ll include a teaser in runtime
    lines: [
      "Nice push. Keep the rhythm: one focused change, one clear message.",
      "Solid pace—aim for a tiny PR before you leave this page.",
      "Ship it small, ship it clear. You’re close."
    ],
    why: () => ""
  }
};

// Deterministic cycling per repo+case
async function pickLine(repo, caseKey, pool) {
  const key = `cc-cycle-${repo}-${caseKey}`;
  const { [key]: idx = 0 } = await chrome.storage.local.get(key);
  const line = pool.lines[idx % pool.lines.length];
  // bump index (wrap)
  const next = (idx + 1) % pool.lines.length;
  await chrome.storage.local.set({ [key]: next });
  return line;
}

function classifyCase(m) {
  if (m.daysSinceLast > 3) return "QUIET";
  if (m.streak >= 3 && m.avgMsgLen < 20) return "STREAK_SHORT_MSG";
  if (m.pctConventional < 30 && m.avgMsgLen >= 20) return "LOW_CONVENTIONAL";
  return "DEFAULT";
}

async function makeFeedback(repo, commits) {
  const m = computeMetrics(commits);
  const caseKey = classifyCase(m);
  const pool = POOLS[caseKey];

  let text = await pickLine(repo, caseKey, pool);
  if (caseKey === "DEFAULT") {
    const last = commits[0];
    const msg = (last?.commit?.message || "").trim();
    const teaser = msg.length > 30 ? msg.slice(0, 30) + "..." : msg || "your last commit";
    text = `“${teaser}” — ${text}`;
  }

  const why = pool.why(m);
  return { text, mood: pool.mood, showCoach: caseKey !== "DEFAULT", why, metrics: m };
}

// Speak with Chrome TTS if available
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
  return makeFeedback(repo, commits);
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
          text: "Trouble talking to GitHub, but you can still ship a tiny improvement.",
          mood: "encouraging",
          showCoach: true,
          why: "API error or rate limit → use a template and keep moving.",
          metrics: {}
        };
        speak(fallback.text);
        sendResponse({ ok: false, error: String(e), ...fallback });
      }
    })();
    return true;
  }
});
