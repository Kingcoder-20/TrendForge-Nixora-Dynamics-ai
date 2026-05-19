// auth.js — login + signup
'use strict';

function showError(el, msg) { if (!el) return; el.textContent = msg; el.hidden = false; }
function clearError(el) { if (!el) return; el.hidden = true; el.textContent = ''; }

document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');

  if (loginForm) {
    const err = document.getElementById('login-error');
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault(); clearError(err);
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      if (!email || !password) return showError(err, 'Please fill in both fields.');
      const btn = loginForm.querySelector('button[type=submit]');
      btn.disabled = true; const old = btn.textContent; btn.textContent = 'Signing in…';
      try {
        const res = await API.login({ email, password });
        const data = res && res.data;
        window.location.href = (data && data.redirect) || '/chat';
      } catch (e2) {
        showError(err, e2.message || 'Could not sign in.');
        btn.disabled = false; btn.textContent = old;
      }
    });
  }

  if (signupForm) {
    const err = document.getElementById('signup-error');
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault(); clearError(err);
      const username = document.getElementById('username').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      if (username.length < 3) return showError(err, 'Username must be at least 3 characters.');
      if (!email.includes('@')) return showError(err, 'Please enter a valid email.');
      if (password.length < 8) return showError(err, 'Password must be at least 8 characters.');
      const btn = signupForm.querySelector('button[type=submit]');
      btn.disabled = true; const old = btn.textContent; btn.textContent = 'Creating…';
      try {
        await API.signup({ username, email, password });
        // backend doesn't auto-login on signup; route to login
        toast && toast('Account created. Please sign in.');
        setTimeout(() => { window.location.href = '/login'; }, 600);
      } catch (e2) {
        showError(err, e2.message || 'Could not create account.');
        btn.disabled = false; btn.textContent = old;
      }
    });
  }
});
