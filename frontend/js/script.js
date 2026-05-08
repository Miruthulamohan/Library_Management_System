/* Library Management System — Shared JS */

const API = `${location.origin}/api`;

// ── Storage helpers ───────────────────────────────────────────────────────
const getToken = ()  => localStorage.getItem('lms_token');
const getUser  = ()  => { try { return JSON.parse(localStorage.getItem('lms_user')); } catch { return null; } };
const setAuth  = (token, user) => {
  localStorage.setItem('lms_token', token);
  localStorage.setItem('lms_user', JSON.stringify(user));
};
const clearAuth = () => {
  localStorage.removeItem('lms_token');
  localStorage.removeItem('lms_user');
};

// ── Auth guard ────────────────────────────────────────────────────────────
function requireAuth(role = null) {
  const token = getToken(), user = getUser();
  if (!token || !user) { location.href = '/login.html'; return false; }
  if (role && user.role !== role) {
    location.href = user.role === 'admin' ? '/admin/dashboard.html' : '/student/dashboard.html';
    return false;
  }
  return true;
}

function logout() {
  clearAuth();
  location.href = '/login.html';
}

// ── Fetch wrapper ─────────────────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${API}${endpoint}`, {
      headers: { 'Content-Type':'application/json', 'Authorization':`Bearer ${getToken()}` },
      ...options
    });
    if (res.status === 401) { logout(); return null; }
    // Backend may return non-JSON bodies on 4xx/5xx (e.g. Flask error page).
    // Avoid throwing during `res.json()` so callers can still show a meaningful error.
    let data = null;
    try {
      data = await res.json();
    } catch {
      const text = await res.text().catch(() => '');
      data = text ? { error: text } : null;
    }
    return { ok: res.ok, status: res.status, data };
  } catch {
    showToast('Cannot connect to server. Is Flask running?', 'error');
    return null;
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  document.getElementById('lms-toast')?.remove();
  const colors = { success:'#10b981', error:'#ef4444', info:'#4f46e5', warning:'#f59e0b' };
  const el = document.createElement('div');
  el.id = 'lms-toast';
  el.textContent = msg;
  Object.assign(el.style, {
    position:'fixed', bottom:'80px', right:'20px', background:colors[type]||colors.info,
    color:'#fff', padding:'12px 20px', borderRadius:'10px', fontSize:'14px',
    zIndex:'9999', boxShadow:'0 4px 16px rgba(0,0,0,.18)', maxWidth:'320px',
    opacity:'0', transition:'opacity .25s, transform .25s', transform:'translateY(8px)'
  });
  document.body.appendChild(el);
  requestAnimationFrame(() => { el.style.opacity='1'; el.style.transform='translateY(0)'; });
  setTimeout(() => {
    el.style.opacity='0'; el.style.transform='translateY(8px)';
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

// ── Modal helpers ─────────────────────────────────────────────────────────
function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});

// ── Utilities ─────────────────────────────────────────────────────────────
function parseDateTime(d) {
  if (!d) return null;
  if (d instanceof Date) return isNaN(d.getTime()) ? null : d;
  if (typeof d === 'number') {
    const dt = new Date(d);
    return isNaN(dt.getTime()) ? null : dt;
  }

  const s = String(d).trim();
  if (!s) return null;

  // Date-only (MySQL DATE): YYYY-MM-DD (no timezone)
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (m) {
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 0, 0, 0, 0);
  }

  // DateTime (MySQL TIMESTAMP/DATETIME): YYYY-MM-DD HH:mm:ss(.SSS)?
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?$/);
  if (m) {
    const y  = Number(m[1]);
    const mo = Number(m[2]) - 1;
    const da = Number(m[3]);
    const hh = Number(m[4]);
    const mm = Number(m[5]);
    const ss = m[6] !== undefined ? Number(m[6]) : 0;
    // MySQL returns TIMESTAMP/DATETIME strings without timezone info.
    // The server runs in IST and the browser is also in IST (local time).
    // Parse the components directly as local time — no offset math needed.
    const dt = new Date(y, mo, da, hh, mm, ss, 0);
    return isNaN(dt.getTime()) ? null : dt;
  }

  // Fallback (ISO strings, etc.)
  const dt = new Date(s);
  return isNaN(dt.getTime()) ? null : dt;
}

function formatDate(d) {
  const dt = parseDateTime(d);
  if (!dt) return '—';
  return dt.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' });
}
function formatTime(d) {
  const dt = parseDateTime(d);
  if (!dt) return '';
  return dt.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', hour12: true });
}
function formatDateTime(d) {
  const dt = parseDateTime(d);
  if (!dt) return '—';
  const date = dt.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' });
  const time = dt.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', hour12: true });
  return date + ', ' + time;
}
function formatAmount(a) { return `Rs.${parseFloat(a||0).toFixed(2)}`; }
function timeAgo(d) {
  const dt = parseDateTime(d) || (d ? new Date(d) : null);
  if (!dt || isNaN(dt.getTime())) return '';
  const diff = Date.now() - dt.getTime();
  const m = Math.floor(diff/60000);
  if (m < 1)  return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m/60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h/24)}d ago`;
}
function debounce(fn, ms=300) {
  let t; return (...a) => { clearTimeout(t); t=setTimeout(()=>fn(...a),ms); };
}

// ── Notification badge ────────────────────────────────────────────────────
async function loadNotifBadge() {
  const badge = document.getElementById('notif-badge');
  if (!badge || !getToken()) return;
  const r = await apiFetch('/notifications/unread-count');
  if (r?.ok && r.data.count > 0) {
    badge.textContent = r.data.count;
    badge.style.display = 'inline';
  } else {
    badge.style.display = 'none';
  }
}

// ── PWA install prompt ────────────────────────────────────────────────────
let deferredPrompt;
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  deferredPrompt = e;
  const bar = document.getElementById('install-bar');
  if (bar) bar.classList.add('show');
});

function installPWA() {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  deferredPrompt.userChoice.then(() => {
    deferredPrompt = null;
    document.getElementById('install-bar')?.classList.remove('show');
  });
}

// Run badge on every page load
window.addEventListener('load', loadNotifBadge);
