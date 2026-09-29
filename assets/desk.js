(() => {
  const desk = document.querySelector('.project-desk');
  if (!desk) return;
  const panels = [...desk.querySelectorAll('.desk-panel')];
  const projectLinks = [...desk.querySelectorAll('[data-project-link]')];
  const byId = new Map(panels.map(panel => [panel.id, panel]));
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  document.body.classList.add('desk-enhanced');
  document.addEventListener('keydown', () => { document.body.dataset.input = 'keyboard'; });
  document.addEventListener('pointerdown', () => { document.body.dataset.input = 'pointer'; });

  function selectProject(id, { push = false, pointer = false } = {}) {
    if (!byId.has(id)) return;
    panels.forEach(panel => { panel.hidden = panel.id !== id; });
    projectLinks.forEach(link => {
      if (link.dataset.projectLink === id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    if (push && location.hash !== `#${id}`) history.pushState(null, '', `#${id}`);
    const panel = byId.get(id);
    if (pointer && !reduceMotion.matches && typeof panel.animate === 'function') {
      panel.getAnimations().forEach(animation => animation.cancel());
      panel.animate([{ opacity: .65, transform: 'translateY(4px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 160, easing: 'cubic-bezier(.23,1,.32,1)' });
    }
  }
  function selectFromAddress() {
    const id = location.hash.slice(1);
    if (byId.has(id)) selectProject(id);
    else if (!id || id === 'top' || !panels.some(panel => !panel.hidden)) selectProject('synrail');
  }
  projectLinks.forEach((link, index) => {
    link.addEventListener('click', event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      selectProject(link.dataset.projectLink, { push: true, pointer: event.detail > 0 });
    });
    link.addEventListener('keydown', event => {
      const offset = event.key === 'ArrowDown' || event.key === 'ArrowRight' ? 1 : event.key === 'ArrowUp' || event.key === 'ArrowLeft' ? -1 : 0;
      if (!offset && !['Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? projectLinks.length - 1 : (index + offset + projectLinks.length) % projectLinks.length;
      projectLinks[next].focus();
      selectProject(projectLinks[next].dataset.projectLink, { push: true });
    });
  });
  // Initialize once even for legacy/non-project fragments; their anchors remain intact.
  selectProject(byId.has(location.hash.slice(1)) ? location.hash.slice(1) : 'synrail');
  window.addEventListener('popstate', selectFromAddress);
  window.addEventListener('hashchange', selectFromAddress);

  const proof = desk.querySelector('.proof-experiment');
  const proofButtons = [...proof.querySelectorAll('[data-proof-step]')];
  const proofFrames = [...proof.querySelectorAll('[data-proof-frame]')];
  const nextButton = proof.querySelector('[data-proof-next]');
  const nextLabels = ['Show the failing check →', 'See what changes after repair →', 'Start again ↺'];
  let proofStep = 0;
  function setProofStep(step) {
    proofStep = step;
    proof.dataset.proofStage = String(step);
    proofButtons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === step)));
    proofFrames.forEach((frame, i) => { frame.hidden = i !== step; });
    nextButton.textContent = nextLabels[step];
  }
  proofButtons.forEach(button => button.addEventListener('click', () => setProofStep(Number(button.dataset.proofStep))));
  nextButton.addEventListener('click', () => setProofStep((proofStep + 1) % 3));
  setProofStep(0);

  const replay = desk.querySelector('.replay-experiment');
  const modeButtons = [...replay.querySelectorAll('button[data-branch-mode]')];
  const traceButtons = [...replay.querySelectorAll('[data-trace-node]')];
  const branchNodes = [...replay.querySelectorAll('[data-branch-node]')];
  const positionInput = replay.querySelector('#trace-position');
  const labels = ['A', 'B', 'X', 'C', 'D'];
  let changed = true;
  let position = 2;
  function updateTrace() {
    replay.dataset.branchMode = changed ? 'changed' : 'original';
    replay.dataset.tracePosition = String(position);
    modeButtons.forEach(button => button.setAttribute('aria-pressed', String((button.dataset.branchMode === 'changed') === changed)));
    traceButtons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === position)));
    branchNodes.forEach(node => {
      const inspected = changed && Number(node.dataset.branchNode) === position;
      node.classList.toggle('is-inspected', inspected);
      node.setAttribute('aria-pressed', String(inspected));
      node.disabled = !changed;
    });
    replay.querySelector('.branch-track').setAttribute('aria-hidden', String(!changed));
    replay.querySelector('.branch-label').setAttribute('aria-hidden', String(!changed));
    const label = labels[position];
    let title, description;
    if (!changed) {
      title = 'The recorded execution';
      description = 'The original input and transaction order are unchanged. This is the reference sequence for comparison.';
    } else if (position < 2) {
      title = 'The shared history';
      description = 'Before the intervention, both branches use the same historical context and starting checkpoint.';
    } else if (position === 2) {
      title = 'One declared intervention';
      description = 'The input changes here. The checkpoint and historical transaction order stay fixed.';
    } else {
      title = 'Execute again against the changed state';
      description = 'This transaction is replayed, not copied. Its result may succeed, revert, or become invalid; this diagram does not compute that outcome.';
    }
    replay.querySelector('[data-trace-symbol]').textContent = changed && position >= 2 ? `${label} → ${label}′` : label;
    replay.querySelector('[data-trace-title]').textContent = title;
    replay.querySelector('[data-trace-description]').textContent = description;
    replay.querySelector('[data-trace-counter]').textContent = `${position + 1} / 5`;
    positionInput.value = String(position);
    positionInput.setAttribute('aria-valuetext', `Transaction ${label}, ${title.toLowerCase()}`);
  }
  modeButtons.forEach(button => button.addEventListener('click', () => { changed = button.dataset.branchMode === 'changed'; updateTrace(); }));
  traceButtons.forEach(button => button.addEventListener('click', () => { position = Number(button.dataset.traceNode); updateTrace(); }));
  branchNodes.forEach(button => button.addEventListener('click', () => { position = Number(button.dataset.branchNode); updateTrace(); }));
  positionInput.addEventListener('input', () => { position = Number(positionInput.value); updateTrace(); });
  updateTrace();

  const payment = desk.querySelector('.payment-experiment');
  const amountInput = payment.querySelector('#request-amount');
  function updatePayment() {
    const cents = Number(amountInput.value);
    const amount = (cents / 100).toFixed(2);
    const allowed = cents <= 10;
    payment.dataset.paymentState = allowed ? 'allowed' : 'blocked';
    payment.querySelector('#amount-output').textContent = amount;
    payment.querySelector('[data-receipt-amount]').textContent = `${amount} USDC`;
    payment.querySelector('[data-payment-verdict]').textContent = allowed ? 'Within this limit' : 'Over the limit';
    payment.querySelector('[data-payment-reason]').textContent = allowed ? 'The amount passes this check. The remaining mandate conditions still apply.' : 'This request would be rejected by the per-charge check.';
    payment.querySelector('.decision-marker').textContent = allowed ? '✓' : '×';
    amountInput.setAttribute('aria-valuetext', `${amount} USDC, ${allowed ? 'within the per-charge limit' : 'over the per-charge limit'}`);
  }
  amountInput.addEventListener('input', updatePayment);
  updatePayment();

  const vault = desk.querySelector('.vault-experiment');
  const vaultCopy = [
    ['An analyst proposes an action.', 'The proposal becomes part of an inspectable decision trail, before anything executes.'],
    ['A separate validator challenges it.', 'Deterministic checks can stop execution. A proposal is not yet an executed transaction.'],
    ['Keep the outcome and its evidence.', 'Offchain records are anchored on Mantle. The interface distinguishes executed actions, blocked proposals, holds, and intents that never executed.']
  ];
  const vaultButtons = [...vault.querySelectorAll('[data-vault-stage]')];
  vaultButtons.forEach(button => button.addEventListener('click', () => {
    const step = Number(button.dataset.vaultStage);
    vaultButtons.forEach((item, i) => item.setAttribute('aria-pressed', String(step === i)));
    vault.querySelector('[data-vault-title]').textContent = vaultCopy[step][0];
    vault.querySelector('[data-vault-description]').textContent = vaultCopy[step][1];
  }));
})();
