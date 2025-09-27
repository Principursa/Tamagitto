// background.js (MV3 service worker)

// Parse owner/repo from a GitHub URL
function parseRepoFromUrl(url) {
  const m = url.match(/github\.com\/([^\/]+)\/([^\/?#]+)(?:[\/?#]|$)/i);
  if (!m) return null;
  return `${m[1]}/${m[2]}`;
}

// Generate a short feedback message + mood from commits array
function makeFeedback(commits) {
  if (!Array.isArray(commits) || commits.length === 0) {
    return { text: "This repo looks quiet. Want to make a tiny commit to get momentum back?", mood: "nudging" };
  }
  const last = commits[0];
  const msg = (last?.commit?.message || "").trim();
  const teaser = msg.length > 30 ? msg.slice(0, 30) + "..." : msg || "your last commit";
  return { text: `Nice push on "${teaser}". What's the next bite-sized change you can ship?`, mood: "celebrating" };
}

// Speak with Chrome TTS if available
function speak(text) {
  if (!chrome.tts) return;
  chrome.tts.speak(text, { rate: 0.95, pitch: 1.05, voiceName: 'Google US English' });
}

async function analyzeRepoFromUrl(url) {
  const repo = parseRepoFromUrl(url);
  if (!repo) throw new Error("Not on a GitHub repo page.");
  const res = await fetch(`https://api.github.com/repos/${repo}/commits?per_page=5`);
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
    return true; // keep the channel open for async response
  }
});
