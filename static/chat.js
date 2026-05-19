// chat.js — main dashboard
'use strict';

const TYPING_STATUSES = [
  'Analyzing viral trends…',
  'Researching social platforms…',
  'Scanning TikTok hooks…',
  'Curating angles for you…',
  'Forging your response…',
];

const TRENDS = [
  { tag: 'TikTok', title: 'NPC livestream skits', desc: 'Dominating short-form engagement this week.', prompt: 'Give me 5 NPC livestream skit ideas I can record today.' },
  { tag: 'Reels', title: 'Glow-up transformations', desc: 'Fast-cut before/after edits with trending audio.', prompt: 'Write a glow-up transformation Reel script with a strong hook.' },
  { tag: 'Shorts', title: 'POV emotional storytelling', desc: 'Quiet hooks, big emotional payoffs.', prompt: 'Outline a 45-second YouTube Shorts POV story about overcoming failure.' },
  { tag: 'Niche', title: 'Street interview rage content', desc: 'High engagement in Naija TikTok.', prompt: 'Generate 7 street interview question ideas for Lagos creators.' },
  { tag: 'Hashtags', title: 'Sigma grind resurgence', desc: 'Carousel + reel hashtag stack.', prompt: 'Build a hashtag strategy for sigma grind content on Instagram.' },
  { tag: 'Growth', title: 'Relatable broke-student content', desc: 'Performing strongly in Nigeria.', prompt: 'Suggest a 7-day posting plan around broke-student humor.' },
  { tag: 'Hook', title: '"Bro had no idea…"', desc: 'Surprise ending skits going viral.', prompt: 'Write 5 hooks that start with "Bro had no idea…"' },
];

const CHAT_STATE = {
  mode: 'normal', // greeting | normal | main (UI-only)
  history: [],
};

function $(s, r = document) { return r.querySelector(s); }
function $$(s, r = document) { return Array.from(r.querySelectorAll(s)); }

function escapeHTML(s) {
  return s.replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}

// minimal markdown: headings, bold, italic, inline code, code blocks, lists
function renderMarkdown(src) {
  let s = escapeHTML(src);
  s = s.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code.trim()}</code></pre>`);
  s = s.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  s = s.replace(/^### (.*)$/gm, '<h3>$1</h3>');
  s = s.replace(/^## (.*)$/gm, '<h2>$1</h2>');
  s = s.replace(/^# (.*)$/gm, '<h1>$1</h1>');
  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|\s)\*([^*\n]+)\*/g, '$1<em>$2</em>');
  // lists
  s = s.replace(/(?:^|\n)((?:[-*] .*(?:\n|$))+)/g, (_, block) => {
    const items = block.trim().split(/\n/).map(l => `<li>${l.replace(/^[-*]\s+/, '')}</li>`).join('');
    return `\n<ul>${items}</ul>`;
  });
  s = s.replace(/(?:^|\n)((?:\d+\. .*(?:\n|$))+)/g, (_, block) => {
    const items = block.trim().split(/\n/).map(l => `<li>${l.replace(/^\d+\.\s+/, '')}</li>`).join('');
    return `\n<ol>${items}</ol>`;
  });
  // paragraphs / line breaks
  s = s.replace(/\n{2,}/g, '</p><p>');
  s = s.replace(/\n/g, '<br/>');
  return `<p>${s}</p>`;
}

function timeNow() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function hideEmpty() { const es = $('#empty-state'); if (es) es.style.display = 'none'; }

function addMessage({ role, content, isHTML = false }) {
  hideEmpty();
  const stream = $('#chat-stream');
  const msg = document.createElement('div');
  msg.className = `msg ${role}`;
  const who = role === 'user'
    ? (document.querySelector('meta[name="username"]').content || 'You')
    : 'TrendForge AI';
  msg.innerHTML = `
    <div class="msg-meta">${escapeHTML(who)} · ${timeNow()}</div>
    <div class="bubble">${isHTML ? content : escapeHTML(content)}</div>
    ${role === 'ai' ? `
      <div class="msg-actions">
        <button data-act="copy">📋 Copy</button>
        <button data-act="share">↗ Share</button>
      </div>` : ''}
  `;
  stream.appendChild(msg);
  stream.scrollTop = stream.scrollHeight;

  if (role === 'ai') {
    msg.querySelector('[data-act="copy"]').addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(msg.querySelector('.bubble').innerText); toast('Copied.'); }
      catch { toast('Copy failed.', 'error'); }
    });
    msg.querySelector('[data-act="share"]').addEventListener('click', () => {
      const cap = $('#share-caption'); if (cap) cap.value = msg.querySelector('.bubble').innerText.slice(0, 280);
      document.getElementById('share-modal').setAttribute('aria-hidden', 'false');
    });
  }
  return msg;
}

function addTypingBubble() {
  hideEmpty();
  const stream = $('#chat-stream');
  const msg = document.createElement('div');
  msg.className = 'msg ai';
  msg.dataset.typing = '1';
  msg.innerHTML = `
    <div class="msg-meta">TrendForge AI · ${timeNow()}</div>
    <div class="bubble">
      <span class="typing-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span>
      <span class="typing-status">${TYPING_STATUSES[0]}</span>
    </div>`;
  stream.appendChild(msg);
  stream.scrollTop = stream.scrollHeight;

  let i = 0;
  const st = msg.querySelector('.typing-status');
  const itv = setInterval(() => {
    i = (i + 1) % TYPING_STATUSES.length;
    if (st) st.textContent = TYPING_STATUSES[i];
  }, 1400);
  msg._stop = () => clearInterval(itv);
  return msg;
}

function streamInto(targetEl, text) {
  // pseudo-stream: reveal word by word
  return new Promise(resolve => {
    const html = renderMarkdown(text);
    targetEl.innerHTML = html;
    targetEl.style.opacity = '0';
    requestAnimationFrame(() => { targetEl.style.transition = 'opacity .25s'; targetEl.style.opacity = '1'; resolve(); });
  });
}

/* ---------- Send ---------- */
async function sendMessage(raw) {
  const message = (raw || '').trim();
  if (!message) return;
  addMessage({ role: 'user', content: message });
  const input = $('#chat-input'); input.value = ''; autosize(input);

  const typing = addTypingBubble();
  try {
    const res = await API.chat(message);
    typing._stop && typing._stop();
    typing.remove();

    let reply = '';
    if (res.mode === 'greeting') {
      const name = document.querySelector('meta[name="username"]').content || 'creator';
      const m = res.message || `Hello ${name}!`;
      reply = m;
    } else {
      reply = (typeof res.reply === 'string') ? res.reply : JSON.stringify(res.reply);
    }
    const m = addMessage({ role: 'ai', content: renderMarkdown(reply), isHTML: true });
    // soft fade
    const bub = m.querySelector('.bubble'); bub.style.opacity = '0'; requestAnimationFrame(() => { bub.style.transition = 'opacity .3s'; bub.style.opacity = '1'; });
  } catch (e) {
    typing._stop && typing._stop();
    typing.remove();
    if (e.status === 401) {
      toast('Please sign in again.', 'error');
      setTimeout(() => { window.location.href = '/login'; }, 800);
      return;
    }
    addMessage({ role: 'ai', content: `⚠️ ${e.message || 'Something went wrong.'}` });
  }
}

/* ---------- Composer ---------- */
function autosize(t) {
  t.style.height = 'auto'; t.style.height = Math.min(t.scrollHeight, 200) + 'px';
}

function initComposer() {
  const form = $('#chat-form'); if (!form) return;
  const input = $('#chat-input');
  input.addEventListener('input', () => autosize(input));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); }
  });
  form.addEventListener('submit', (e) => { e.preventDefault(); sendMessage(input.value); });

  $$('.chip').forEach(c => c.addEventListener('click', () => {
    input.value = c.dataset.prefill; autosize(input); input.focus();
  }));

  // voice
  const vb = $('#voice-btn');
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { vb.disabled = true; vb.title = 'Voice not supported in this browser'; vb.style.opacity = .4; return; }
  const rec = new SR(); rec.continuous = false; rec.interimResults = false; rec.lang = navigator.language || 'en-US';
  let listening = false;
  vb.addEventListener('click', () => {
    if (listening) { rec.stop(); return; }
    try { rec.start(); listening = true; vb.textContent = '⏺'; }
    catch { toast('Voice unavailable.', 'error'); }
  });
  rec.onresult = (ev) => { input.value = (input.value ? input.value + ' ' : '') + ev.results[0][0].transcript; autosize(input); };
  rec.onend = () => { listening = false; vb.textContent = '🎙'; };
  rec.onerror = () => { listening = false; vb.textContent = '🎙'; };
}

/* ---------- Mode switch (UI only, backend auto-detects) ---------- */
function initModes() {
  const wrap = $('.mode-switch'); if (!wrap) return;
  wrap.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-mode]'); if (!b) return;
    CHAT_STATE.mode = b.dataset.mode;
    $$('.mode-switch button').forEach(x => x.classList.toggle('active', x === b));
    const sub = $('#hello-sub');
    const map = {
      greeting: 'Greeting mode · quick hellos and small talk.',
      normal: 'Normal mode · ideas, captions, summaries.',
      main: 'Main mode · full scripts and deep research.',
    };
    if (sub) sub.textContent = map[CHAT_STATE.mode];
  });
}

/* ---------- Sidebar mobile ---------- */
function initSidebar() {
  const ts = $('#toggle-side'); const side = $('#side');
  if (ts && side) ts.addEventListener('click', () => side.classList.toggle('open'));
}

/* ---------- Trends sidebar ---------- */
function renderTrends() {
  const wrap = $('#trend-cards'); if (!wrap) return;
  wrap.innerHTML = '';
  TRENDS.slice().sort(() => Math.random() - .5).forEach(t => {
    const el = document.createElement('div');
    el.className = 'trend-card';
    el.innerHTML = `<div class="tag">${t.tag}</div><div class="title">${t.title}</div><div class="desc">${t.desc}</div>`;
    el.addEventListener('click', () => {
      const input = $('#chat-input'); input.value = t.prompt; autosize(input); input.focus();
    });
    wrap.appendChild(el);
  });
}
function initTrends() {
  renderTrends();
  const r = $('#refresh-trends'); if (r) r.addEventListener('click', renderTrends);
}

/* ---------- Comments ---------- */
function fmtWhen(iso) {
  try { return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }); }
  catch { return iso || ''; }
}
async function loadComments() {
  const list = $('#comment-list'); if (!list) return;
  try {
    const res = await API.comments.list();
    const items = (res && res.data) || [];
    list.innerHTML = items.length ? '' : '<li class="comment-item muted small">Be the first to share something.</li>';
    items.forEach(c => {
      const li = document.createElement('li');
      li.className = 'comment-item';
      li.innerHTML = `<div><span class="who">${escapeHTML(c.username || 'Anon')}</span><span class="when">${fmtWhen(c.created_at)}</span></div><div class="what">${escapeHTML(c.content || '')}</div>`;
      list.appendChild(li);
    });
  } catch (e) {
    list.innerHTML = `<li class="comment-item muted small">Couldn't load comments.</li>`;
  }
}
function initComments() {
  const form = $('#comment-form'); if (!form) return;
  loadComments();
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = $('#comment-input'); const val = input.value.trim();
    if (!val) return;
    try {
      await API.comments.add(val); input.value = '';
      toast('Posted to the Creator Wall.');
      loadComments();
    } catch (err) {
      if (err.status === 401) { toast('Sign in to post.', 'error'); return; }
      toast(err.message || 'Could not post.', 'error');
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initComposer();
  initModes();
  initSidebar();
  initTrends();
  initComments();
});
