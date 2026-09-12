/* Optional progressive enhancement. Content and links work without JavaScript. */
document.documentElement.classList.add('js');
const toggle = document.querySelector('.docs-menu-toggle');
const sidebar = document.querySelector('.doc-sidebar');
if (toggle && sidebar) {
  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!expanded));
    sidebar.classList.toggle('is-open', !expanded);
    toggle.textContent = expanded ? 'Browse documentation + ' : 'Close documentation − ';
  });
}

// Silent looping previews: respect motion/data preferences and pause offscreen.
const previews = [...document.querySelectorAll('.video-card video')];
const motionToggle = document.querySelector('#video-motion-toggle');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let previewsPaused = reducedMotion.matches || Boolean(navigator.connection?.saveData);
function updatePreviewPlayback() {
  previews.forEach(video => {
    video.muted = true;
    if (previewsPaused || document.hidden || video.dataset.visible === 'false') video.pause();
    else video.play().catch(() => {}); // Native controls remain available if autoplay is denied.
  });
  if (motionToggle) {
    motionToggle.textContent = previewsPaused ? 'Play previews' : 'Pause previews';
    motionToggle.setAttribute('aria-pressed', String(previewsPaused));
  }
}
if (previews.length) {
  motionToggle?.addEventListener('click', () => {
    previewsPaused = !previewsPaused; updatePreviewPlayback();
  });
  reducedMotion.addEventListener('change', event => {
    previewsPaused = event.matches; updatePreviewPlayback();
  });
  document.addEventListener('visibilitychange', updatePreviewPlayback);
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => { entry.target.dataset.visible = String(entry.isIntersecting); });
      updatePreviewPlayback();
    }, {threshold: 0.15});
    previews.forEach(video => observer.observe(video));
  }
  updatePreviewPlayback();
}
