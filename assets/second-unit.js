(() => {
  document.querySelectorAll('[data-su-process]').forEach(process => {
    const controls = process.querySelector('.su-stage-controls');
    const buttons = [...process.querySelectorAll('[data-su-step]')];
    const frames = [...process.querySelectorAll('[data-su-frame]')];
    if (!controls || buttons.length !== frames.length || !frames.length) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let selected = -1;
    let transition = null;
    process.addEventListener('keydown', () => { process.dataset.input = 'keyboard'; });
    process.addEventListener('pointerdown', () => { process.dataset.input = 'pointer'; });
    function select(index, pointer = false) {
      if (selected === index) return;
      transition?.cancel();
      transition = null;
      buttons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
      frames.forEach((frame, i) => { frame.hidden = i !== index; });
      selected = index;
      if (pointer && !reducedMotion.matches && typeof frames[index].animate === 'function') {
        transition = frames[index].animate(
          [{ opacity: .55, transform: 'translateY(5px)' }, { opacity: 1, transform: 'translateY(0)' }],
          { duration: 180, easing: 'cubic-bezier(.23,1,.32,1)' }
        );
      }
    }
    buttons.forEach((button, index) => {
      button.addEventListener('click', event => select(index, event.detail > 0));
      button.addEventListener('keydown', event => {
        let next;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % buttons.length;
        else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index - 1 + buttons.length) % buttons.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = buttons.length - 1;
        else return;
        event.preventDefault();
        select(next);
        buttons[next].focus();
      });
    });
    process.classList.add('su-enhanced');
    controls.hidden = false;
    select(0);
  });

  document.querySelectorAll('[data-su-previews]').forEach(group => {
    const videos = [...group.querySelectorAll('[data-su-preview]')];
    const toggle = group.querySelector('[data-su-preview-toggle]');
    if (!toggle || !videos.length) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let desired = !reducedMotion.matches;
    let inView = false;
    let revision = 0;
    function updateLabel() {
      toggle.textContent = desired ? 'Pause previews' : 'Play previews';
    }
    async function sync() {
      const current = ++revision;
      updateLabel();
      if (!desired || !inView || document.hidden) {
        videos.forEach(video => video.pause());
        return;
      }
      videos.forEach(video => {
        video.muted = true;
        if (!video.getAttribute('src')) video.src = video.dataset.suPreview;
      });
      const result = await Promise.allSettled(videos.map(video => video.play()));
      if (current !== revision) return;
      if (result.some(item => item.status === 'rejected')) {
        videos.forEach(video => video.pause());
        desired = false;
        updateLabel();
      }
    }
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      desired = !desired;
      if (desired) inView = true;
      sync();
    });
    document.addEventListener('visibilitychange', sync);
    reducedMotion.addEventListener?.('change', () => {
      if (reducedMotion.matches) desired = false;
      sync();
    });
    if (typeof IntersectionObserver === 'function') {
      const observer = new IntersectionObserver(entries => {
        inView = entries[entries.length - 1].isIntersecting;
        sync();
      }, { threshold: .25 });
      observer.observe(group);
    } else {
      desired = false;
      updateLabel();
    }
  });
})();
