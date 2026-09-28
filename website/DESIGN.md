# Visual direction

The third preview addresses the author's criticism of both composition and layout.
The staggered gallery and enlarged screenshots made the site look misaligned.
Changing a display font and an accent color had not solved the presentation.

Design read: a personal developer portfolio for people who want to inspect the
work, with an editorial opening and spacious project demonstrations. Native
HTML/CSS remains appropriate for the existing static site. This is a custom design,
not an implementation of an external design system.

Dials: DESIGN_VARIANCE 4, MOTION_INTENSITY 2, VISUAL_DENSITY 4. Consistent alignment
and readable project material take priority over decorative asymmetry.

| Before | After | Why |
| --- | --- | --- |
| Condensed uppercase display type | Manrope hierarchy and a serif italic line in the opening | A quieter personal introduction without making every heading a poster |
| Olive surfaces and bright green | Neutral charcoal/ivory with a restrained warm accent | Let the actual products carry most of the color |
| Two cramped current-project tiles | Full-width studies with text and demonstrations on a shared column grid | Give each ongoing project room to explain its purpose |
| Screenshots wider than their frames | Full images at their native aspect ratio | Keep the application interfaces intact |
| A lowered second gallery card | Equal media widths, aligned headings and metadata | Resolve the specific layout fault in the user's screenshot |
| Large repeated slogan sections | Smaller development notes and background sections | Put the projects ahead of self-description |

Synrail uses the actual recorded demo, now without a crop. It opens in a native
video dialog and links to a transcript. RHOOK remains an explicitly labeled
conceptual model; its switch does not execute a replay. Both have direct source
links next to their case links.

The application gallery uses flex columns to align the metadata even when the
summaries wrap differently. At narrow widths the same content becomes a single
column. No image zoom or translation occurs on hover. Motion is confined to small
link feedback and the RHOOK branch transition; keyboard branch changes are instant
and reduced-motion preferences are respected.

Manrope is self-hosted. The opening italic uses Georgia with a serif fallback.
The shared palette also applies to case pages, the catalog, About, and Updates.
Project facts, route slugs, legacy anchors, and award evidence remain unchanged.

Minimum text-token contrast across the defined page surfaces: 4.88:1 in light mode
and 6.89:1 in dark mode. See QA.md for the scope and limits of verification.
