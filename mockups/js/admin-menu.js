(function () {
  const body = document.body;
  const menuBtn = document.getElementById('admin-menu-btn');
  const closeBtn = document.getElementById('admin-drawer-close');
  const backdrop = document.getElementById('admin-backdrop');
  const drawer = document.getElementById('admin-drawer');

  function setMenuOpen(open) {
    body.classList.toggle('admin-menu-open', open);
    if (menuBtn) menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (drawer) drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
  }

  if (menuBtn) menuBtn.addEventListener('click', () => setMenuOpen(!body.classList.contains('admin-menu-open')));
  if (closeBtn) closeBtn.addEventListener('click', () => setMenuOpen(false));
  if (backdrop) backdrop.addEventListener('click', () => setMenuOpen(false));
  if (drawer) {
    drawer.querySelectorAll('.nav-item').forEach(link => {
      link.addEventListener('click', () => setMenuOpen(false));
    });
  }
})();
