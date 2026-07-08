(function () {
  const root = document.documentElement;
  const themeButton = document.querySelector("[data-theme-toggle]");
  const storedTheme = localStorage.getItem("textbook-theme");

  if (storedTheme) {
    root.dataset.theme = storedTheme;
  }

  function syncThemeButton() {
    if (!themeButton) return;
    themeButton.textContent = root.dataset.theme === "dark" ? "☀" : "☾";
    themeButton.setAttribute(
      "aria-label",
      root.dataset.theme === "dark" ? "ライトモードに切り替え" : "ダークモードに切り替え"
    );
  }

  syncThemeButton();

  themeButton?.addEventListener("click", function () {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("textbook-theme", root.dataset.theme);
    syncThemeButton();
  });

  document.querySelector("[data-menu-toggle]")?.addEventListener("click", function () {
    document.body.classList.toggle("sidebar-open");
  });

  document.addEventListener("click", function (event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (target.closest(".sidebar") || target.closest("[data-menu-toggle]")) return;
    document.body.classList.remove("sidebar-open");
  });

  const search = document.querySelector("[data-nav-search]");
  const navItems = Array.from(document.querySelectorAll("[data-nav-item]"));

  search?.addEventListener("input", function () {
    const query = search.value.trim().toLowerCase();
    navItems.forEach(function (item) {
      item.hidden = query.length > 0 && !item.textContent.toLowerCase().includes(query);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    const active = document.activeElement;
    if (active && ["INPUT", "TEXTAREA"].includes(active.tagName)) return;
    event.preventDefault();
    search?.focus();
  });

  const progress = document.querySelector("[data-progress]");
  function updateProgress() {
    if (!progress) return;
    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    const value = max > 0 ? (doc.scrollTop / max) * 100 : 0;
    progress.style.width = value + "%";
  }

  updateProgress();
  document.addEventListener("scroll", updateProgress, { passive: true });
})();
