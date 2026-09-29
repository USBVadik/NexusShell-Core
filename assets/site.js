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
  document.querySelectorAll('.replay-lab').forEach(lab => {
    const choices = lab.querySelectorAll('[data-replay-view]');
    choices.forEach(button => {
      button.hidden = false;
      button.addEventListener('click', event => {
        const changed = button.dataset.replayView === 'changed';
        lab.dataset.instant = String(event.detail === 0);
        lab.dataset.replay = changed ? 'changed' : 'original';
        choices.forEach(choice => choice.setAttribute('aria-pressed', String(choice === button)));
        lab.querySelector('.replay-explanation').textContent = changed
          ? 'Change X. Replay the transactions that follow.'
          : 'The recorded sequence, with the original input.';
        lab.querySelector('svg').setAttribute('aria-label', changed
          ? 'Conceptual replay: a changed input X creates a different branch, with C and D regenerated.'
          : 'Original recorded execution: A, B, X, C, D.');
      });
    });
  });
  const demoDialog = document.querySelector('#synrail-demo-dialog');
  if (demoDialog && typeof demoDialog.showModal === 'function') {
    const recording = demoDialog.querySelector('video');
    document.querySelector('[data-open-demo]')?.addEventListener('click', event => {
      event.preventDefault();
      demoDialog.showModal();
      recording.currentTime = 0;
      recording.play().catch(() => { /* Native controls remain available. */ });
    });
    demoDialog.querySelector('[data-close-demo]').addEventListener('click', () => demoDialog.close());
    demoDialog.addEventListener('click', event => {
      if (event.target === demoDialog) demoDialog.close();
    });
    demoDialog.addEventListener('close', () => recording.pause());
  }
  const redirectLegacyAnchor = () => {
    if (location.pathname !== '/' && location.pathname !== '/index.html') return;
    const legacy = ['#demo', '#run', '#why', '#use'];
    if (legacy.includes(location.hash)) location.replace('/synrail/' + location.hash);
  };
  redirectLegacyAnchor();
  window.addEventListener('hashchange', redirectLegacyAnchor);
})();
