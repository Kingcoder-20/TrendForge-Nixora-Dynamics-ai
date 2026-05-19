// ui.js — themes, drawer, modals, share, ratings, hourly prompts, greeting, quotes, footer
'use strict';

const STORAGE = {
  theme: 'tf:theme',
  firstVisit: 'tf:firstVisit',
  sharePrompted: 'tf:sharePrompted',
  ratingPrompted: 'tf:ratingPrompted',
  rating: 'tf:rating',
  chatHistory: 'tf:chatHistory',
};

const QUOTES = [
  "Show up daily. The algorithm rewards rhythm.",
  "The riches are in the niches.",
  "You're one viral post away. Keep going.",
  "Consistency beats talent. Always.",
  "Creators worldwide are using TrendForge right now.",
  "Post like nobody's watching. They will be.",
  "Done is better than perfect. Hit publish.",
  "Your story is the trend nobody else can copy.",
  "Every scroll is a chance. Make it count.",
  "Thousands of creators trusted TrendForge this week — you're in good company.",
];

function $(sel, root = document) { return root.querySelector(sel); }
function $$(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

function getUsername() {
  const m = document.querySelector('meta[name="username"]');
  return (m && m.content && m.content.trim()) || '';
}
function getEmail() {
  const m = document.querySelector('meta[name="email"]');
  return (m && m.content && m.content.trim()) || '';
}

function toast(msg, type = '') {
  const stack = $('#toast-stack'); if (!stack) return;
  const el = document.createElement('div');
  el.className = 'toast ' + (type || '');
  el.textContent = msg;
  stack.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3200);
}

/* ---------- Theme ---------- */
function applyTheme(name) {
  document.documentElement.setAttribute('data-theme', name);
  localStorage.setItem(STORAGE.theme, name);
  $$('.theme-chip').forEach(c => c.classList.toggle('active', c.dataset.theme === name));
}
function initTheme() {
  const saved = localStorage.getItem(STORAGE.theme) || 'midnight';
  applyTheme(saved);
  $$('.theme-chip').forEach(c => c.addEventListener('click', () => applyTheme(c.dataset.theme)));
}

/* ---------- Drawer + modals ---------- */
function openEl(el) { if (el) el.setAttribute('aria-hidden', 'false'); }
function closeEl(el) { if (el) el.setAttribute('aria-hidden', 'true'); }

function initDrawer() {
  $$('[data-open-drawer]').forEach(b => b.addEventListener('click', () => openEl($('#settings-drawer'))));
  document.addEventListener('click', (e) => {
    if (e.target.matches('[data-close-drawer]')) closeEl($('#settings-drawer'));
    if (e.target.matches('[data-close-modal]')) {
      const m = e.target.closest('.modal'); if (m) closeEl(m);
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { $$('.modal,.drawer').forEach(closeEl); }
  });

  // Profile fill
  const name = getUsername() || 'Creator';
  const mail = getEmail() || '—';
  const pn = $('#profile-name'); if (pn) pn.textContent = name;
  const pe = $('#profile-email'); if (pe) pe.textContent = mail;
  const av = $('#profile-avatar'); if (av) av.textContent = (name[0] || 'U').toUpperCase();

  // Action wires
  const oS = $('#open-share'); if (oS) oS.addEventListener('click', () => openShare());
  const oR = $('#open-rating'); if (oR) oR.addEventListener('click', () => openEl($('#rating-modal')));
  const cH = $('#clear-history'); if (cH) cH.addEventListener('click', () => {
    localStorage.removeItem(STORAGE.chatHistory);
    const stream = $('#chat-stream');
    if (stream) {
      $$('.msg', stream).forEach(m => m.remove());
      const es = $('#empty-state'); if (es) es.style.display = '';
    }
    toast('Chat history cleared on this device.');
  });
}

/* ---------- Share modal ---------- */
function buildCaption() {
  const u = window.location.origin;
  return `I've been using TrendForge AI by Nexora Dynamics to find viral ideas and write scripts fast. You should try it 👉 ${u}`;
}
function openShare() {
  const m = $('#share-modal'); if (!m) return;
  const cap = $('#share-caption'); if (cap) cap.value = buildCaption();
  openEl(m);
}
function initShare() {
  const grid = $('#share-modal .share-grid'); if (!grid) return;
  grid.addEventListener('click', async (e) => {
    const b = e.target.closest('button[data-share]'); if (!b) return;
    const cap = $('#share-caption').value || buildCaption();
    const url = window.location.origin;
    const enc = encodeURIComponent(cap);
    const map = {
      copy: null,
      tiktok: 'https://www.tiktok.com/upload',
      instagram: 'https://www.instagram.com/',
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}&quote=${enc}`,
      x: `https://twitter.com/intent/tweet?text=${enc}`,
      whatsapp: `https://wa.me/?text=${enc}`,
    };
    const target = b.dataset.share;
    if (target === 'copy') {
      try { await navigator.clipboard.writeText(cap); toast('Caption copied to clipboard.'); }
      catch { toast('Could not copy. Select the text manually.', 'error'); }
      return;
    }
    if (target === 'tiktok' || target === 'instagram') {
      try { await navigator.clipboard.writeText(cap); toast('Caption copied — paste it after the app opens.'); } catch {}
    }
    window.open(map[target], '_blank', 'noopener');
  });
}

/* ---------- Rating modal ---------- */
function initRating() {
  const stars = $('#rating-stars'); if (!stars) return;
  let value = parseInt(localStorage.getItem(STORAGE.rating) || '0', 10);
  const paint = () => $$('button', stars).forEach(b => b.classList.toggle('on', parseInt(b.dataset.star, 10) <= value));
  paint();
  stars.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-star]'); if (!b) return;
    value = parseInt(b.dataset.star, 10); paint();
  });
  const submit = $('#submit-rating');
  if (submit) submit.addEventListener('click', () => {
    if (!value) { toast('Pick a star first 🙂'); return; }
    localStorage.setItem(STORAGE.rating, String(value));
    localStorage.setItem(STORAGE.ratingPrompted, '1');
    closeEl($('#rating-modal'));
    toast(`Thank you for the ${value}-star rating!`);
  });
}

/* ---------- Hourly prompts ---------- */
function initHourly() {
  if (!localStorage.getItem(STORAGE.firstVisit)) {
    localStorage.setItem(STORAGE.firstVisit, String(Date.now()));
  }
  const first = parseInt(localStorage.getItem(STORAGE.firstVisit), 10);
  const HOUR = 60 * 60 * 1000;

  const check = () => {
    const elapsed = Date.now() - first;
    if (elapsed >= HOUR && !localStorage.getItem(STORAGE.sharePrompted)) {
      localStorage.setItem(STORAGE.sharePrompted, '1');
      openEl($('#hourly-share'));
    }
    if (elapsed >= 2 * HOUR && !localStorage.getItem(STORAGE.ratingPrompted)) {
      localStorage.setItem(STORAGE.ratingPrompted, '1');
      openEl($('#rating-modal'));
    }
  };
  // staggered checks
  setTimeout(check, 5000);
  setInterval(check, 5 * 60 * 1000);

  const hso = $('#hourly-share-open');
  if (hso) hso.addEventListener('click', () => { closeEl($('#hourly-share')); openShare(); });
}

/* ---------- Greeting + quotes + footer ---------- */
function initGreeting() {
  const name = getUsername();
  const hello = name ? `Welcome, ${name} 👋` : 'Welcome, creator 👋';
  const h = $('#hero-greet'); if (h && name) h.textContent = `Welcome back, ${name}. AI-powered ideas, hooks and full scripts — tuned to what's trending right now.`;
  const hl = $('#hello-line'); if (hl) hl.textContent = hello;
  const eg = $('#empty-greet'); if (eg) eg.textContent = name ? `Hello, ${name}` : 'Hello, creator';
}

function rotateQuotes() {
  const targets = [$('#quote-text'), $('#side-quote')].filter(Boolean);
  if (!targets.length) return;
  let i = 0;
  const tick = () => {
    i = (i + 1) % QUOTES.length;
    targets.forEach(t => { t.style.opacity = '0'; setTimeout(() => { t.textContent = QUOTES[i]; t.style.opacity = '1'; }, 250); });
  };
  targets.forEach(t => { t.style.transition = 'opacity .3s ease'; });
  setInterval(tick, 7000);
}

function initFooter() {
  const f = $('#footer-date'); if (!f) return;
  const d = new Date();
  f.textContent = d.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

/* ---------- Password toggle (shared) ---------- */
function initPwToggle() {
  $$('.toggle-pw').forEach(btn => btn.addEventListener('click', () => {
    const id = btn.dataset.toggle;
    const inp = document.getElementById(id);
    if (!inp) return;
    inp.type = inp.type === 'password' ? 'text' : 'password';
  }));
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initDrawer();
  initShare();
  initRating();
  initHourly();
  initGreeting();
  initFooter();
  initPwToggle();
  rotateQuotes();
  startHealthPolling();
});
