# Interactive project desk

29 September 2026. The author chose an interactive portfolio: character through
interface behavior and demonstrations. The home is a compact project workspace,
with Synrail and RHOOK first, followed by the hackathon applications. Case pages
remain documents for deeper reading. Native HTML, CSS, and JavaScript fit the
existing static hosting; there is no external UI kit or new runtime dependency.

Dials: DESIGN_VARIANCE 5, MOTION_INTENSITY 2, VISUAL_DENSITY 6. The important
variation is in how each project can be explored, with a consistent frame and
navigation. Manrope, a small warm accent, and restrained light/dark surfaces keep
the working examples readable.

| Before | After | Why |
| --- | --- | --- |
| Large slogan followed by a long gallery | Compact personal introduction and project selector | Start exploring the work immediately |
| Static previews with similar compositions | Four interactions tied to the projects | Explain something specific about each system |
| Separate large sections for current work | Persistent Synrail and RHOOK navigation, with dated notes inside | Keep continued work visible while exploring |
| Decorative typographic contrast | One sans-serif family with monospace for code and short labels | Let content and behavior define the page |
| A generic concluding contact block | Short colophon and public contact links | Keep the page useful without a sales pitch |

## Interaction and evidence

- Synrail: three stages adapted from the recorded false-green example. The visitor
  can inspect the claim, failed verification, and repair. The original recording
  opens in a native dialog. The walkthrough does not execute commands.
- RHOOK: inspect the historical sequence or the branch after changing X. Node
  buttons and a range control explain the shared context, intervention, and
  downstream recomputation. This is explicitly a conceptual model, with a link to
  the public 50-block example, not the result of executing that example here.
- OneLink Pay: move an amount across the demonstrated 0.10 USDC per-charge limit.
  Passing that single check does not imply the complete payment is authorized.
  The example is local and has no wallet, payment, or network operation.
- TuringVault: inspect the propose/challenge/record workflow alongside the actual
  application screenshot. It is a workflow guide, not fabricated live activity.

Project selection is encoded in the URL. Back, forward, direct links, arrow keys,
Home, and End work with the selector. Outputs use live regions; native buttons,
links, range inputs, details, and the dialog provide the main controls. Without
JavaScript the project descriptions and source links remain in document order,
and the Synrail walkthrough renders all three stages.

A pointer selection changes the project panel with a 160ms opacity/4px transition.
Keyboard input changes state immediately. Reduced motion disables transitions;
there are no looping effects, autoplay, artificial loading, or cursor tricks.
The desktop sidebar becomes a two-column selector on mobile. Application images
keep their original aspect ratios.

Recognition remains a quiet link to precise categories and supporting evidence.
No new personal role, award, usage, financial result, or project-status claims were
introduced. Route slugs, source content, inner pages, and legacy Synrail anchors
remain available. See QA.md for verification scope and limits.
