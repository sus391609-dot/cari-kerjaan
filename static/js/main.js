// Site-wide helpers and small interactions for RUMAH KARIR.

(function () {
  const hamburger = document.querySelector('.hamburger');
  const drawer = document.querySelector('.mobile-drawer');
  const closeBtn = drawer ? drawer.querySelector('.close-x') : null;
  if (hamburger && drawer) {
    hamburger.addEventListener('click', () => drawer.classList.add('open'));
  }
  if (closeBtn && drawer) {
    closeBtn.addEventListener('click', () => drawer.classList.remove('open'));
  }
})();

window.api = async function api(url, opts = {}) {
  const init = Object.assign({ credentials: 'same-origin' }, opts);
  if (init.body && typeof init.body === 'object' && !(init.body instanceof FormData)) {
    init.headers = Object.assign({ 'Content-Type': 'application/json' }, init.headers || {});
    init.body = JSON.stringify(init.body);
  }
  const res = await fetch(url, init);
  let data = null;
  try { data = await res.json(); } catch (_) { data = null; }
  return { ok: res.ok, status: res.status, data };
};

window.formatRp = function (n) {
  if (!n && n !== 0) return '-';
  try { return 'Rp ' + Number(n).toLocaleString('id-ID'); } catch (_) { return '-'; }
};

window.escapeHtml = function (s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
};
