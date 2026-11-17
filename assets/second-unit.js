(() => {
  document.querySelectorAll('[data-su-process]').forEach(process => {
    const controls = process.querySelector('.su-stage-controls');
    const buttons = [...process.querySelectorAll('[data-su-step]')];
    const frames = [...process.querySelectorAll('[data-su-frame]')];
    if (!controls || buttons.length !== frames.length || !frames.length) return;
    function select(index) {
      buttons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
      frames.forEach((frame, i) => { frame.hidden = i !== index; });
    }
    buttons.forEach((button, index) => {
      button.addEventListener('click', () => select(index));
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
})();
