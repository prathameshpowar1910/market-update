/**
 * Market Digest — app.js
 * Minimal vanilla JS for progressive enhancement.
 */

/* ── Glossary live search ───────────────────────────────────────────── */
(function initGlossarySearch() {
  const searchInput = document.getElementById('glossary-search');
  if (!searchInput) return;

  const categoryInput = document.getElementById('glossary-category');
  const clearButton = document.getElementById('glossary-clear');
  const resultCount = document.getElementById('glossary-results');
  const entries     = document.querySelectorAll('.glossary-entry');
  const sections    = document.querySelectorAll('.glossary-letter-section');
  const noResults   = document.getElementById('glossary-no-results');

  function filterGlossary(query, category = categoryInput?.value || '') {
    const q = query.trim().toLowerCase();
    let anyVisible = false;
    let visibleCount = 0;

    entries.forEach(entry => {
      const term = entry.dataset.term || '';
      const def  = entry.querySelector('.glossary-definition')?.textContent.toLowerCase() || '';
      const matchesCategory = !category || entry.dataset.category === category;
      const match = matchesCategory && (!q || term.includes(q) || def.includes(q));
      entry.style.display = match ? '' : 'none';
      if (match) { anyVisible = true; visibleCount += 1; }
    });

    // Hide letter headers that have no visible entries
    sections.forEach(section => {
      const visible = [...section.querySelectorAll('.glossary-entry')]
        .some(e => e.style.display !== 'none');
      section.style.display = visible ? '' : 'none';
    });

    if (noResults) noResults.style.display = anyVisible ? 'none' : '';
    if (resultCount) resultCount.textContent = `Showing ${visibleCount} of ${entries.length} terms`;
    if (clearButton) clearButton.hidden = !q && !category;
  }

  searchInput.addEventListener('input', e => filterGlossary(e.target.value));
  searchInput.addEventListener('search', e => filterGlossary(e.target.value));
  categoryInput?.addEventListener('change', () => filterGlossary(searchInput.value));
  clearButton?.addEventListener('click', () => {
    searchInput.value = '';
    if (categoryInput) categoryInput.value = '';
    filterGlossary('');
    searchInput.focus();
  });
})();


/* ── Smooth scroll for letter nav ──────────────────────────────────── */
document.querySelectorAll('.letter-nav-item').forEach(link => {
  link.addEventListener('click', e => {
    const href = link.getAttribute('href');
    const target = href && document.querySelector(href);
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});


/* ── Animate sections on scroll (IntersectionObserver) ─────────────── */
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.animationPlayState = 'running';
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1 }
  );

  document.querySelectorAll('.section').forEach(section => {
    section.style.animationPlayState = 'paused';
    observer.observe(section);
  });
}
