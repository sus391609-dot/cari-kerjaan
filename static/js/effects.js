// RUMAH KARIR — cursor particle effects + scroll-reveal animations.
//
// Two independent enhancements:
//   1) #cursor-particles: a lightweight canvas particle field that gently
//      gravitates toward the mouse cursor (antigravity-style — particles drift
//      with subtle pull/repulsion to the pointer).
//   2) Scroll reveal: auto-tags eligible elements with `.reveal` and uses
//      IntersectionObserver to add `.in` when they scroll into view.

(function () {
  'use strict';

  const prefersReduced =
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------------- Cursor Particles ----------------
  function initParticles() {
    if (prefersReduced) return;
    // Don't run on tiny screens (mobile) — saves battery, reduces noise.
    if (window.innerWidth < 720) return;

    const canvas = document.createElement('canvas');
    canvas.id = 'cursor-particles';
    canvas.setAttribute('aria-hidden', 'true');
    document.body.appendChild(canvas);

    const ctx = canvas.getContext('2d', { alpha: true });
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0, h = 0;
    const mouse = { x: -9999, y: -9999, active: false };

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener('resize', resize, { passive: true });

    window.addEventListener('mousemove', (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
    }, { passive: true });
    window.addEventListener('mouseout', () => { mouse.active = false; });
    window.addEventListener('blur', () => { mouse.active = false; });

    // Particle field
    const count = Math.max(40, Math.min(110, Math.floor((w * h) / 22000)));
    const particles = [];
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        r: Math.random() * 1.4 + 0.6,
        // soft grayscale; some particles slightly cooler
        hue: 220 + Math.random() * 20,
        light: 70 + Math.random() * 25,
        alpha: 0.35 + Math.random() * 0.45,
      });
    }

    const LINK_DIST = 130;       // px — link nearby particles
    const MOUSE_DIST = 180;      // px — interaction radius
    const ATTRACT = 0.022;       // strength of pull toward cursor

    function step() {
      ctx.clearRect(0, 0, w, h);

      // Optional soft glow under cursor
      if (mouse.active) {
        const grad = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, 220);
        grad.addColorStop(0, 'rgba(200, 210, 230, 0.10)');
        grad.addColorStop(1, 'rgba(200, 210, 230, 0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(mouse.x, mouse.y, 220, 0, Math.PI * 2);
        ctx.fill();
      }

      // Update + draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        if (mouse.active) {
          const dx = mouse.x - p.x;
          const dy = mouse.y - p.y;
          const dist2 = dx * dx + dy * dy;
          if (dist2 < MOUSE_DIST * MOUSE_DIST) {
            const dist = Math.sqrt(dist2) || 0.0001;
            const force = ((MOUSE_DIST - dist) / MOUSE_DIST) * ATTRACT;
            p.vx += (dx / dist) * force;
            p.vy += (dy / dist) * force;
          }
        }

        // damping + drift
        p.vx *= 0.96;
        p.vy *= 0.96;
        p.x += p.vx;
        p.y += p.vy;

        // wrap around edges with margin
        if (p.x < -20) p.x = w + 20;
        if (p.x > w + 20) p.x = -20;
        if (p.y < -20) p.y = h + 20;
        if (p.y > h + 20) p.y = -20;

        // Draw point
        ctx.fillStyle = `hsla(${p.hue}, 8%, ${p.light}%, ${p.alpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw links between near particles + to cursor
      ctx.lineWidth = 0.6;
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < LINK_DIST * LINK_DIST) {
            const d = Math.sqrt(d2);
            const t = 1 - d / LINK_DIST;
            ctx.strokeStyle = `rgba(190, 200, 220, ${0.10 * t})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
        if (mouse.active) {
          const dx = a.x - mouse.x;
          const dy = a.y - mouse.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < MOUSE_DIST * MOUSE_DIST) {
            const d = Math.sqrt(d2);
            const t = 1 - d / MOUSE_DIST;
            ctx.strokeStyle = `rgba(230, 234, 240, ${0.22 * t})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.stroke();
          }
        }
      }

      requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }

  // ---------------- Scroll Reveal ----------------
  function initScrollReveal() {
    const REVEAL_CLASSES = ['reveal', 'reveal-left', 'reveal-right', 'reveal-scale'];
    const hasReveal = (el) => REVEAL_CLASSES.some((c) => el.classList.contains(c));

    // Tag a sane default set: every <section class="section"> inside <main>,
    // plus the Indonesia map container (handled with a scale-in).
    function tag() {
      document.querySelectorAll('main .section').forEach((el) => {
        if (!hasReveal(el)) el.classList.add('reveal');
      });
      document.querySelectorAll('.id-map').forEach((el) => {
        if (!hasReveal(el)) el.classList.add('reveal-scale');
      });
    }

    // Reduced-motion / no-IO fallback: just show everything immediately.
    if (prefersReduced || !('IntersectionObserver' in window)) {
      tag();
      document
        .querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale')
        .forEach((el) => el.classList.add('in'));
      return;
    }

    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.04 });

    function observeAll() {
      document
        .querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale')
        .forEach((el) => {
          if (!el.dataset.ioObserved) {
            el.dataset.ioObserved = '1';
            io.observe(el);
          }
        });
    }

    tag();
    observeAll();

    // Safety net: if for any reason an element above the fold doesn't trigger
    // the observer (e.g. layout shift from async-loaded SVG/iframe), reveal it
    // anyway after a short grace period. Anything still below the fold will
    // continue to wait for the user to scroll into view.
    setTimeout(() => {
      const vh = window.innerHeight || document.documentElement.clientHeight;
      document
        .querySelectorAll('.reveal:not(.in), .reveal-left:not(.in), .reveal-right:not(.in), .reveal-scale:not(.in)')
        .forEach((el) => {
          const r = el.getBoundingClientRect();
          if (r.top < vh * 0.98 && r.bottom > 0) el.classList.add('in');
        });
    }, 600);

    // Final fallback: after 5s, force-reveal everything regardless of state so
    // no content is ever stuck invisible (e.g. dynamic content that mounted
    // late and never tripped the observer).
    setTimeout(() => {
      document
        .querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale')
        .forEach((el) => el.classList.add('in'));
    }, 5000);
  }

  // ---------------- Magnetic Buttons (tiny micro-interaction) ----------------
  function initMagneticButtons() {
    if (prefersReduced) return;
    document.querySelectorAll('.btn').forEach((btn) => {
      btn.addEventListener('mousemove', (e) => {
        const r = btn.getBoundingClientRect();
        const x = e.clientX - r.left - r.width / 2;
        const y = e.clientY - r.top - r.height / 2;
        btn.style.transform = `translate(${x * 0.08}px, ${y * 0.12}px)`;
      });
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = '';
      });
    });
  }

  // ---------------- Boot ----------------
  function boot() {
    try { initParticles(); } catch (e) { console.warn('[effects] particles failed:', e); }
    try { initScrollReveal(); } catch (e) { console.warn('[effects] scroll-reveal failed:', e); }
    try { initMagneticButtons(); } catch (e) { console.warn('[effects] magnetic buttons failed:', e); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  // Re-run reveal init on `load` too so async-loaded SVGs/iframes don't leave
  // any element stuck invisible.
  window.addEventListener('load', () => {
    try { initScrollReveal(); } catch (e) { console.warn('[effects] reveal re-init failed:', e); }
  });
})();
