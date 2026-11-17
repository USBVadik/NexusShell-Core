"""Public editorial content for Second Unit. No private production records or paths."""

TITLE = 'Second Unit'
SUMMARY = 'An agentic film crew, from brief to final cut.'
DESCRIPTION = ('Plan shots, review takes, assemble the edit, and carry what worked '
               'into the next film. You approve the creative decisions along the way.')

# Add only films selected by the author for this page. Public fields:
# title, src, poster, width, height, duration, caption, audio.
# Media files must be website derivatives, never originals or private references.
FILMS = []

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
CLOSING = ['Built as a working production environment.',
           'Developed through films, revisions and recorded feedback.']
