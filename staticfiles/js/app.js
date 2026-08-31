/**
 * Horizon SMS — Ultra Realistic Animation Engine 2026
 * Covers: Particle Canvas, Count-Up, Scroll Reveal, Ripples,
 *         Progress Bar, Command Palette, Theme Switcher, Toasts
 */

/* ============================================================
   THEME ENGINE
   ============================================================ */
(function () {
  const saved = localStorage.getItem('horizon-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
})();

document.addEventListener('DOMContentLoaded', function () {

  /* ============================================================
     1. PAGE PROGRESS BAR
     ============================================================ */
  const bar = document.createElement('div');
  bar.id = 'page-progress';
  document.body.prepend(bar);
  setTimeout(() => { bar.style.opacity = '0'; }, 900);

  /* ============================================================
     2. FLOATING PARTICLE CANVAS
     ============================================================ */
  const canvas = document.createElement('canvas');
  canvas.id = 'particle-canvas';
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d');

  function resizeCanvas() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  const PARTICLE_COUNT = 40;
  const particles = [];

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x = Math.random() * canvas.width;
      this.y = Math.random() * canvas.height;
      this.size = Math.random() * 2.5 + 0.5;
      this.speedX = (Math.random() - 0.5) * 0.4;
      this.speedY = -Math.random() * 0.6 - 0.2;
      this.opacity = Math.random() * 0.4 + 0.1;
      this.decay  = Math.random() * 0.003 + 0.001;
      const colors = ['79,70,229', '124,58,237', '6,182,212', '16,185,129'];
      this.color = colors[Math.floor(Math.random() * colors.length)];
    }
    update() {
      this.x += this.speedX;
      this.y += this.speedY;
      this.opacity -= this.decay;
      if (this.opacity <= 0) this.reset();
    }
    draw() {
      ctx.save();
      ctx.globalAlpha = this.opacity;
      ctx.fillStyle = `rgba(${this.color}, 1)`;
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(new Particle());

  function animateParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => { p.update(); p.draw(); });
    requestAnimationFrame(animateParticles);
  }
  animateParticles();

  /* ============================================================
     3. THEME TOGGLE
     ============================================================ */
  const themeBtn = document.getElementById('themeToggleBtn');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next    = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('horizon-theme', next);
      const icon = themeBtn.querySelector('i');
      if (icon) icon.className = next === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
      themeBtn.style.transform = 'rotate(360deg)';
      setTimeout(() => { themeBtn.style.transform = ''; }, 400);
    });
    // Set correct icon on load
    const savedTheme = localStorage.getItem('horizon-theme') || 'light';
    const icon = themeBtn.querySelector('i');
    if (icon) icon.className = savedTheme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
  }

  /* ============================================================
     4. COUNT-UP ANIMATION
     ============================================================ */
  function animateCountUp(el) {
    const target = parseFloat(el.getAttribute('data-target') || el.textContent.replace(/[^0-9.]/g, ''));
    if (isNaN(target)) return;
    const prefix = el.getAttribute('data-prefix') || '';
    const suffix = el.getAttribute('data-suffix') || '';
    const decimals = target % 1 !== 0 ? 1 : 0;
    const duration = 1800;
    const start = performance.now();

    function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

    function frame(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const value = easeOut(progress) * target;
      el.textContent = prefix + value.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',') + suffix;
      if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  /* ============================================================
     5. INTERSECTION OBSERVER — SCROLL REVEAL + COUNT-UP
     ============================================================ */
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        const el = entry.target;
        // Staggered delay for siblings
        const siblings = Array.from(el.parentElement?.children || []);
        const idx = siblings.indexOf(el);
        el.style.animationDelay = (idx * 0.08) + 's';
        el.classList.add('revealed');
        // Count-up numbers
        const nums = el.querySelectorAll('.stat-number, [data-countup]');
        nums.forEach(n => animateCountUp(n));
        revealObserver.unobserve(el);
      }
    });
  }, { threshold: 0.12 });

  // Auto-observe reveal targets
  document.querySelectorAll('.reveal-up, .reveal-scale, .reveal-left, .reveal-right, .card-saas, .stat-card')
    .forEach(el => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity 0.55s cubic-bezier(0.34,1.56,0.64,1), transform 0.55s cubic-bezier(0.34,1.56,0.64,1)';
      revealObserver.observe(el);
    });

  // When revealed, animate in
  const styleEl = document.createElement('style');
  styleEl.textContent = `.revealed { opacity: 1 !important; transform: none !important; }`;
  document.head.appendChild(styleEl);

  /* ============================================================
     6. RIPPLE EFFECT ON BUTTONS
     ============================================================ */
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-saas-primary');
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.cssText = `left:${x}px; top:${y}px; width:10px; height:10px; margin-left:-5px; margin-top:-5px;`;
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);
  });

  /* ============================================================
     7. COMMAND PALETTE (Ctrl+K)
     ============================================================ */
  const palette = document.getElementById('commandPalette');
  const cmdInput = document.getElementById('commandInput');
  const cmdItems = document.querySelectorAll('.command-item');
  let selectedIdx = -1;

  function openPalette() {
    if (!palette) return;
    palette.classList.add('active');
    if (cmdInput) {
      cmdInput.value = '';
      filterCommands('');
      setTimeout(() => cmdInput.focus(), 60);
    }
    selectedIdx = -1;
  }

  function closePalette() {
    if (!palette) return;
    palette.classList.remove('active');
  }

  document.querySelectorAll('.topbar-search-trigger').forEach(b => b.addEventListener('click', openPalette));

  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      palette?.classList.contains('active') ? closePalette() : openPalette();
    }
    if (e.key === 'Escape') closePalette();
  });

  palette?.addEventListener('click', (e) => { if (e.target === palette) closePalette(); });

  cmdInput?.addEventListener('input', () => filterCommands(cmdInput.value.toLowerCase().trim()));

  function filterCommands(q) {
    cmdItems.forEach(item => {
      item.style.display = (!q || item.textContent.toLowerCase().includes(q)) ? 'flex' : 'none';
    });
  }

  /* ============================================================
     8. AUTO-DISMISS ALERTS
     ============================================================ */
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      try { new bootstrap.Alert(alert).close(); }
      catch { alert.style.opacity = '0'; setTimeout(() => alert.remove(), 300); }
    }, 5500);
  });

  /* ============================================================
     10. SUPER REALISTIC SIDEBAR PHYSICS & 3D MAGNETIC ENGINE
     ============================================================ */
  const sidebarLinks = document.querySelectorAll('.sidebar-link[data-magnetic="true"], .user-profile-capsule[data-magnetic="true"]');

  sidebarLinks.forEach((link, i) => {
    // Initial Stagger Entry
    link.style.animation = `sidebarItemEnter 0.45s cubic-bezier(0.34,1.56,0.64,1) ${i * 0.035}s both`;

    let bounds = null;
    let isHovered = false;
    let currentX = 0, currentY = 0, currentRx = 0, currentRy = 0;
    let targetX = 0, targetY = 0, targetRx = 0, targetRy = 0;
    let rafId = null;

    function updateBounds() {
      bounds = link.getBoundingClientRect();
    }

    function onMouseEnter(e) {
      isHovered = true;
      updateBounds();
      cancelAnimationFrame(rafId);
      renderPhysics();
    }

    function onMouseMove(e) {
      if (!bounds) updateBounds();
      const mouseX = e.clientX - bounds.left;
      const mouseY = e.clientY - bounds.top;

      // Update spotlight position
      link.style.setProperty('--mouse-x', `${mouseX}px`);
      link.style.setProperty('--mouse-y', `${mouseY}px`);

      // Compute normalized values (-1 to +1)
      const normX = Math.max(-1, Math.min(1, ((mouseX / bounds.width) - 0.5) * 2));
      const normY = Math.max(-1, Math.min(1, ((mouseY / bounds.height) - 0.5) * 2));

      // Target physics coordinates
      targetX = 6 + (normX * 3); // subtle magnetic pull to right
      targetY = normY * 2.5;
      targetRx = -normY * 12; // tilt on X axis
      targetRy = normX * 12;  // tilt on Y axis
    }

    function onMouseLeave() {
      isHovered = false;
      targetX = 0;
      targetY = 0;
      targetRx = 0;
      targetRy = 0;
    }

    function renderPhysics() {
      // Spring physics interpolation (Damped harmonic spring with friction 0.18)
      const springDamping = 0.18;
      currentX += (targetX - currentX) * springDamping;
      currentY += (targetY - currentY) * springDamping;
      currentRx += (targetRx - currentRx) * springDamping;
      currentRy += (targetRy - currentRy) * springDamping;

      if (isHovered || Math.abs(currentX) > 0.05 || Math.abs(currentRx) > 0.05) {
        link.style.setProperty('--tx', `${currentX.toFixed(2)}px`);
        link.style.setProperty('--ty', `${currentY.toFixed(2)}px`);
        link.style.transform = `perspective(800px) translate3d(${currentX.toFixed(2)}px, ${currentY.toFixed(2)}px, 8px) rotateX(${currentRx.toFixed(2)}deg) rotateY(${currentRy.toFixed(2)}deg) scale(1.02)`;
        rafId = requestAnimationFrame(renderPhysics);
      } else {
        // Settled cleanly
        link.style.setProperty('--tx', '0px');
        link.style.setProperty('--ty', '0px');
        link.style.transform = '';
      }
    }

    link.addEventListener('mouseenter', onMouseEnter);
    link.addEventListener('mousemove', onMouseMove);
    link.addEventListener('mouseleave', onMouseLeave);
    window.addEventListener('resize', updateBounds, { passive: true });
  });

  /* ============================================================
     11. CHART.JS — ANIMATED DEFAULTS
     ============================================================ */
  if (typeof Chart !== 'undefined') {
    Chart.defaults.animation.duration = 1200;
    Chart.defaults.animation.easing = 'easeOutQuart';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(10,12,30,0.9)';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(79,70,229,0.3)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
    Chart.defaults.plugins.tooltip.titleFont = { family: 'Inter', weight: '600', size: 12 };
    Chart.defaults.plugins.tooltip.bodyFont  = { family: 'Inter', size: 12 };
    Chart.defaults.plugins.legend.labels.padding = 20;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.pointStyleWidth = 10;
    Chart.defaults.plugins.legend.labels.font = { family: 'Inter', size: 12 };
    Chart.defaults.scale.grid.color = 'rgba(79,70,229,0.06)';
    Chart.defaults.scale.ticks.color = '#94a3b8';
    Chart.defaults.scale.ticks.font = { family: 'Inter', size: 11 };
  }

  /* ============================================================
     12. SMOOTH LINK TRANSITIONS
     ============================================================ */
  document.querySelectorAll('a[href]:not([href^="#"]):not([href^="javascript"]):not([target="_blank"])').forEach(link => {
    link.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (!href || href === window.location.pathname) return;
      document.body.style.transition = 'opacity 0.25s ease';
      document.body.style.opacity = '0';
    });
  });

  window.addEventListener('pageshow', () => {
    document.body.style.opacity = '1';
  });

  /* ============================================================
     13. TOPBAR — Shadow on scroll
     ============================================================ */
  const topbar = document.querySelector('.app-topbar');
  window.addEventListener('scroll', () => {
    if (!topbar) return;
    if (window.scrollY > 10) {
      topbar.style.boxShadow = '0 4px 20px rgba(79,70,229,0.08)';
    } else {
      topbar.style.boxShadow = 'none';
    }
  }, { passive: true });

  /* ============================================================
     14. SIDEBAR NAVIGATION & SEARCH ENGINE
     ============================================================ */
  const collapseBtn = document.getElementById('sidebarCollapseBtn');
  const sidebar = document.getElementById('appSidebar');
  const mobileToggle = document.getElementById('sidebarToggle');
  const sidebarSearch = document.getElementById('sidebarSearchInput');
  const sidebarNoResults = document.getElementById('sidebarNoResults');

  // Auto-populate data-tooltip for all sidebar links
  document.querySelectorAll('.sidebar-link').forEach(link => {
    const textEl = link.querySelector('.sidebar-link-text');
    if (textEl && !link.getAttribute('data-tooltip')) {
      link.setAttribute('data-tooltip', textEl.textContent.trim());
    }
  });

  // Restore saved collapse state
  if (localStorage.getItem('horizon-sidebar-collapsed') === 'true') {
    document.body.classList.add('sidebar-collapsed');
  }

  if (collapseBtn) {
    collapseBtn.addEventListener('click', function () {
      document.body.classList.toggle('sidebar-collapsed');
      const isCollapsed = document.body.classList.contains('sidebar-collapsed');
      localStorage.setItem('horizon-sidebar-collapsed', isCollapsed ? 'true' : 'false');
      
      // Micro-interaction bounce
      collapseBtn.style.transform = 'scale(0.85) rotate(180deg)';
      setTimeout(() => { collapseBtn.style.transform = ''; }, 250);
    });
  }

  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      sidebar.classList.toggle('show');
    });

    document.addEventListener('click', function (e) {
      if (window.innerWidth <= 992 && sidebar.classList.contains('show')) {
        if (!sidebar.contains(e.target) && !mobileToggle.contains(e.target)) {
          sidebar.classList.remove('show');
        }
      }
    });
  }

  // Keyboard shortcut for sidebar search (Ctrl+K or Cmd+K)
  if (sidebarSearch) {
    window.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        if (document.activeElement !== sidebarSearch) {
          e.preventDefault();
          sidebarSearch.focus();
          sidebarSearch.select();
        }
      }
    });
  }

  console.log('%c🌟 Horizon SMS 2026 — Redesigned Direct Link Sidebar & Engine Loaded', 'color:#4f46e5;font-weight:700;font-size:14px');
});
