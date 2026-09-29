"""The interactive project desk. All project content is present without JavaScript."""


def render(projects, updates, visual):
    links = []
    marks = ['S', 'R', '1', 'T']
    for i, p in enumerate(projects):
        group = '<p class="shelf-label">In progress</p>' if i == 0 else '<p class="shelf-label shelf-divider">Applications</p>' if i == 2 else ''
        links.append(f'''{group}<a class="shelf-project" href="#{p['slug']}" data-project-link="{p['slug']}" aria-controls="{p['slug']}"><span class="project-monogram mark-{p['slug']}" aria-hidden="true">{marks[i]}</span><span><strong>{p['name']}</strong><small>{p['kind']}</small></span><span class="shelf-arrow" aria-hidden="true">↗</span></a>''')

    def heading(p, description, repo):
        return f'''<header class="desk-project-heading"><div><p class="desk-eyebrow">{p['context']} <span aria-hidden="true">/</span> {p['kind']}</p><h2 id="title-{p['slug']}" tabindex="-1">{p['name']}</h2><p class="desk-description">{description}</p></div><div class="desk-project-links"><a href="/projects/{p['slug']}/">Project notes <span aria-hidden="true">↗</span></a><a href="https://github.com/USBVadik/{repo}" target="_blank" rel="noopener noreferrer">Source code <span aria-hidden="true">↗</span></a></div></header>'''

    def note(project):
        item = next((u for u in updates if u['project'] == project), None)
        if item:
            return f'''<a class="desk-development" href="{item['url']}" target="_blank" rel="noopener noreferrer"><span class="development-label">Latest project note<time datetime="{item['date']}">{item['display_date']}</time></span><span>{item['title']}</span><span aria-hidden="true">↗</span></a>'''
        return ''

    synrail = f'''<section class="desk-panel" id="synrail" aria-labelledby="title-synrail">
{heading(projects[0], 'Evidence checks for coding agents.', 'synrail')}
<div class="experiment proof-experiment" data-proof-stage="0">
<div class="experiment-caption"><span>THE FALSE-GREEN DEMO</span><span>Recorded walkthrough</span></div>
<div class="proof-workspace"><div class="proof-steps" role="group" aria-label="Synrail walkthrough steps">
<button type="button" data-proof-step="0" aria-pressed="true"><span class="step-number">1</span><span><strong>The claim</strong><small>What the agent says</small></span></button>
<button type="button" data-proof-step="1" aria-pressed="false"><span class="step-number">2</span><span><strong>The check</strong><small>What verification finds</small></span></button>
<button type="button" data-proof-step="2" aria-pressed="false"><span class="step-number">3</span><span><strong>The repair</strong><small>What acceptance needs</small></span></button>
</div><div class="proof-output" aria-live="polite" aria-atomic="true">
<div class="proof-frame" data-proof-frame="0"><div class="proof-state"><span class="signal signal-wait"></span>Claim recorded</div><h3>“Fixed add();<br>tests pass.”</h3><div class="evidence-slip"><span>Submitted evidence</span><code>grep found the fast-path line</code></div><p>A matching line of code doesn’t tell us whether the behavior works.</p></div>
<div class="proof-frame" data-proof-frame="1"><div class="proof-state"><span class="signal signal-fail"></span>Verification failed</div><h3>The test<br>still fails.</h3><pre class="proof-command"><code><span>$ synrail verify</span>\n<strong class="proof-fail">Verification unit: FAIL (exit 1)</strong>\n<span>$ synrail check</span>\nSynrail: Status: Verification Failed</code></pre><p>Running the check exposes what the text search missed.</p></div>
<div class="proof-frame" data-proof-frame="2"><div class="proof-state"><span class="signal signal-pass"></span>Accepted after repair</div><h3>The repair passes<br>verification.</h3><pre class="proof-command"><code><span>$ synrail verify</span>\n<strong class="proof-pass">Verification unit: GREEN</strong>\n<span>$ synrail check</span>\nSynrail: Status: Accepted</code></pre><p>The repaired behavior passes verification. The work can now be accepted.</p></div>
</div></div><div class="experiment-controls"><button class="desk-button" type="button" data-proof-next>Show the failing check <span aria-hidden="true">→</span></button><a class="recording-link" href="/synrail/#demo" data-open-demo>Watch the original <span>0:08 ↗</span></a></div>
</div><div class="experiment-footnote"><span>Walk through the recorded example above. No commands run in your browser.</span><a href="/synrail/#run">Try it locally ↗</a></div>
{note('Synrail')}</section>'''

    labels = ['A', 'B', 'X', 'C', 'D']
    nodes = ''.join(f'<button class="trace-node" type="button" data-trace-node="{i}" aria-label="Inspect transaction {label}" aria-pressed="{str(i==2).lower()}"><span>{label}</span><small>{"input" if i==2 else ""}</small></button>' for i,label in enumerate(labels))
    rhook = f'''<section class="desk-panel" id="rhook" aria-labelledby="title-rhook">
{heading(projects[1], 'Replay execution after one changed input.', 'rhook')}
<div class="experiment replay-experiment" data-branch-mode="changed" data-trace-position="2">
<div class="experiment-caption"><span>INSIDE A REPLAY</span><span>Conceptual model</span></div>
<div class="replay-mode-switch" role="group" aria-label="Execution branch"><button type="button" data-branch-mode="original" aria-pressed="false">Original input</button><button type="button" data-branch-mode="changed" aria-pressed="true">Change X <span aria-hidden="true">↳</span></button></div>
<div class="trace-board"><span class="trace-label">Recorded sequence</span><div class="history-track">{nodes}</div><div class="branch-track" aria-label="Recomputed branch"><div class="branch-connector" aria-hidden="true"></div><button class="branch-node" type="button" data-branch-node="2" aria-label="Inspect replayed transaction X" aria-pressed="true">X′</button><button class="branch-node" type="button" data-branch-node="3" aria-label="Inspect replayed transaction C" aria-pressed="false">C′</button><button class="branch-node" type="button" data-branch-node="4" aria-label="Inspect replayed transaction D" aria-pressed="false">D′</button></div><div class="branch-label">Recomputed execution</div></div>
<div class="trace-inspector" aria-live="polite" aria-atomic="true"><span class="inspect-symbol" data-trace-symbol>X → X′</span><div><strong data-trace-title>One declared intervention</strong><p data-trace-description>The input changes here. The checkpoint and historical transaction order stay fixed.</p></div></div>
<div class="trace-scrubber"><label for="trace-position">Follow the execution</label><input id="trace-position" type="range" min="0" max="4" value="2" step="1" aria-valuetext="Transaction X, changed input"><span data-trace-counter>3 / 5</span></div>
</div><div class="experiment-footnote"><span>This diagram explains the model; it does not run a blockchain replay.</span><a href="https://github.com/USBVadik/rhook/tree/main/examples/robinhood-v4" target="_blank" rel="noopener noreferrer">Reproduce the 50-block example ↗</a></div>
{note('RHOOK')}</section>'''

    onelink = f'''<section class="desk-panel" id="onelink-pay" aria-labelledby="title-onelink-pay">
{heading(projects[2], 'Spending permissions with limits and a receipt.', 'OLP')}
<div class="experiment payment-experiment" data-payment-state="blocked"><div class="experiment-caption"><span>A SPENDING PERMISSION</span><span>Local illustration</span></div>
<div class="payment-workspace"><div class="payment-request"><label for="request-amount">Requested payment</label><div class="payment-value"><output id="amount-output" for="request-amount">0.20</output><span>USDC</span></div><input id="request-amount" type="range" min="5" max="30" value="20" step="5" aria-valuetext="0.20 USDC"><div class="amount-ticks" aria-hidden="true"><span>0.05</span><span>0.30 USDC</span></div><p>Move the amount across the permission’s limit.</p></div><div class="permission-receipt"><span class="receipt-label">Research expense card</span><div class="permission-line"><span>Per-charge limit</span><strong>0.10 USDC</strong></div><div class="permission-line"><span>Your request</span><strong data-receipt-amount>0.20 USDC</strong></div><div class="payment-decision" aria-live="polite" aria-atomic="true"><span class="decision-marker" aria-hidden="true">×</span><div><strong data-payment-verdict>Over the limit</strong><p data-payment-reason>This request would be rejected by the per-charge check.</p></div></div><span class="receipt-edge" aria-hidden="true"></span></div></div>
<div class="experiment-controls"><a class="desk-button" href="https://onelink-pay.vercel.app/try" target="_blank" rel="noopener noreferrer">Try the app’s spending check ↗</a><a href="https://onelink-pay.vercel.app/demo-replay" target="_blank" rel="noopener noreferrer">View a verified run ↗</a></div></div>
<div class="experiment-footnote"><span>Illustrates one limit only. No wallet or payment; other mandate checks are outside this example.</span></div>
<details class="desk-evidence"><summary><span>View the application</span><span aria-hidden="true">+</span></summary>{visual(projects[2])}</details>
<a class="desk-development" href="/projects/onelink-pay/"><span class="development-label">UXmaxx 2026<small>Encode / Particle Network</small></span><span>Magic Labs Bonus Challenge winner</span><span aria-hidden="true">↗</span></a></section>'''

    turing = f'''<section class="desk-panel" id="turingvault" aria-labelledby="title-turingvault">
{heading(projects[3], 'Proposals, checks, and execution records on Mantle.', 'TuringVault-Core')}
<div class="experiment vault-experiment"><div class="experiment-caption"><span>FOLLOW THE DECISION</span><span>Workflow guide</span></div><a class="vault-screen" href="/assets/media/turingvault-console.jpg" target="_blank" rel="noopener"><img src="/assets/media/turingvault-console.jpg" width="1152" height="617" alt="The TuringVault agent console, captured 29 September 2026."><span>Open full screenshot ↗</span></a>
<div class="vault-stages" role="group" aria-label="TuringVault workflow"><button type="button" data-vault-stage="0" aria-pressed="true"><span>01</span> Propose</button><button type="button" data-vault-stage="1" aria-pressed="false"><span>02</span> Challenge</button><button type="button" data-vault-stage="2" aria-pressed="false"><span>03</span> Record</button></div><div class="vault-explanation" aria-live="polite" aria-atomic="true"><strong data-vault-title>An analyst proposes an action.</strong><p data-vault-description>The proposal becomes part of an inspectable decision trail, before anything executes.</p></div></div>
<div class="experiment-footnote"><span>Operator-funded demonstration on Mantle. No public deposits.</span><a href="https://turingvault.dev/" target="_blank" rel="noopener noreferrer">Open TuringVault ↗</a></div>
<a class="desk-development" href="/projects/turingvault/"><span class="development-label">Mantle Turing Test<small>2026</small></span><span>Project Deployment Award &amp; Demo Day</span><span aria-hidden="true">↗</span></a></section>'''

    return f'''<div id="top"></div><div class="desk-intro"><h1>Vadik’s project desk<span class="desk-intro-dot" aria-hidden="true">.</span></h1><p>Open a project. Follow the work.</p></div>
<span id="technology" class="legacy-anchor"></span><div class="project-desk" id="work"><aside class="project-shelf"><div class="shelf-bio"><span class="shelf-handle">USBVadik</span><p>I build with agents.<br>And work on ways<br>to check their work.</p><a href="/about/">A little about me <span aria-hidden="true">↗</span></a></div><nav class="project-switcher" aria-label="Choose a project">{''.join(links)}</nav><div class="shelf-bottom"><a href="/projects/agent-automation/">The earlier bot experiments ↗</a><a href="/projects/">All projects ↗</a></div></aside><div class="desk-canvas">{synrail}{rhook}{onelink}{turing}</div></div>
<div class="desk-colophon" id="transparency"><p>Built over time, from Telegram bots to agent tooling and onchain experiments.</p><a href="/updates/" id="updates">Development notes ↗</a></div>
<div class="legacy-anchor" id="demo"></div><div class="legacy-anchor" id="run"></div><div class="legacy-anchor" id="why"></div><div class="legacy-anchor" id="use"></div>
<dialog class="demo-dialog" id="synrail-demo-dialog" aria-labelledby="demo-dialog-title"><div class="dialog-heading"><h2 id="demo-dialog-title">Synrail / the original recording</h2><button type="button" data-close-demo aria-label="Close demo">Close <span aria-hidden="true">×</span></button></div>{visual(projects[0], True)}<p>A recorded run from the public repository. <a href="/synrail/#demo-transcript">Read the transcript</a></p></dialog>'''
