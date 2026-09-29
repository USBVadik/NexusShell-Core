# Preview verification

29 September 2026. Interactive home, checked against the local Python HTTP server
before publication. Inner-page content and shared styles are unchanged from the
previous preview.

- Build: ten content pages, 404.html, the old Synrail redirect, sitemap, and robots.
  Python source compiles; the new JavaScript passes Node syntax checking.
- Static audit: 12 HTML files and 185 local link/asset references, with no missing
  targets or fragments, duplicate IDs, or missing image dimensions/alt text.
  Content pages have one H1. Canonical/OG metadata remains present.
- All four project panels checked at 320px: no horizontal overflow or broken
  loaded images. Synrail and RHOOK visually checked at 390px; Synrail at 768px;
  all four project layouts inspected on desktop at 1280px. Light and dark themes
  inspected. Appearance selection survives navigation.
- Project selection changes the hash and sole visible panel. Browser Back and
  direct-hash reload restore selection. Arrow keys and End move focus and select
  the corresponding project.
- Synrail: all three stages, next-step control, actual video dialog, and Escape
  checked. Escape pauses playback and restores focus to the launch link. The
  three proof stages each occupied 442px at the checked desktop size.
- RHOOK: original/changed modes, individual replay-node selection, and range End
  checked. Original mode disables alternate nodes and removes that branch from
  the accessibility tree. The explanatory text and aria-pressed values update.
- OneLink Pay: range Home yields 0.05 USDC; keyboard increments to 0.10 pass the
  illustrated check, and 0.15 fails. Other conditions are explicitly out of scope.
- TuringVault: Challenge and Record update the workflow explanation; the real
  screenshot retains its complete aspect ratio.
- A temporary script-free rendering verified the fallback: all project panels,
  descriptions, and three Synrail stages remain readable, project anchors work,
  and there is no overflow at 320px. The temporary file was removed.
- New home text-token contrast across defined surfaces: at least 4.64:1 in light
  mode and 6.73:1 in dark mode. This is a token check, not a full accessibility audit.
- Shared case routes, award disclosures, copy controls, old Synrail redirects,
  and all inner pages at 320px were verified in the preceding revision. They are
  unchanged; this revision concentrates browser checks on the new home.
- The legacy home #demo redirect was rechecked and still opens /synrail/#demo.
- Browser error logs were empty during the interactive checks.
- CSS/JS URLs have content hashes. git diff --check passes.

Limits: the examples explain behavior and distinguish recordings, models, and
local calculations. They do not execute Synrail or RHOOK, validate payment flows,
or establish product health. Public sources were checked when the case content
was written; this revision does not revalidate current repository state.
Lighthouse, production Core Web Vitals, and a full accessibility audit were not run.
