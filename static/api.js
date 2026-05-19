// api.js — fetch wrapper, Flask-session-safe
'use strict';

const API = (() => {
  async function request(url, options = {}) {
    const opts = {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    };
    if (opts.body && typeof opts.body !== 'string') opts.body = JSON.stringify(opts.body);
    const res = await fetch(url, opts);
    const ct = res.headers.get('content-type') || '';
    const data = ct.includes('application/json') ? await res.json().catch(() => ({})) : await res.text();
    if (!res.ok) {
      const msg = (data && data.error) || `Request failed (${res.status})`;
      const err = new Error(msg);
      err.status = res.status; err.data = data;
      throw err;
    }
    return data;
  }
  return {
    get: (u) => request(u, { method: 'GET' }),
    post: (u, body) => request(u, { method: 'POST', body }),
    health: () => request('/health', { method: 'GET' }),
    signup: (b) => request('/api/signup', { method: 'POST', body: b }),
    login: (b) => request('/api/login', { method: 'POST', body: b }),
    chat: (msg) => request('/api/chat', { method: 'POST', body: { user_message: msg } }),
    comments: {
      list: () => request('/api/comments', { method: 'GET' }),
      add: (content) => request('/api/comments', { method: 'POST', body: { content } }),
    },
  };
})();

async function startHealthPolling() {
  const pills = document.querySelectorAll('#health-pill');
  if (!pills.length) return;
  const update = async () => {
    try {
      await API.health();
      pills.forEach(p => { p.classList.remove('bad'); p.classList.add('ok'); p.innerHTML = '<span class="dot"></span> Backend online'; });
    } catch {
      pills.forEach(p => { p.classList.remove('ok'); p.classList.add('bad'); p.innerHTML = '<span class="dot"></span> Offline'; });
    }
  };
  update();
  setInterval(update, 30000);
}
