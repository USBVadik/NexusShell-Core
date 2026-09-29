#!/usr/bin/env python3
"""Build plain HTML for GitHub Pages. Run: python3 website/build.py"""
from pathlib import Path
from html import escape
import json
from hashlib import sha256
from content import PROJECTS, UPDATES
from desk import render as render_desk

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://nexusshell.dev'
e = escape
PAGES = []


def asset(path):
    digest = sha256((ROOT / path.lstrip('/')).read_bytes()).hexdigest()[:12]
    return path + '?v=' + digest


def link(label, href, cls=''):
    extra = ' rel="noopener noreferrer" target="_blank"' if href.startswith('https://') else ''
    return f'<a href="{e(href, quote=True)}" class="{e(cls)}"{extra}>{e(label)}<span class="arrow" aria-hidden="true">↗</span></a>'


def header(active):
    nav = ''
    for label, href in [('Projects', '/projects/'), ('About', '/about/'), ('Updates', '/updates/')]:
        current = ' aria-current="page"' if label == active else ''
        nav += f'<a href="{href}"{current}>{label}</a>'
    return f'''<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="/" aria-label="NexusShell home"><span class="brand-mark" aria-hidden="true">n</span>nexusshell</a>
<nav class="primary-nav" aria-label="Main navigation">{nav}{link('GitHub', 'https://github.com/USBVadik')}</nav>
<label class="sr-only" for="theme">Appearance</label><select class="theme-control" id="theme" data-theme-select hidden><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select>
</div></header>'''


def footer():
    return f'''<footer class="site-footer" id="contact"><div class="wrap">
<div class="contact-row"><div><h2>Have something<br>in mind?</h2><p>A question, an idea, or something worth building.</p></div>
<div class="contact-links">{link('GitHub', 'https://github.com/USBVadik')}{link('Say hello on X', 'https://x.com/a_seven_life')}</div></div>
<div class="footer-bottom"><p>NexusShell <span aria-hidden="true">/</span> Vadik</p><p><a href="/updates/">Updates from the work</a></p></div>
</div></footer>'''


def page(path, title, description, body, active='', schema=None):
    canonical = BASE + path
    structured = schema or {'@context': 'https://schema.org', '@type': 'WebPage', 'name': title, 'url': canonical,
                           'isPartOf': {'@type': 'WebSite', 'name': 'NexusShell', 'url': BASE + '/'}}
    desk_assets = f'<link rel="stylesheet" href="{asset("/assets/desk.css")}"><script defer src="{asset("/assets/desk.js")}"></script>' if path == '/' else ''
    page_footer = '<footer class="desk-footer" id="contact"><span>NexusShell / Vadik</span><div><a href="https://github.com/USBVadik">GitHub ↗</a><a href="https://x.com/a_seven_life">Say hello on X ↗</a></div></footer>' if path == '/' else footer()
    text = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(description, quote=True)}"><link rel="canonical" href="{canonical}">
<meta name="color-scheme" content="light dark"><meta name="theme-color" content="#f7f6f2" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#141618" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website"><meta property="og:site_name" content="NexusShell"><meta property="og:title" content="{e(title, quote=True)}"><meta property="og:description" content="{e(description, quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}/assets/media/nexusshell-preview.jpg"><meta property="og:image:alt" content="NexusShell, the projects and ongoing work of Vadik."><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="preload" href="/assets/fonts/manrope-regular.ttf" as="font" type="font/ttf" crossorigin>
<script>try{{const t=localStorage.getItem('nexusshell-theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t;}}catch(_){{}}</script>
<link rel="stylesheet" href="{asset('/assets/site.css')}"><script defer src="{asset('/assets/site.js')}"></script>
{desk_assets}<script type="application/ld+json">{json.dumps(structured, ensure_ascii=False).replace('<', chr(92)+'u003c')}</script>
</head><body class="{'home-page' if path == '/' else 'inner-page'}">{header(active)}<main id="main" class="wrap">{body}</main>{page_footer}</body></html>
'''
    dest = ROOT / (path.strip('/') + '/index.html' if path != '/' else 'index.html')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding='utf-8')
    PAGES.append(path)


def branch_diagram():
    return '''<div class="branch-figure"><svg viewBox="0 0 490 220" role="img" aria-label="RHOOK replay model: an original branch A, B, X, C, D is compared with a branch where X is changed and C and D are recomputed.">
<text class="label" x="20" y="25">Historical execution</text><text class="label accent-text" x="20" y="205">Replay after one changed input</text>
<path class="track" d="M45 70H445"/><path class="changed-track" d="M145 70C195 70 190 149 245 149H445"/>
<rect class="node" x="23" y="48" width="44" height="44" rx="8"/><text x="45" y="76" text-anchor="middle">A</text>
<rect class="node" x="123" y="48" width="44" height="44" rx="8"/><text x="145" y="76" text-anchor="middle">B</text>
<rect class="node" x="223" y="48" width="44" height="44" rx="8"/><text x="245" y="76" text-anchor="middle">X</text>
<rect class="node" x="323" y="48" width="44" height="44" rx="8"/><text x="345" y="76" text-anchor="middle">C</text>
<rect class="node" x="423" y="48" width="44" height="44" rx="8"/><text x="445" y="76" text-anchor="middle">D</text>
<rect class="changed-node" x="223" y="127" width="44" height="44" rx="8"/><text class="accent-text" x="245" y="155" text-anchor="middle">X′</text>
<rect class="changed-node" x="323" y="127" width="44" height="44" rx="8"/><text class="accent-text" x="345" y="155" text-anchor="middle">C′</text>
<rect class="changed-node" x="423" y="127" width="44" height="44" rx="8"/><text class="accent-text" x="445" y="155" text-anchor="middle">D′</text>
</svg></div>'''


def visual(project, full=False):
    media = project['media']
    if media == 'rhook':
        return branch_diagram()
    if media == 'synrail':
        if full:
            return '<video controls playsinline preload="none" width="1500" height="760" poster="/assets/media/synrail-demo.png" aria-label="Synrail false-green verification demo"><source src="/assets/media/synrail-demo.mp4" type="video/mp4"><a href="/assets/media/synrail-demo.mp4">Watch the Synrail demo</a></video>'
        return '<img src="/assets/media/synrail-demo.png" alt="The Synrail demo, showing a failed verification followed by an accepted result." width="1500" height="760" fetchpriority="high">'
    filename = 'onelink-pay-app.jpg' if media == 'onelink-pay' else 'turingvault-console.jpg'
    width,height = (1280,720) if media == 'onelink-pay' else (1152,617)
    return f'<img src="/assets/media/{filename}" alt="{e(project["name"])} application interface." width="{width}" height="{height}" loading="lazy">'


def current_card(project):
    return f'''<a class="project-card" href="/projects/{project['slug']}/"><div class="project-title card-heading"><h3>{project['name']}</h3><span class="project-status">{project['status']}</span></div><div class="project-visual {project['media']}">{visual(project)}</div>
<div class="project-card-body">
<p>{project['summary']}</p><div class="project-card-foot"><span class="project-kind">{project['kind']}</span><span>View project <span class="arrow" aria-hidden="true">↗</span></span></div></div></a>'''


def other_card(project):
    return f'''<a class="other-card" href="/projects/{project['slug']}/"><div class="other-image">{visual(project)}</div>
<div class="other-caption"><h3>{project['name']} <span class="arrow" aria-hidden="true">↗</span></h3><p>{project['summary']}</p><div class="quiet-meta">{project['context']} <span aria-hidden="true">/</span> {project['kind']}</div></div></a>'''


def home():
    page('/', 'NexusShell | Vadik’s project desk', 'Explore the work of Vadik: Synrail, RHOOK, OneLink Pay and TuringVault, with interactive walkthroughs, source code and development notes.', render_desk(PROJECTS, UPDATES, visual))


def catalog():
    body = f'''<section class="page-intro"><a class="breadcrumb" href="/">NexusShell</a><h1>Projects</h1><p class="lede">The tools and applications I’ve been working on, with source code, examples, and some context.</p></section>
<section class="section first-section catalog-section"><h2 class="catalog-label">Ongoing</h2><div class="work-grid">{''.join(current_card(p) for p in PROJECTS[:2])}</div></section>
<section class="section catalog-section"><h2 class="catalog-label">Applications &amp; experiments</h2><div class="other-grid">{''.join(other_card(p) for p in PROJECTS[2:])}</div>
<div class="origin-row"><p>Telegram bots and agent automation, where the hands-on work began.</p><a href="/projects/agent-automation/">Early work <span class="arrow" aria-hidden="true">↗</span></a></div></section>'''
    page('/projects/', 'Projects | NexusShell', 'Ongoing tools, onchain applications, and agent automation by Vadik.', body, 'Projects')


def project_page(project, next_project):
    p = project
    updates = [u for u in UPDATES if u['project'] == p['name']]
    history = ''
    if updates:
        history = '<h2>Changes along the way</h2><ul class="case-updates">' + ''.join(f'<li><time datetime="{u["date"]}">{u["display_date"]}</time>{link(u["title"],u["url"])}</li>' for u in updates) + '</ul>'
    award = ''
    if p.get('award'):
        a = p['award']
        aw,ah=(1492,1054) if p['slug']=='onelink-pay' else (1200,675)
        award = f'''<details class="recognition"><summary>{a['label']}</summary><div class="recognition-body"><p>{a['body']}</p><p>{link(a['source_label'], a['url'])}</p><a href="/assets/media/{a['image']}" target="_blank" rel="noopener"><img src="/assets/media/{a['image']}" alt="{e(a['alt'], quote=True)}" width="{aw}" height="{ah}" loading="lazy"></a><p class="evidence-caption">{a['caption']} Open the image to view it in full.</p></div></details>'''
    body = f'''<section class="page-intro"><a class="breadcrumb" href="/projects/">← All projects</a><h1>{p['name']}</h1><p class="lede">{p['intro']}</p><div class="project-meta"><span class="{'ongoing' if p['status']=='Ongoing' else ''}">{p['status']}</span><span>{p['context']}</span><span>{p['technology']}</span></div></section>
<figure><div class="hero-media {'demo' if p['media']=='synrail' else ''}">{visual(p,True)}</div><figcaption>{p['caption']}</figcaption></figure>
<div class="case-layout"><article class="prose">{p['body']}{award}{history}</article><aside class="case-aside"><h2>Explore the project</h2><ul>{''.join('<li>'+link(label,url)+'</li>' for label,url in p['links'])}</ul><p>{p['note']}</p><span class="aside-label">Part of</span><span class="aside-value">NexusShell / Vadik</span></aside></div>
<a class="next-project" href="/projects/{next_project['slug']}/"><div><small>Another project</small><span>{next_project['name']}</span></div><span aria-hidden="true">↗</span></a>'''
    page(f'/projects/{p["slug"]}/', p['name']+' | NexusShell', p['intro'], body, 'Projects')


def about():
    body = '''<section class="page-intro"><a class="breadcrumb" href="/">NexusShell</a><h1>Hi, I’m Vadik.</h1><p class="lede">I build software with AI agents and work on tools for understanding what that software actually does.</p></section>
<div class="about-layout"><aside class="about-facts"><p><strong>Online</strong>USBVadik / a_seven_life</p><p><strong>Current focus</strong>Synrail and RHOOK</p><p><strong>This site</strong>Projects, context, and updates</p></aside>
<article class="prose about-story"><h2>How it started</h2><p>My first hands-on projects were Telegram bots and agent automation. I was setting things up on a remote server, connecting tools, and learning by getting them to run.</p>
<p>Hackathons gave the work a more concrete shape. TuringVault explored inspectable AI decisions on Mantle. OneLink Pay explored what software should be allowed to spend, and how a person could keep control of that permission.</p>
<h2>What I’m spending time on</h2><p>Synrail and RHOOK are ongoing work. With Synrail, the question is what evidence a coding agent needs before calling a task complete. With RHOOK, it is what changes downstream when one historical input is different.</p>
<p>Both involve coming back to the details: verification behavior, examples that someone else can run, and documentation that describes the limits. The <a href="/updates/">updates page</a> links to some of those changes.</p>
<h2>Working with agents</h2><p>AI agents are part of how I build. That experience also shapes the problems I choose to work on. The source code and project pages are here so the work can be inspected, tried, and discussed.</p>
<h2>A few milestones</h2><p>OneLink Pay won the <a href="https://www.encodeclub.com/programmes/uxmaxx-hackathon/">Magic Labs Bonus Challenge at UXmaxx 2026</a>. TuringVault received a <a href="https://x.com/a_seven_life/status/2091796580848308287">Project Deployment Award at the Mantle Turing Test Hackathon</a> and appeared in its AI Trading &amp; Strategy Demo Day.</p>
<p>The project pages have the demos, supporting material, and a little more about the implementation.</p>
<ul class="about-projects"><li><a href="/projects/synrail/">Synrail <small>Checking agent work</small></a></li><li><a href="/projects/rhook/">RHOOK <small>Replaying onchain execution</small></a></li><li><a href="/projects/onelink-pay/">OneLink Pay <small>Scoped spending permissions</small></a></li><li><a href="/projects/turingvault/">TuringVault <small>Inspectable AI decisions</small></a></li></ul></article></div>'''
    schema = {'@context':'https://schema.org','@type':'Person','name':'Vadik','alternateName':'USBVadik','url':BASE+'/about/','sameAs':['https://github.com/USBVadik','https://x.com/a_seven_life']}
    page('/about/', 'About Vadik | NexusShell', 'A little background on Vadik, the projects, and the ongoing work on Synrail and RHOOK.', body, 'About', schema)


def updates_page():
    entries = ''.join(f'''<article class="update-entry"><time datetime="{u['date']}">{u['display_date']}</time><div><a class="tag" href="/projects/{u['project'].lower()}/">{u['project']}</a><h2>{u['title']}</h2><p>{u['body']}</p>{link(u['label'],u['url'],'text-link')}</div></article>''' for u in UPDATES)
    body = f'''<section class="page-intro updates-intro"><a class="breadcrumb" href="/">NexusShell</a><h1>Updates from the work.</h1><p class="lede">A few changes worth keeping track of. Each entry links to the work in the repository.</p></section>{entries}'''
    page('/updates/', 'Updates | NexusShell', 'Development notes from Synrail and RHOOK, with dates and links to the work.', body, 'Updates')


def automation_page():
    body = '''<section class="page-intro"><a class="breadcrumb" href="/projects/">← All projects</a><h1>Bots &amp; agent automation.</h1><p class="lede">The first practical experiments behind NexusShell.</p><div class="project-meta"><span>Early work</span><span>Telegram / agent tooling</span></div></section>
<div class="case-layout"><article class="prose"><h2>Starting with something useful</h2><p>The early work was about setting up Telegram bots and connecting agents to everyday tasks: configuring tools, connecting integrations, and getting them to run.</p><p>These were my first hands-on experiments with agent automation. They came before the hackathon applications and the more focused work on verification.</p><h2>Where the work went next</h2><p>TuringVault and OneLink Pay turned some of those interests into applications with a specific user flow. Synrail and RHOOK now take more of my attention, with a closer look at checking work and explaining execution.</p><p>The original NexusShell repository still contains the earlier automation code alongside this site.</p></article><aside class="case-aside"><h2>Related work</h2><ul><li><a href="https://github.com/USBVadik/NexusShell-Core">Original repository ↗</a></li><li><a href="/projects/synrail/">Synrail →</a></li><li><a href="/about/">More background →</a></li></ul></aside></div>'''
    page('/projects/agent-automation/', 'Bots & agent automation | NexusShell', 'The early Telegram bots and agent automation experiments behind NexusShell.', body, 'Projects')


def product_page():
    p=PROJECTS[0]
    body=f'''<section class="page-intro"><a class="breadcrumb" href="/">NexusShell</a><h1>Synrail</h1><p class="lede">Check the evidence before accepting a coding agent’s work.</p><div class="project-meta"><span class="ongoing">Open-source alpha</span><span>Local CLI</span><span>Python 3.11-3.14</span></div><div class="action-links"><a class="action-link primary" href="#run">Run the demo</a>{link('GitHub','https://github.com/USBVadik/synrail','action-link')}</div></section>
<figure id="demo"><div class="hero-media demo">{visual(p,True)}</div><figcaption>The false-green demo: plausible evidence, a failing check, and a repair. <a href="#demo-transcript">Read the transcript.</a></figcaption></figure>
<div class="case-layout"><article class="prose"><h2 id="why">What it checks</h2><p>A claim that a task is done is different from evidence that the work passed its checks. Synrail binds the task, current patch, and verification result before returning an accepted status.</p><p>Missing, stale, or mismatched proof produces a reason and a bounded next step. Synrail works alongside CI and code review.</p>
<h2 id="run">Try the local demo</h2><p>The standalone demo creates a disposable example. It starts with a real failing test, then shows what changes after the behavior is repaired and verified.</p>
<div class="command"><button class="copy-button" type="button" data-copy hidden>Copy</button><pre><code>git clone https://github.com/USBVadik/synrail
cd synrail
make install-dev
make demo</code></pre><span class="copy-status" role="status" aria-live="polite"></span></div>
<p>See the <a href="https://github.com/USBVadik/synrail/blob/main/docs/core/FIRST_RUN_GUIDE.md">first-run guide</a> for installation details, Windows setup, and use in an existing project.</p>
<h2 id="use">A small workflow</h2><p>Start a task, make the change, run the required verification, record the evidence, and check it. For behavior claims, a fresh verification receipt is part of acceptance.</p>
<h2>Also in progress</h2><p>The protected-admission shadow experiment observes pull requests that change conventional test, CI, policy, permission, or deployment paths. It is non-blocking and does not replace review. <a href="https://github.com/USBVadik/synrail/blob/main/docs/core/PROTECTED_ADMISSION_SHADOW.md">Read the current scope.</a></p>
<h2>Limits</h2><p>Synrail cannot prove universal correctness. The local tool is not a security boundary against an agent with the operator’s machine access. The alpha and the shadow experiment have different scopes, documented in the repository.</p>
<details class="recognition" id="demo-transcript"><summary>Demo transcript</summary><div class="recognition-body"><p>The agent claims the function is fixed and tests pass. Its initial proof is a text search.</p><div class="command"><pre><code>$ synrail verify
Verification unit: FAIL (exit 1)
$ synrail check
Synrail: Status: Verification Failed

# After the behavior is repaired:
$ synrail verify
Verification unit: GREEN
$ synrail check
Synrail: Status: Accepted</code></pre></div><p>The recording is from the <a href="https://github.com/USBVadik/synrail/tree/main/examples/false-green-demo">public demo in the repository</a>.</p></div></details>
<h2 id="transparency">Background and ongoing work</h2><p>Synrail is one of the projects I’m continuing to work on through NexusShell. The <a href="/projects/synrail/">project page</a> has more context and recent changes.</p></article><aside class="case-aside"><h2>Project links</h2><ul>{''.join('<li>'+link(label,url)+'</li>' for label,url in p['links'][1:])}</ul><p>Feedback on a real agent task is useful. <a href="https://github.com/USBVadik/synrail/issues">Open an issue on GitHub.</a></p></aside></div>'''
    page('/synrail/', 'Synrail | Check the evidence behind agent work', 'A local acceptance gate for coding agents. Try the false-green demo and read the limits of the current alpha.',body)


def finish():
    (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{BASE}{path}</loc></url>\n' for path in PAGES)+'</urlset>\n')
    (ROOT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    page('/404/', 'Page not found | NexusShell', 'Find the projects and ongoing work on NexusShell.', '<section class="not-found"><p class="byline">404</p><h1>This page isn’t here.</h1><p>The address may have changed. You can find the current work in the project index.</p><a class="action-link primary" href="/projects/">View projects</a></section>')
    error_page=(ROOT/'404/index.html').read_text().replace(BASE+'/404/', BASE+'/404.html').replace('<title>', '<meta name="robots" content="noindex"><title>',1)
    (ROOT/'404.html').write_text(error_page)
    (ROOT/'404/index.html').unlink()
    (ROOT/'404').rmdir()
    (ROOT/'synrail.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synrail | NexusShell</title><link rel="canonical" href="https://nexusshell.dev/synrail/"><meta http-equiv="refresh" content="0;url=/synrail/"></head><body><p><a href="/synrail/">Open the Synrail page</a></p><script>location.replace('/synrail/'+location.hash);</script></body></html>''')


if __name__ == '__main__':
    home()
    catalog()
    for i, project in enumerate(PROJECTS):
        project_page(project, PROJECTS[(i+1)%len(PROJECTS)])
    about()
    updates_page()
    automation_page()
    product_page()
    finish()
    print(f'Built {len(PAGES)-1} pages plus 404.html. No runtime dependencies.')
