/* The reader works as local HTML; the theme control needs no saved state. */
(function () {
  'use strict';
  const picker = document.getElementById('theme-select');
  const menus = document.querySelectorAll('.chapter-menu, .section-menu');
  const narrow = window.matchMedia('(max-width: 760px)');
  function syncMenus() { menus.forEach(menu => { menu.open = !narrow.matches; }); }
  syncMenus();
  narrow.addEventListener('change', syncMenus);
  if (picker) picker.addEventListener('change', function () {
    if (picker.value === 'auto') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.dataset.theme = picker.value;
  });
}());
