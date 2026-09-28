(() => {
  const themeSelect = document.querySelector('[data-theme-select]');
  if (themeSelect) {
    themeSelect.hidden = false;
    themeSelect.value = document.documentElement.dataset.theme || 'system';
    themeSelect.addEventListener('change', () => {
      const theme = themeSelect.value;
      if (theme === 'system') delete document.documentElement.dataset.theme;
      else document.documentElement.dataset.theme = theme;
      try { localStorage.setItem('nexusshell-theme', theme); } catch (_) { /* System preference still works. */ }
    });
  }
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', async () => {
      const block = button.closest('.command');
      const status = block.querySelector('[role="status"]');
      try {
        await navigator.clipboard.writeText(block.querySelector('code').textContent);
        status.textContent = 'Copied to clipboard.';
        button.textContent = 'Copied';
      } catch (_) {
        status.textContent = 'Select the commands above to copy them.';
      }
    });
  });
  const redirectLegacyAnchor = () => {
    if (location.pathname !== '/' && location.pathname !== '/index.html') return;
    const legacy = ['#demo', '#run', '#why', '#use'];
    if (legacy.includes(location.hash)) location.replace('/synrail/' + location.hash);
  };
  redirectLegacyAnchor();
  window.addEventListener('hashchange', redirectLegacyAnchor);
})();
