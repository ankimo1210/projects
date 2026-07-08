
(function () {
  const root = document.body.dataset.root || "";
  const searchIndex = window.SEARCH_INDEX || [];
  const forms = document.querySelectorAll("[data-search-form]");
  const inputs = document.querySelectorAll("[data-search-input]");
  const results = document.querySelectorAll("[data-search-results]");
  const pageJumpForms = document.querySelectorAll("[data-page-jump]");

  function normalize(value) {
    return (value || "").toString().toLowerCase();
  }

  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, function (char) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char];
    });
  }

  function makeSnippet(text, query) {
    const normalizedText = normalize(text);
    const normalizedQuery = normalize(query);
    const found = normalizedText.indexOf(normalizedQuery);
    const start = Math.max(0, found - 55);
    const end = Math.min(text.length, found + query.length + 85);
    let snippet = text.slice(start, end).replace(/\s+/g, " ").trim();
    if (start > 0) snippet = "... " + snippet;
    if (end < text.length) snippet += " ...";
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return escapeHtml(snippet).replace(new RegExp(escapedQuery, "ig"), function (match) {
      return "<mark>" + escapeHtml(match) + "</mark>";
    });
  }

  function renderSearch(query) {
    const trimmed = query.trim();
    results.forEach(function (target) {
      if (trimmed.length < 2) {
        target.classList.remove("visible");
        target.innerHTML = "";
        return;
      }

      const normalizedQuery = normalize(trimmed);
      const matches = searchIndex
        .map(function (item) {
          const haystack = normalize([item.title, item.section, item.chapter, item.text].join(" "));
          const score = haystack.indexOf(normalizedQuery);
          return score === -1 ? null : { item: item, score: score };
        })
        .filter(Boolean)
        .sort(function (a, b) {
          return a.score - b.score || a.item.page - b.item.page;
        })
        .slice(0, 8);

      target.classList.add("visible");
      if (!matches.length) {
        target.innerHTML = '<div class="empty">該当ページがありません。</div>';
        return;
      }

      target.innerHTML = matches.map(function (match) {
        const item = match.item;
        return [
          '<a href="',
          root + item.path,
          '"><strong>',
          escapeHtml(item.title),
          " / ",
          escapeHtml(item.section),
          "</strong><small>",
          makeSnippet(item.text, trimmed),
          "</small></a>"
        ].join("");
      }).join("");
    });
  }

  forms.forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const input = form.querySelector("[data-search-input]");
      renderSearch(input ? input.value : "");
    });
  });

  inputs.forEach(function (input) {
    input.addEventListener("input", function () {
      renderSearch(input.value);
    });
  });

  pageJumpForms.forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const input = form.querySelector("input[name='page']");
      const value = input ? parseInt(input.value, 10) : NaN;
      if (!Number.isFinite(value) || value < 1 || value > 136) return;
      window.location.href = root + "pages/page-" + String(value).padStart(3, "0") + ".html";
    });
  });
})();
