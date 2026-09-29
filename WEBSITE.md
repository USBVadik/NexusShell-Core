# NexusShell website

The website is plain HTML served from the root of `main` by GitHub Pages.
The domain remains `nexusshell.dev`; `CNAME` and the existing hosting setup are preserved.

## Edit and preview

Use Python 3.11 or newer. No packages are required.

```sh
python3 website/build.py
python3 -m http.server 4173 --bind 127.0.0.1
```

Open `http://127.0.0.1:4173/`. Stop the server with Ctrl+C.

- `website/content.py`: project descriptions, source links, and dated updates.
- `website/build.py`: shared layouts, navigation, About, and Synrail product copy.
- `website/desk.py`: the interactive home and its project-specific walkthroughs.
- `assets/desk.css` and `assets/desk.js`: home styles and interaction state.
- `assets/site.css`: shared styles and light/dark themes.
- `assets/site.js`: appearance preference, command copying, the demo dialog,
  and old home anchors (plus the earlier replay switch retained for compatibility).
- `assets/media/`: actual application screenshots, the Synrail demo, and award evidence.

Run the build after editing content or shared assets. It adds content hashes to CSS
and JavaScript URLs so an earlier cached version does not survive a deployment.
Commit the generated HTML and sitemap with the source changes. GitHub Pages does
not run the Python builder. No npm or backend is needed to serve the site.

## Content direction

Current work comes first: Synrail and RHOOK. Updates describe specific changes and
link to dated commits. New updates are curated, not automatically inferred from
commit volume. Add them to the top of `UPDATES`, with the source date and URL.

OneLink Pay and TuringVault remain accessible as hackathon applications. Awards
belong inside their cases, with the precise category and supporting source. Avoid
implying an overall hackathon win, production certification, a team size, a client
relationship, or personal responsibilities that have not been confirmed.

The site is in English. Public identity is Vadik / USBVadik. Contact links use the
existing public GitHub and X profiles; no hiring availability or email is invented.

## Routes

`/`, `/projects/`, four main project cases, `/projects/agent-automation/`, `/about/`,
`/updates/`, and `/synrail/`. `404.html` provides a recovery page.

`/synrail.html` redirects to `/synrail/` and preserves its hash with JavaScript.
Old home anchors `#demo`, `#run`, `#why`, and `#use` lead to the corresponding Synrail
sections. The home also retains `#top`, `#technology`, `#transparency`, and `#contact`.

## Assets and sources

- Manrope is self-hosted under the SIL Open Font License in `assets/fonts/OFL-Manrope.txt`.
- Barlow Condensed files remain from the earlier preview but are no longer loaded.
- Synrail recording and poster: the public `USBVadik/synrail` false-green demo.
- OneLink Pay screenshot: `https://onelink-pay.vercel.app/`, captured 28 September 2026.
- TuringVault console screenshot: `https://turingvault.dev/`, captured 29 September 2026.
  The frame contains the agent console and signal map; navigation and wallet controls are outside it.
- RHOOK visual: an explanatory replay diagram, not measured performance.
- UXmaxx certificate and Mantle Demo Day programme: supplied by the author.
- Award categories and development notes: URLs are stored with their entries in
  `website/content.py`. The Mantle project-specific award note is the author's
  post; the Demo Day image independently shows participation, not the award.
- `nexusshell-preview.jpg`: a screenshot of this site for link previews.

The visual direction and interaction decisions are recorded in `website/DESIGN.md`.
The home keeps all four project panels in HTML. JavaScript selects the panel from
its URL hash and enables the walkthroughs; without it, project content remains in
document order. Synrail uses a recorded example, RHOOK a conceptual replay model,
OneLink Pay a local calculation of one permission limit, and TuringVault a workflow
guide. None connects a wallet or runs the underlying product. The Synrail recording
opens in a native dialog; without JavaScript its link opens the product page.

When adding a project, update `PROJECTS` and the home panel/selector in
`website/desk.py` together. The four walkthroughs are intentionally specific to
the existing projects, rather than automatically generated from marketing copy.
Keep labels explicit about whether an example is recorded, conceptual, or live.

## Review and publication

Before publication, rebuild and check internal links, image loading, metadata,
mobile layouts, keyboard focus, both themes, and old Synrail URLs. Check the public
source links when changing claims. Keep the public app screenshots dated; they are
not live health indicators. A local preview cannot establish production speed.

Merging into `main` updates the public site through the existing GitHub Pages
deployment. Keep draft changes on a branch until the preview has been reviewed.
For rollback, revert the website commit and let Pages redeploy.
