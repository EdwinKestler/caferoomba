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
