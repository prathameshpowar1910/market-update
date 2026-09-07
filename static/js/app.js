/**
 * Market Digest — app.js
 * Minimal vanilla JS for progressive enhancement.
 */

/* ── Glossary live search ───────────────────────────────────────────── */
(function initGlossarySearch() {
  const searchInput = document.getElementById('glossary-search');
  if (!searchInput) return;

  const entries     = document.querySelectorAll('.glossary-entry');
  const sections    = document.querySelectorAll('.glossary-letter-section');
  const noResults   = document.getElementById('glossary-no-results');

  function filterGlossary(query) {
    const q = query.trim().toLowerCase();
    let anyVisible = false;

    entries.forEach(entry => {
      const term = entry.dataset.term || '';
      const def  = entry.querySelector('.glossary-definition')?.textContent.toLowerCase() || '';
      const match = !q || term.includes(q) || def.includes(q);
      entry.style.display = match ? '' : 'none';
      if (match) anyVisible = true;
    });

    // Hide letter headers that have no visible entries
    sections.forEach(section => {
      const visible = [...section.querySelectorAll('.glossary-entry')]
        .some(e => e.style.display !== 'none');
      section.style.display = visible ? '' : 'none';
    });

    if (noResults) noResults.style.display = anyVisible ? 'none' : '';
  }

  searchInput.addEventListener('input', e => filterGlossary(e.target.value));
  searchInput.addEventListener('search', e => filterGlossary(e.target.value));
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
