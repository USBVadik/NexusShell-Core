"""Public editorial content for Second Unit. No private production records or paths."""

TITLE = 'Second Unit'
SUMMARY = 'An agentic film crew, from brief to final cut.'
DESCRIPTION = ('Plan shots, review takes, assemble the edit, and carry what worked '
               'into the next film. You approve the creative decisions along the way.')

AUTHOR_NAME = 'Vadik'
AUTHOR_ROLE = 'Creator of Second Unit'
AUTHOR_CONTACTS = [
    ('GitHub', 'https://github.com/USBVadik'),
    ('X', 'https://x.com/a_seven_life'),
    ('Alternate email', 'mailto:applevadik@gmail.com'),
]
AUTHOR_WORK_CONTACT = 'mailto:vadik@nexusshell.dev'

BABELSBERG_TRACK = (
    'I’m preparing for the Studio Babelsberg track because its focus on physical '
    'contact, stable backgrounds and character continuity matches the checks '
    'I use to review shots.'
)

BABELSBERG_CHECKS = [
    {
        'problem': 'Floating actors',
        'check': 'Check where feet meet the support surface and whether the contact shadow holds through the motion.',
        'example': 'A mascot take was rejected because its feet never met the tabletop, even though the movement looked plausible.',
        'link': ('Read the physical-contact breakdown', '#physical-contact'),
    },
    {
        'problem': 'Stuttering backgrounds',
        'check': 'Anchor each location to the shot’s camera position and tilt. Review vertical lines and fixed landmarks through the take.',
        'example': 'A loft reference taken straight on made a tilted shot look wrong. The next pass used a location reference from the same angle as the shot.',
    },
    {
        'problem': 'Characters that change between shots',
        'check': 'Build each shot from the same read-only character master. Review defining traits against the character canon.',
        'example': 'In Lawn Wars, look for the rider’s moustache and sunglasses in a close-up and a wider shot.',
        'frames': [
            ('lawn-continuity-close.jpg', '00:12 · Close-up', 'Close-up of the rider in sunglasses with a horseshoe moustache.'),
            ('lawn-continuity-wide.jpg', '01:00 · Wide shot', 'The same rider in sunglasses and a blue shirt on his red mower.'),
        ],
    },
]

# Add the approved first and revised frames here when they are supplied.
# Each frame has src, alt, width, and height.
PHYSICAL_CONTACT_FRAMES = {}
PHYSICAL_CONTACT_STATES = [
    ('before', 'Before · First take', 'The mascot’s feet hang in the air above the table.'),
    ('after', 'After · Revised take', 'Both feet rest on the tabletop and cast a contact shadow.'),
]

# Snapshot from the Numbers section of PRODUCT_PAGE_EN.md.
PRODUCTION_NUMBERS = [
    ('67', 'Recorded failures', 'Across 6 projects and 28 symptom types.'),
    ('44', 'Numbered review checks', 'Plus a separate axis check.'),
    ('23', 'A/B taste pairs', 'Side-by-side examples used to calibrate reviews.'),
    ('1,451', 'Verified generations', '1,005 images, 295 Omni videos and 151 Veo videos.'),
]
REGISTRY_DETAILS = [
    ('Planned jobs', '2,064'),
    ('Shot IDs', '341'),
    ('Safety blocks', '52 recorded, with none resubmitted'),
    ('Failures found', '41 by the author and 26 by agents'),
    ('Fix outcomes', '46 worked, 13 partly worked, 5 failed, 3 untested'),
    ('Golden references', '20 shots plus one meme remake'),
    ('Reference library for analysis', '218 film frames, 86 AI-creator works and 13 reels'),
    ('Automated tests', '556'),
    ('Lawn Wars cost per finished second', 'About $1.90, registry estimate'),
]

# Add only films selected by the author for this page. Required public fields:
# id, title, src, poster, preview, width, height, duration, caption, audio.
# Media files must be website derivatives, never originals or private references.
# Author-selected website derivatives, inspected before publication.
SELECTED_FILMS = [
    {
        'id': 'lawn', 'title': 'Lawn Wars, pt. 1',
        'src': '/assets/media/second-unit/lawn-wars.mp4',
        'poster': '/assets/media/second-unit/lawn-poster.jpg',
        'preview': '/assets/media/second-unit/lawn-preview.mp4',
        'width': 720, 'height': 1280, 'duration': '1:06',
        'audio': 'Generation audio · no music',
        'caption': 'Two suburban dads turn a 7 a.m. lawn-mowing dispute into a race. A 69-shot comedy built with staged coverage, a versioned edit and a reviewed grade.',
    },
    {
        'id': 'gravity', 'title': 'Gravity turns off on Tuesdays',
        'src': '/assets/media/second-unit/gravity-tuesdays.mp4',
        'poster': '/assets/media/second-unit/gravity-poster.jpg',
        'preview': '/assets/media/second-unit/gravity-preview.mp4',
        'width': 1280, 'height': 720, 'duration': '0:28',
        'audio': 'Silent version',
        'caption': 'A deadpan comedy built around one world rule. The parody news intro uses a fictional presenter to announce that gravity has been switched off in California.',
        'stills': [
            {'src': '/assets/media/second-unit/gravity-frame-1.jpg', 'alt': 'A fictional news presenter introduces a gravity outage in California.'},
            {'src': '/assets/media/second-unit/gravity-frame-2.jpg', 'alt': 'A woman reaches for a floating takeaway cup beside a tilting bus.'},
            {'src': '/assets/media/second-unit/gravity-frame-3.jpg', 'alt': 'A tethered reporter and camera operator hover above the pavement.'},
            {'src': '/assets/media/second-unit/gravity-frame-4.jpg', 'alt': 'A woman in pink checks her wrist beside a white picket fence.'},
        ],
        'sheet': '/assets/media/second-unit/gravity-shot-sheet.jpg',
    },
]

FILMS = SELECTED_FILMS

STUDY_MEDIA = {
    'colour': '/assets/media/second-unit/colour-passes.jpg',
    'upscale_video': '/assets/media/second-unit/upscale-study.mp4',
    'upscale_poster': '/assets/media/second-unit/upscale-poster.jpg',
    'upscale_crops': '/assets/media/second-unit/upscale-crops.jpg',
}

STAGES = [
    {
        'id': 'prepare', 'name': 'Prepare', 'title': 'Give the film a direction.',
        'body': 'Start with the brief, budget and acceptance criteria. Analyse references for composition, light, colour and rhythm, then turn those observations into a story and a shot plan.',
        'input': 'Brief, constraints, budget', 'output': 'Measured refboard and story beats',
        'check': 'Does each shot have a purpose, a clear action and a place in the story?',
        'human': 'Approve the direction and story.',
    },
    {
        'id': 'establish', 'name': 'Establish', 'title': 'Keep a shared picture of the scene.',
        'body': 'Approve character and location masters. Record the features that must remain consistent, the action axis, light direction and prop states. Each new shot starts from its master.',
        'input': 'Approved story and references', 'output': 'Character masters, canon and scene map',
        'check': 'Character features, screen direction, light and prop scale stay consistent.',
        'human': 'Approve the masters and keyframes.',
    },
    {
        'id': 'generate', 'name': 'Generate', 'title': 'Explore in drafts. Keep the accepted take.',
        'body': 'Build keyframes with a declared camera, subject, action and change over time. Explore motion in inexpensive drafts. Keep accepted takes as source files for the final edit and upscale.',
        'input': 'Approved keyframe and job specification', 'output': 'Motion drafts and contact sheets',
        'check': 'Inspect the usable window, physical contact, faces, hands and movement.',
        'human': 'Choose the take that belongs in the cut.',
    },
    {
        'id': 'review', 'name': 'Review', 'title': 'Judge the shot inside the film.',
        'body': 'Inspect contact sheets and details, then watch shots inside the cut. Separate reviewer agents check framing and physical contact, continuity and motivation, and colour across the sequence.',
        'input': 'Draft takes, scene map and director’s notes', 'output': 'Timecoded findings and a revised cut',
        'check': 'A plausible frame can still fail in motion or at the next cut.',
        'human': 'Accept, redirect or request another pass.',
    },
    {
        'id': 'finish', 'name': 'Finish', 'title': 'Finish the version you approved.',
        'body': 'Assemble the edit with versioned scripts. Match colour outliers, apply the look, and add grain at delivery size. Check the exported file and keep a no-music version where required.',
        'input': 'Approved cut and accepted source takes', 'output': 'Delivery master and rebuild records',
        'check': 'Review the whole sequence, export metadata and delivery format.',
        'human': 'Sign off on the cut, look and delivery.',
    },
    {
        'id': 'carry-forward', 'name': 'Carry forward', 'title': 'Make the next film start with more context.',
        'body': 'Record rejected takes, the reason, the proposed fix and whether it worked. Accepted references and A/B preferences become material for the next review. Proven fixes move into the shared rules.',
        'input': 'Failures, accepted shots and A/B preferences', 'output': 'Relevant fixes, review rules and regression references',
        'check': 'A correction keeps its outcome and the feedback that caused it.',
        'human': 'Set the taste through concrete verdicts.',
    },
]

REVIEWERS = [
    ('Cinematography', 'DP / takes',
     'Does the frame hold up?',
     'Perspective, light, depth, character features, contact with the ground, hands and prop scale. A shot can be rejected, returned for another take, or passed to the director.'),
    ('Editing', 'ED',
     'Does one shot lead to the next?',
     'What motivates an action, what causes the next event, and whether continuity survives the cut. The director’s notes are tracked against timecodes.'),
    ('Colour', 'CO',
     'Does the sequence belong together?',
     'Match before applying the look. Inspect skin and the full sequence as well as individual cuts. Numeric comparisons support the review; the director decides whether the film looks right.'),
]

MEMORY = [
    ('Record', 'The rejected take, symptom and exact feedback.'),
    ('Try', 'A proposed correction, with its outcome kept alongside it.'),
    ('Promote', 'Proven fixes become shared rules with a recorded reason.'),
    ('Retrieve', 'Relevant fixes and accepted examples inform the next job.'),
]

CRAFT_NOTE = 'The models are not fine-tuned on the reference library. Craft knowledge is recorded as rules, checklists and measured observations used around the models.'
CASE = {
    'title': 'Lawn Wars',
    'intro': 'A correction from Lawn Wars, a comedy about two suburban dads racing ride-on mowers at 7 a.m.',
    'version': 'Colour / r6 → r6b',
    'paragraphs': [
        'The r6 cut met the local colour-difference targets, yet the sequence drifted between warm and cool shots. A second pass pulled the whole cut toward one target.',
        'The author rejected it: the image had become cold and the greens had lost separation. A warmer uniform pass was rejected too. The final returned to the earlier grade.',
    ],
    'rule_lines': ['Match the outliers.', 'Review the whole film.'],
    'rule': 'Correct outliers selectively and inspect the full sequence as a contact sheet before chasing a single target. A good measurement still needs a creative verdict.',
}
MEMORY_NOTE = 'Accepted shots form regression references; recorded A/B preferences help calibrate reviewers. This loop updates instructions and review material, not the weights of the generation models.'
RECORDS = {
    'intro': 'A film is a set of decisions and source files that should survive the session that made it.',
    'before': [
        'Declare the model, inputs, estimated cost and remaining budget. The runner checks spending caps and request fingerprints before submission.',
        'Vendor safety refusals are recorded as terminal outcomes, separately from quota errors, invalid requests and other API failures.',
    ],
    'after': ['Source take and checksum', 'Job specification and generation record',
              'Versioned edit and grade scripts', 'Review findings and export metadata'],
    'conclusion': 'Rebuild the final from the accepted files.',
}
ENGINES_INTRO = 'The generation layer uses model adapters. Planning, review and post-production sit around it.'
ADAPTERS = [
    ('Image generation', 'Gemini image models', 'In use'),
    ('Motion generation', 'Omni / Veo', 'In use'),
    ('Masters & keyframes', 'FLUX adapter', 'Planned'),
]
FLUX_PLAN = 'The planned first step is a FLUX adapter for character masters and keyframes, followed by a comparison on the same approved references with the same reviewers and budget limits. A competition entry would need to use FLUX for all image and video generation, following the programme rules.'
