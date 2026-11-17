# Second Unit draft verification

17 November 2026. Local draft only. Selected films have not yet been supplied.

- The static build emits 11 content pages, the 404, and legacy Synrail redirect.
- Link audit: 13 HTML files, 205 local references; no missing targets, fragments,
  duplicate IDs or missing image dimensions/alt text. Content pages have one H1.
- Python modules compile; the new JavaScript passes Node syntax checking.
- All six stages exercised with pointer input; exactly one frame is visible.
  At the initial desktop size the process height stays 519.6px across stages.
  Home and arrow keys move selection and focus together.
- All stages checked at 320px with no horizontal overflow. The home deep link
  selects Second Unit; switching away and browser Back restore it.
- Product page visually inspected at 320, 768 and 1280px, in light and dark themes.
  Native reviewer disclosures opened by pointer and keyboard.
- Script-free rendering checked at 320px: all six named stages remain readable,
  controls remain hidden, and there is no horizontal overflow. Temporary file removed.
- Empty film list produces no film section, players or link to a missing film section.
- Second Unit uses a neutral product footer and its own screenshot for social previews.
- Independent review identified four issues: fallback stage names, product attribution
  in shared chrome/preview, editorial copy embedded in markup, and internal notes in
  the publishable checkout. Each was addressed. Detailed handoff notes stay outside
  the repository; its design document contains only release-safe material.
- Generated page inspected for placeholder product names and private local paths.
  No media from the production workspace was copied. FLUX is labeled planned.
- Browser error log was empty during product-page navigation and interaction.

Limits: no generated video is running on this website. The source workflow,
generation providers, budget enforcement and aggregate counts were not audited.
Film playback and poster loading require another check after selected media is added.
This is not a full accessibility or performance audit.

## Creative polish, 17 November

- Inspected the new framing graphic in dark desktop and light mobile layouts.
  Decorative geometry is aria-hidden, and the original text remains readable.
- Rechecked all six pointer selections: one visible stage, stable 519.6px process
  height at 1280px, no horizontal overflow. Keyboard Home updates selection and
  focus immediately with the input mode marked as keyboard.
- Independent review found the animation cancellation path assumed getAnimations.
  A local compatibility page reproduced the failure with getAnimations and animate
  unavailable, then passed after tracking only the owned animation handle.
  The temporary compatibility page was removed.
- The hero and framing illustration fit 320px and 768px without overflow. The memory line
  becomes a two-column layout on narrow screens.
- No films or private production assets were added during this presentation pass.

## Selected media release, 17 November

The owner supplied and explicitly authorized publication of eight selected media
files. Public derivatives add two complete films, two silent six-second previews,
a silent upscale study, three original comparison/contact sheets, three posters
and four extracted frames. Lawn Wars retains generated sound without commercial
music. Gravity is silent and its fictional news intro is labeled as parody.

- ffprobe confirmed dimensions, codecs, durations and audio streams for all inputs.
  All five public MP4 files decode fully with ffmpeg -xerror. Their moov atoms
  precede mdat for progressive playback. Supplied sheets are byte-identical.
- Static audit: 13 HTML files, 233 local references, no missing files or fragments.
  Video/image dimensions and alternatives are present. Full films and the study
  use native controls and preload=none. Hero sources are attached when visible.
- Preview behavior exercised against the actual script in a focused Node harness:
  deferred source attachment, play/pause, latest observer sample, hidden document,
  reduced motion, no IntersectionObserver, and rejected autoplay all passed.
- Independent review found the finishing-grid auto minimum, generic still alt text,
  stale observer-sample choice and outdated contributor fields. Corrected all four.
- Comparison captions distinguish r6/r7/r7b colour passes from the selected final
  and mark the upscale A/B as an experiment with no final method selected.
- The product social preview now uses a real frame from the Gravity film.

Current limitation: browser access is unavailable in this chat. The new media
layout has not been visually rechecked in a browser, and native browser playback
is not claimed as tested in this release. Codec/decode, script behavior and
production HTTP checks provide the verification available in this environment.
