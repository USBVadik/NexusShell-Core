"""Render the Second Unit page and its entries in the existing portfolio."""
from html import escape as e
from second_unit_content import (TITLE, SUMMARY, DESCRIPTION, FILMS, STAGES,
                                REVIEWERS, MEMORY, CRAFT_NOTE, CASE, MEMORY_NOTE,
                                RECORDS, ENGINES_INTRO, ADAPTERS, FLUX_PLAN, CLOSING,
                                STUDY_MEDIA)


def process(prefix, compact=False):
    controls = ''.join(
        f'<button type="button" data-su-step="{i}" aria-controls="{prefix}-{s["id"]}" aria-pressed="{str(i == 0).lower()}"><span>{i+1:02}</span>{e(s["name"])}</button>'
        for i, s in enumerate(STAGES))
    frames = []
    for i, stage in enumerate(STAGES):
        frames.append(f'''<section class="su-step" id="{prefix}-{stage['id']}" data-su-frame="{i}" aria-labelledby="{prefix}-heading-{i}">
<div class="su-step-copy"><span class="su-step-index">{i+1:02} / {len(STAGES):02} · {e(stage['name'])}</span><h3 id="{prefix}-heading-{i}">{e(stage['title'])}</h3><p>{e(stage['body'])}</p></div>
<dl class="su-step-record"><div><dt>Starts with</dt><dd>{e(stage['input'])}</dd></div><div><dt>Leaves behind</dt><dd>{e(stage['output'])}</dd></div><div><dt>Review</dt><dd>{e(stage['check'])}</dd></div><div class="su-human"><dt>Your decision</dt><dd>{e(stage['human'])}</dd></div></dl></section>''')
    return f'''<div class="su-process {'su-process-compact' if compact else ''}" data-su-process><div class="su-process-bar"><span>Production workflow</span><span>Explore the method</span></div><div class="su-stage-controls" role="group" aria-label="Production stages" hidden>{controls}</div><div class="su-process-output" aria-live="polite" aria-atomic="true">{''.join(frames)}</div><div class="su-process-bottom"><span>Human approval at the creative decisions.</span><span>Each film feeds the next ↶</span></div></div>'''


def films():
    if not FILMS:
        return ''
    items = []
    for film in FILMS:
        stills = ''
        if film.get('stills'):
            frames = ''.join(f'<a href="{e(frame["src"], quote=True)}" target="_blank" rel="noopener"><img src="{e(frame["src"], quote=True)}" width="480" height="270" loading="lazy" alt="{e(frame["alt"], quote=True)}"></a>' for frame in film['stills'])
            stills = f'<div class="su-film-stills" aria-label="Four frames from the film">{frames}</div>'
        sheet = ''
        if film.get('sheet'):
            sheet = f'<details class="su-contact-sheet"><summary>Inspect the shot sheet <span aria-hidden="true">+</span></summary><a href="{e(film["sheet"], quote=True)}" target="_blank" rel="noopener"><img src="{e(film["sheet"], quote=True)}" width="1536" height="944" loading="lazy" alt="Contact sheet showing the sequence of shots in Gravity turns off on Tuesdays."></a></details>'
        items.append(f'''<article class="su-film su-film-{film['id']}"><figure><video controls playsinline preload="none" poster="{e(film['poster'], quote=True)}" width="{int(film['width'])}" height="{int(film['height'])}" aria-label="{e(film['title'], quote=True)}"><source src="{e(film['src'], quote=True)}" type="video/mp4"><a href="{e(film['src'], quote=True)}">Open the film</a></video><figcaption><div><h3>{e(film['title'])}</h3><span>{e(film['duration'])} · {e(film['audio'])}</span></div><p>{e(film['caption'])}</p></figcaption></figure>{stills}{sheet}</article>''')
    return f'<section class="su-section" id="films"><div class="su-section-heading"><h2>Made with Second Unit.</h2><p>Two complete films, followed by the production decisions behind them.</p></div><div class="su-films">{"".join(items)}</div></section>'


def previews():
    if not FILMS:
        return ''
    videos = ''.join(f'<video class="su-preview su-preview-{film["id"]}" muted loop playsinline preload="none" width="{film["width"]}" height="{film["height"]}" poster="{film["poster"]}" data-su-preview="{film["preview"]}" aria-label="Silent six-second excerpt from {e(film["title"], quote=True)}"></video>' for film in FILMS)
    return f'<div class="su-preview-pair" data-su-previews>{videos}<button class="su-preview-toggle" type="button" data-su-preview-toggle hidden>Play previews</button></div>'


def colour_study():
    if not FILMS:
        return ''
    return f'''<figure class="su-colour-study"><a href="{STUDY_MEDIA['colour']}" target="_blank" rel="noopener"><img src="{STUDY_MEDIA['colour']}" width="1520" height="960" loading="lazy" alt="Lawn Wars colour study comparing r6, r7 and r7b across the same shots."></a><figcaption><strong>Three passes, one decision.</strong><p>The r7 and r7b attempts to unify the grade were rejected. The final r6b kept the r6 colour and replaced one short motion window. Open the sheet to compare the frames.</p></figcaption></figure>'''


def upscale_study():
    if not FILMS:
        return ''
    return f'''<section class="su-section" id="upscale"><div class="su-section-heading"><h2>Inspect the finishing choices.</h2><p>A six-second comparison from Lawn Wars: Lanczos on the left, Omni on the right. This is an A/B study; the final upscale method has not been chosen.</p></div><div class="su-upscale-grid"><figure><video controls playsinline preload="none" width="1080" height="1920" poster="{STUDY_MEDIA['upscale_poster']}" aria-label="Lanczos versus Omni upscale comparison, silent"><source src="{STUDY_MEDIA['upscale_video']}" type="video/mp4"><a href="{STUDY_MEDIA['upscale_video']}">Open the comparison</a></video><figcaption>Same shot, two upscale methods. Silent comparison.</figcaption></figure><figure><a href="{STUDY_MEDIA['upscale_crops']}" target="_blank" rel="noopener"><img src="{STUDY_MEDIA['upscale_crops']}" width="1080" height="1440" loading="lazy" alt="Native-resolution comparison crops of the face and lawn after Lanczos and Omni upscaling."></a><figcaption>Detail crops from the study. Open the original sheet to inspect at its native resolution.</figcaption></figure></div></section>'''


def render_home_panel():
    return f'''<section class="desk-panel" id="second-unit" aria-labelledby="title-second-unit"><header class="desk-project-heading"><div><p class="desk-eyebrow">Production workflow <span aria-hidden="true">/</span> AI filmmaking</p><h2 id="title-second-unit" tabindex="-1">Second Unit</h2><p class="desk-description">{SUMMARY}</p></div><div class="desk-project-links"><a href="/second-unit/">Product page <span aria-hidden="true">↗</span></a></div></header>{process('home-production', compact=True)}<div class="experiment-footnote"><span>A walkthrough of the production method. No generation runs in your browser.</span></div><a class="desk-development" href="/second-unit/#learning"><span class="development-label">The learning loop</span><span>What a rejected colour pass changed in the next review</span><span aria-hidden="true">↗</span></a></section>'''


def render_catalog_entry():
    return f'''<a class="su-catalog-entry" href="/second-unit/"><div><span class="su-catalog-label">Ongoing / AI filmmaking</span><h3>Second Unit <span aria-hidden="true">↗</span></h3><p>{SUMMARY}</p></div><div class="su-catalog-method">Brief <span>→</span> Shots <span>→</span> Review <span>→</span> Cut <span>↶</span></div></a>'''


def render_page():
    film_link = '<a class="su-action" href="#films">Watch the films <span aria-hidden="true">↘</span></a>' if FILMS else ''
    reviewers = ''.join(f'''<details class="su-reviewer"><summary><span class="su-reviewer-role">{e(role)}<small>{e(code)}</small></span><span>{e(question)}</span><span class="su-expand" aria-hidden="true">+</span></summary><p>{e(body)}</p></details>''' for role, code, question, body in REVIEWERS)
    memory = ''.join(f'<li><span>{i+1:02}</span><div><h3>{e(name)}</h3><p>{e(body)}</p></div></li>' for i, (name, body) in enumerate(MEMORY))
    case_copy = ''.join(f'<p>{e(p)}</p>' for p in CASE['paragraphs'])
    rule_title = '<br>'.join(e(line) for line in CASE['rule_lines'])
    before_copy = ''.join(f'<p>{e(p)}</p>' for p in RECORDS['before'])
    records = ''.join(f'<li>{e(item)}</li>' for item in RECORDS['after'])
    adapters = ''.join(f'<div class="{"su-planned" if status == "Planned" else ""}"><dt>{e(role)}</dt><dd>{e(model)}</dd><span>{e(status)}</span></div>' for role, model, status in ADAPTERS)
    closing = '<br>'.join(e(line) for line in CLOSING)
    hero_art = previews() or '<div class="su-frame-art" aria-hidden="true"><div class="su-art-frame su-art-frame-back"></div><div class="su-art-frame su-art-frame-front"><span class="su-art-corner su-art-corner-tl"></span><span class="su-art-corner su-art-corner-tr"></span><span class="su-art-number">02</span><span class="su-art-corner su-art-corner-bl"></span><span class="su-art-corner su-art-corner-br"></span><span class="su-art-cross"></span></div><span class="su-art-arrow">↶</span></div>'
    return f'''<article class="su-page">
<nav class="su-breadcrumb" aria-label="Breadcrumb"><a href="/">NexusShell</a><span aria-hidden="true">/</span><span>Second Unit</span></nav>
<header class="su-hero"><div><p class="su-byline"><span class="su-byline-mark" aria-hidden="true">02</span> AI filmmaking / Ongoing work</p><h1>Second <span class="su-title-unit">Unit</span></h1><p class="su-headline">{SUMMARY}</p><p class="su-intro">{DESCRIPTION}</p><div class="su-actions">{film_link}<a class="su-action" href="#workflow">Explore the workflow <span aria-hidden="true">↘</span></a></div></div><figure class="su-production-art"><div class="su-art-caption"><span>Second Unit</span><span>{'Film excerpts' if FILMS else 'The working method'}</span></div>{hero_art}<figcaption><p>Plan the scene.<br>Review the take.<br><span>Remember the correction.</span></p><span>Creative decisions stay with the director.</span></figcaption></figure></header>
{films()}
<section class="su-section su-workflow" id="workflow"><div class="su-section-heading"><h2>From brief to delivery.</h2><p>Character masters, scene maps, review checklists and edit scripts give each generation a place in the film. Explore what each stage uses and leaves behind.</p></div>{process('production')}</section>
<section class="su-section" id="review"><div class="su-section-heading"><h2>Review is part of the workflow.</h2><p>Separate reviewer agents inspect the work. The director approves the keyframes and the cut before accepted takes move to delivery.</p></div><div class="su-reviewers">{reviewers}</div><p class="su-craft-note">{e(CRAFT_NOTE)}</p></section>
<section class="su-section" id="learning"><div class="su-section-heading"><h2>The colour check passed.<br>The director sent it back.</h2><p>{e(CASE['intro'])}</p></div><div class="su-case"><div class="su-case-label"><span>Production note</span><strong>{e(CASE['title'])}</strong><span>{e(CASE['version'])}</span></div><div class="su-case-story">{case_copy}<div class="su-rule"><span>The rule that changed</span><h3>{rule_title}</h3><p>{e(CASE['rule'])}</p></div></div></div>{colour_study()}
<div class="su-memory"><h3>What the next film remembers.</h3><ol>{memory}</ol><p class="su-memory-note">{e(MEMORY_NOTE)}</p></div></section>
{upscale_study()}<section class="su-section" id="records"><div class="su-section-heading"><h2>Keep the production inspectable.</h2><p>{e(RECORDS['intro'])}</p></div><div class="su-record-grid"><div><h3>Before a job runs</h3>{before_copy}</div><div><h3>After a take is accepted</h3><ul>{records}</ul><p>{e(RECORDS['conclusion'])}</p></div></div></section>
<section class="su-section su-engines" id="engines"><div class="su-section-heading"><h2>Current engines.<br>Next: FLUX.</h2><p>{e(ENGINES_INTRO)}</p></div><dl class="su-adapters">{adapters}</dl><p class="su-engine-note">{e(FLUX_PLAN)}</p><a class="su-text-link" href="https://www.encodeclub.com/programmes/bfl-flux-in-production" target="_blank" rel="noopener noreferrer">FLUX: In Production programme <span aria-hidden="true">↗</span></a></section>
<div class="su-closing"><p>{closing}</p><a href="https://x.com/a_seven_life" class="su-text-link">Talk about the workflow <span aria-hidden="true">↗</span></a></div>
</article>'''
