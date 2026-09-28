# Preview verification

28 September 2026. Updated for the third visual preview; checked against the local Python HTTP server, before publication.

- The builder emits ten content pages, `404.html`, the old Synrail redirect,
  `sitemap.xml`, and `robots.txt`. Its source parses as Python 3.11.
- Static audit: 12 HTML files and 182 local link/asset references (absolute canonical and OG URLs excluded), with no
  missing files, broken fragments, duplicate IDs, or missing image dimensions/alt
  attributes. Content pages have one H1, a description, language, and canonical URL.
- Every original ID on the home and Synrail product page remains available.
- Browser checks: all ten content pages and the error page at 320px. No horizontal
  overflow or broken loaded images. Also inspected the home and video dialog at
  390px, and the home at 768, 1024, 1280, 1440, and 1920px.
  On desktop the two application images, titles, and metadata share their top
  coordinates. Images fit their frames without cropping. The entire page was
  inspected by section, including RHOOK, the gallery, notes, and footer.
- Both themes inspected again after the palette and typography changes. Selecting dark survives a reload. System mode is the
  default and can be restored from the Appearance control.
- Minimum text-token contrast across the page surfaces: 4.88:1 in light mode and
  6.89:1 in dark mode. Keyboard Tab reaches the skip link with a visible outline.
- Previously verified unchanged behavior: OneLink Pay and TuringVault award
  disclosures open and load their evidence.
  Synrail command copying reports success. The demo was rechecked in this revision. Video has native controls and a linked
  text transcript. Playback starts only after the visitor opens the demo. The
  7.88-second recording played to completion, without a media error. Escape closes
  the dialog, pauses playback, and returns focus to the launch link.
- Verified `/synrail.html#run` lands on `/synrail/#run`; home `#demo` lands on
  `/synrail/#demo`, including a same-document hash change.
- The RHOOK conceptual diagram switches with pointer and keyboard input.
  `aria-pressed`, the explanation, and the diagram label follow the chosen state.
  The layout reserves space so switching does not shift surrounding content.
- Public GitHub tree checks confirmed every linked Synrail and RHOOK documentation
  path. Commit sources for updates were checked while writing the content.
- No browser console errors were recorded during the page navigation checks.
- `git diff --check` passes. CSS and JavaScript references include content hashes
  to prevent the old styling or behavior being reused after a rebuild.

Limits: this is browser and static verification, not a full accessibility audit.
Lighthouse and production Core Web Vitals have not been measured. The supported
browser tools in this session do not expose a Lighthouse runner. Visiting external
product screens does not verify wallet/payment flows or current system health.
