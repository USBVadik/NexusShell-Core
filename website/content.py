"""Editorial content for the static NexusShell site. Source links stay with each entry."""

UPDATES = [
    {
        'date': '2026-09-24', 'display_date': '24 Sep 2026', 'project': 'RHOOK',
        'title': 'A reproducible replay on Robinhood Chain',
        'body': 'Added a pinned example that replays a changed input over 50 continuous blocks. The accompanying notes record a clean Linux reproduction and the limits of the experiment.',
        'url': 'https://github.com/USBVadik/rhook/commit/c6bf3e397864bb506100917c5b9a1aba6328132b',
        'label': 'Read the change',
    },
    {
        'date': '2026-09-16', 'display_date': '16 Sep 2026', 'project': 'RHOOK',
        'title': 'Tighter checks on execution evidence',
        'body': 'Hardened verification at the public integration boundary. The verifier checks the structure and relationships inside a transcript, including invalidation evidence, instead of accepting matching hashes alone.',
        'url': 'https://github.com/USBVadik/rhook/commit/1e7afa25f3b2aad673938ddcc417dbb8755ca41e',
        'label': 'Read the change',
    },
    {
        'date': '2026-09-15', 'display_date': '15 Sep 2026', 'project': 'Synrail',
        'title': 'Looking at what a pull request can change',
        'body': 'Added an experimental shadow check for changes to tests, CI, policy, permissions, and deployment paths. It observes and reports. It does not block or merge pull requests.',
        'url': 'https://github.com/USBVadik/synrail/commit/6b6536b7911635e24856021be757c1b0ea5fb807',
        'label': 'Read the change',
    },
    {
        'date': '2026-07-17', 'display_date': '17 Jul 2026', 'project': 'Synrail',
        'title': 'Improving proof recording and the first run',
        'body': 'Worked on proof recording and the path into the local tool, including installation and first-run guidance. The goal is to make the checks easier to reproduce in an existing coding-agent workflow.',
        'url': 'https://github.com/USBVadik/synrail/commit/dc870eb6b35985315082f558f30aae70df2e4d84',
        'label': 'Read the change',
    },
]

PROJECTS = [
    {
        'slug': 'synrail', 'name': 'Synrail', 'status': 'Ongoing', 'kind': 'Developer tools',
        'summary': 'Checking whether an AI coding agent has enough evidence to call its work done.',
        'intro': 'A local tool for checking the evidence behind a coding agent’s “done”.',
        'technology': 'Python', 'context': 'Open-source alpha', 'media': 'synrail',
        'links': [
            ('Product page', '/synrail/'),
            ('GitHub', 'https://github.com/USBVadik/synrail'),
            ('Try the demo', 'https://github.com/USBVadik/synrail/tree/main/examples/false-green-demo'),
            ('First-run guide', 'https://github.com/USBVadik/synrail/blob/main/docs/core/FIRST_RUN_GUIDE.md'),
            ('Shadow-check notes', 'https://github.com/USBVadik/synrail/blob/main/docs/core/PROTECTED_ADMISSION_SHADOW.md'),
        ],
        'body': '''
<h2>The question behind it</h2>
<p>A coding agent can say it ran the tests without having run them. It can also produce a check that looks convincing but says little about the change. Synrail asks what evidence should be required before that work is accepted.</p>
<p>The local tool ties a task to a patch and its verification. When the evidence is missing, stale, or inconsistent, it returns a reason and a bounded next step.</p>
<h2>Keeping acceptance separate</h2>
<p>Recording a claim and accepting it are separate operations. A claim about runtime behavior needs a verification command to run and produce a fresh receipt. A changed workspace can make earlier evidence insufficient.</p>
<p>The false-green demo makes this small enough to inspect: a failing unit test sits beside plausible-looking evidence. The work only reaches an accepted state after real verification.</p>
<h2>What I’m working on now</h2>
<p>The newer protected-admission experiment looks at the pull-request boundary. It observes changes to paths that can affect how work is checked or admitted, including tests, workflows, policy, permissions, and deployment configuration.</p>
<p>It currently runs in shadow mode. It is a path-based observation, not a semantic security scan, and it does not make merge decisions. The experiment needs evidence from real use before stronger enforcement makes sense.</p>
<h2>Where the boundary is</h2>
<p>Synrail complements tests and code review. Its local receipts do not establish a security boundary against an agent with the same machine access as the operator. These limits are part of the documentation and the work still ahead.</p>
''',
        'caption': 'The repository’s false-green demo. Follow the failing check and repair, or <a href="/synrail/#demo-transcript">read the transcript</a>.',
        'note': 'The local CLI remains an alpha. Protected admission is a separate, observation-only experiment.',
    },
    {
        'slug': 'rhook', 'name': 'RHOOK', 'status': 'Ongoing', 'kind': 'Onchain research',
        'summary': 'Changing one historical input, then replaying what happens to the transactions that follow.',
        'intro': 'A way to replay onchain execution after changing one declared historical input.',
        'technology': 'Execution & verification', 'context': 'Research implementation', 'media': 'rhook',
        'links': [
            ('GitHub', 'https://github.com/USBVadik/rhook'),
            ('Quickstart', 'https://github.com/USBVadik/rhook/blob/main/QUICKSTART.md'),
            ('Counterfactual model', 'https://github.com/USBVadik/rhook/blob/main/docs/counterfactual-model.md'),
            ('Robinhood example', 'https://github.com/USBVadik/rhook/tree/main/examples/robinhood-v4'),
            ('Current limitations', 'https://github.com/USBVadik/rhook/blob/main/docs/limitations.md'),
        ],
        'body': '''
<h2>One change, then what?</h2>
<p>Suppose one input in a historical blockchain execution had been different. Finding dependent transactions is a useful start, but it does not tell you whether those transactions would succeed, revert, or become invalid.</p>
<p>RHOOK executes the remaining transactions against the state produced by the changed branch. It records where the two histories first differ and enough evidence to explain the difference.</p>
<h2>What the replay keeps fixed</h2>
<p>The starting checkpoint, historical context, and transaction order are declared. One intervention changes the branch. Subsequent execution results and states are then regenerated.</p>
<p>The transcript records transaction identity, state commitments, execution status, fees, logs, and semantic values tied to a particular state. A separate verifier checks the relationships inside that record.</p>
<h2>The current work</h2>
<p>The repository has a small protocol-neutral example and a pinned Robinhood Chain v4 replay over 50 continuous blocks. Recent work has focused on reproducing that example on a clean Linux setup and making the verifier stricter about malformed evidence.</p>
<p>The Robinhood example changes a declared input while keeping the historical envelope for alignment. Its documentation explains that analytical boundary and the limits of the reproduction.</p>
<h2>Still a research implementation</h2>
<p>The current implementation is single-target and does not authenticate the transcript producer. It is not a production certification or a system for assigning liability. The repository keeps those boundaries explicit.</p>
<p>A separate historical Alchemix study informed this line of work. Its reported results are not presented as a benchmark of the current evidence stack.</p>
''',
        'caption': 'A schematic of the replay model. The changed branch regenerates downstream execution; these are not benchmark results.',
        'note': 'Current focus: reproducible execution examples and independently checked evidence.',
    },
    {
        'slug': 'onelink-pay', 'name': 'OneLink Pay', 'status': 'Hackathon project', 'kind': 'Payments',
        'summary': 'Spending permissions with limits, revocation, and a receipt you can inspect.',
        'intro': 'Scoped spending permissions for software, with an onchain budget and a verifiable payment receipt.',
        'technology': 'Particle / Magic / Arbitrum', 'context': 'UXmaxx 2026', 'media': 'onelink-pay',
        'links': [
            ('Open the app', 'https://onelink-pay.vercel.app/'),
            ('Replay a verified run', 'https://onelink-pay.vercel.app/demo-replay'),
            ('Try the spending limit', 'https://onelink-pay.vercel.app/try'),
            ('GitHub', 'https://github.com/USBVadik/OLP'),
            ('Hackathon results', 'https://www.encodeclub.com/programmes/uxmaxx-hackathon/'),
        ],
        'body': '''
<h2>A budget for software</h2>
<p>Giving software permission to pay raises a practical question: how much is it allowed to spend, with whom, and for how long? OneLink Pay makes those terms part of a signed mandate.</p>
<p>The mandate has per-charge, daily, and total limits, an expiry, and one approved merchant. The owner can revoke it. Requests outside the policy are rejected during preflight against the onchain contract.</p>
<h2>Connecting consent to payment</h2>
<p>Magic provides email and Google onboarding. Particle Universal Accounts handle the cross-chain payment path. The application connects those steps to a readable permission screen and a public receipt.</p>
<p>The verified demonstration includes a Base-to-Arbitrum funding flow. The research expense-card example buys two inputs and blocks an additional request above its per-charge limit.</p>
<h2>What the demo shows</h2>
<p>The research task is a deterministic workflow. It demonstrates payment and policy enforcement without claiming that an LLM independently reasons through the task. Recorded transactions and the replay page let someone inspect the result without connecting a wallet.</p>
<p>The app’s <a href="https://onelink-pay.vercel.app/trust">scope page</a> separates the verified flows from the parts that remain examples or future work.</p>
''',
        'award': {
            'label': 'Magic Labs Bonus Challenge winner',
            'body': 'OneLink Pay won the Magic Labs Bonus Challenge at UXmaxx 2026. The official results list a $500 prize. The final event was held on 21 August 2026.',
            'url': 'https://www.encodeclub.com/programmes/uxmaxx-hackathon/',
            'source_label': 'Official results on Encode', 'image': 'uxmaxx-certificate.png',
            'alt': 'UXmaxx certificate naming Vadik and OneLink Pay as a winner, August 2026.',
            'caption': 'Certificate issued for OneLink Pay, August 2026.',
        },
        'caption': 'The OneLink Pay interface, captured on 28 September 2026.',
        'note': 'Built for UXmaxx 2026. The public app includes recorded payment evidence and a wallet-free replay.',
    },
    {
        'slug': 'turingvault', 'name': 'TuringVault', 'status': 'Hackathon project', 'kind': 'AI & onchain systems',
        'summary': 'An AI portfolio experiment with recorded proposals, validation, and execution evidence.',
        'intro': 'An AI portfolio experiment on Mantle, built around decisions that can be inspected after the fact.',
        'technology': 'AI agents / Mantle', 'context': 'Turing Test 2026', 'media': 'turingvault',
        'links': [
            ('Open the app', 'https://turingvault.dev/'),
            ('DoraHacks submission', 'https://dorahacks.io/buidl/43986'),
            ('GitHub', 'https://github.com/USBVadik/TuringVault-Core'),
            ('Mantle announcement', 'https://x.com/Mantle_Official/status/2075596084936847787'),
            ('Project award note', 'https://x.com/a_seven_life/status/2091796580848308287'),
        ],
        'body': '''
<h2>Keeping the decision visible</h2>
<p>A transaction tells you what an agent did. Understanding why it acted requires more context. TuringVault records proposals, challenges, and execution outcomes around an AI portfolio workflow.</p>
<p>The project was built for the Mantle Turing Test Hackathon. Its application is an operator-funded demonstration using Mantle-native assets and yield infrastructure.</p>
<h2>Several checks before execution</h2>
<p>An analyst proposes an action. A separate validator challenges it, and deterministic checks can stop execution. Offchain records are anchored on Mantle so the decision trail can be inspected alongside the transactions.</p>
<p>The interface distinguishes an executed swap from a blocked proposal, a hold, or an intent that never executed. Keeping those states separate matters when assessing the system.</p>
<h2>Making the result inspectable</h2>
<p>The project includes a dashboard, proof explorer, replay view, contract links, and public workflow history. The DoraHacks submission documents the architecture and the verification path used for the hackathon.</p>
<p>The application remains an operator-funded demonstration, with no public deposits. Its recorded decisions can be inspected alongside their execution outcomes.</p>
''',
        'award': {
            'label': 'Project Deployment Award / Mantle Turing Test',
            'body': 'TuringVault received a Project Deployment Award in the Mantle Turing Test Hackathon 2026. It was also included in the AI Trading & Strategy Demo Day on 2 July. The project award note records a $1,000 prize.',
            'url': 'https://x.com/a_seven_life/status/2091796580848308287',
            'source_label': 'Read the project award note', 'image': 'mantle-demo-day.png',
            'alt': 'Mantle Turing Test 2026 Demo Day programme listing TuringVault in AI Trading and Strategy on 2 July.',
            'caption': 'Demo Day programme. The award announcement is linked separately above.',
        },
        'caption': 'The TuringVault agent console, captured on 29 September 2026. The image is a snapshot of the demo, not a live status feed.',
        'note': 'Built for the Mantle Turing Test 2026. Public application and source code remain available to inspect.',
    },
]
