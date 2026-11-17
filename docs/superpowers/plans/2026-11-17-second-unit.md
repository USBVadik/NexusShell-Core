# Second Unit Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this approved draft inline.

**Goal:** Add an English product page and an ongoing-project entry for Second Unit, ready for the user's selected films.
**Architecture:** Extend the existing static Python builder. Keep editorial data, reusable rendering, scoped CSS, and progressive interaction separate.
**Tech Stack:** Python 3.11+, native HTML/CSS/JavaScript, existing GitHub Pages hosting.
**Spec:** `docs/superpowers/specs/2026-11-17-second-unit-design.md`, approved by the user in chat.

## Global Constraints

- Draft only; no deployment in this step. Videos will be selected by the user later.
- No new personal attribution, public generator, FLUX implementation claim, paid calls, or private assets.
- Preserve existing routes and keyboard navigation. Current work remains first.
- Native controls, readable no-JavaScript fallback, both themes, 320px minimum layout.

## Review Focus

- An empty film list must produce no broken player or link to a missing section.
- Direct selection of Second Unit on the home must work with history and existing projects.
- Without JavaScript the complete process remains readable.
- Imported text must not expose private paths or turn planned capabilities into shipped claims.
- Adding a fifth project must not break existing hard-coded four-project case generation.

### Task 1: Product page and process component

Files: create `website/second_unit_content.py`, `website/second_unit.py`, `assets/second-unit.css`, `assets/second-unit.js`; modify `website/build.py`.

Interfaces: content exports `STAGES`, `REVIEWERS`, `FILMS=[]`; renderer exports `render_page()`, `render_home_panel()`, `render_catalog_entry()`. All return HTML strings. Stage controls target IDs scoped to each component instance.

- [x] Implement approved copy and a six-stage process with explicit human decisions.
- [x] Render `/second-unit/` with its own metadata and optional selected-film section.
- [x] Add scoped styles and progressive stage selection, arrows, Home/End, and pressed states.
- [x] Build and check syntax, assets, fragments, and absence of empty media.

### Task 2: Hub integration and verification

Files: modify `website/desk.py`, `website/build.py`, `WEBSITE.md`; generated root/catalog/page/sitemap; update draft verification notes.

- [x] Add Second Unit as ongoing work without inserting into the four existing case records.
- [x] Check the new page and home entry at 320/768/1280px, both themes, keyboard and history.
- [x] Review the changes independently and fix material findings.
- [x] Save a screenshot, leave a local preview, and commit the draft.

Validation uses the builder, a static link audit, JavaScript syntax checks, and browser interactions. No implementation-mirroring unit tests are added for this reversible presentation change, following the session's developer instructions.

## Progress

- Design approved. Working branch: `codex/second-unit`, based on published `origin/main`.
- Existing dedicated checkout reused; no unrelated edits were present.

- Task 1 complete: product route, editorial data, six-stage progressive component.
- Task 2 complete: home/catalog integration, responsive/browser/static verification, independent review and fixes.
- Verification: build 11 content pages; 13 HTML documents, 205 local references, no missing targets or fragments; Python/JS syntax and diff checks pass.
- Ruling: keep this approved draft on its local branch until films are selected and the complete presentation reviewed. No push, PR, merge, or deployment in this step.

## Authorized publication update

The owner subsequently requested publication of the complete product page with
all selected films and production studies, and delivered the eight media inputs.
This explicit instruction supersedes the earlier draft-only integration ruling.
Publish through the existing GitHub Pages branch after file, code and HTTP checks.
