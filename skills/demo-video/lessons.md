# What the review rounds taught us

Apply these from the first cut. Each came from a reviewer's comment on a real video.

## Words

- **No self-promotion.** Never call the tool great, powerful, loved or time-saving. Say what it
  does and let the footage show it.
- **Tell it from the user's side**: "A translator can ask…", "If the team prefers to talk…". Use
  "you" sparingly, don't repeat the same noun in every line, and don't ask rhetorical questions.
- **Results are prompts, not verdicts.** For checking tools, the narration says where to look and
  what a person might ask, never that the tool decides.
- **Don't oversell the audience either.** Name everyone who uses it (translators, community
  reviewers, church leaders, outside experts), not only the most senior role.
- **Name things exactly** as the UI and the data do. Check every feature, resource and product name
  against the code or the screen; don't guess.
- **Don't show an example that could look like the tool's mistake.** A correct finding that a
  viewer might read as wrong (or that the reviewer isn't sure about) costs more than it shows.
  Pick an example that is plainly right.
- **Keep what can't be said safely out.** Don't name a community or language if that could expose
  it; "a language of Tanzania" is enough. Quotes from users are anonymous unless they agreed.
- **Pronunciation.** Listen to every line. Spell acronyms in `say` only when needed ("S I L" yes;
  "A I" left a gap, "AI" was fine). Watch for words the voice merges or splits ("any one" vs
  "anyone", possessives).
- **The close:** one credit line and one call to action with a URL (and a QR code). A wrap-up line
  before it should say what the tool changes for people in plain words, not a slogan.

## Pictures

- **Open with the need** (photos of real-looking people at work), then the product.
- **Show, don't sit.** Don't hold a static screen (a summary, a list) for more than about 5 s:
  open an item, expand a section, click the explainer the narration mentions.
- **Remove distractions.** Tooltips, hover states, focus rings, banners ("not available"), stale
  answers, and anything flashing draw the eye away from what's narrated. Re-take rather than crop
  around them.
- **Footage under its narration.** Keep each picture under the words that describe it. Slow a
  segment down rather than freeze on its last frame; speed waits up (`flex`) rather than cutting
  them out abruptly.
- **Zooms.** Push straight in on one point. Never zoom while the page scrolls (it wobbles). Hold a
  zoom through a click, then ease out. Carry a zoom across segments with `in: false` / `out: false`
  rather than zooming out and in again.
- **Overlays** fade in as their name is spoken and stay up long enough to read.
- **Scrolling** slow enough to read, or not at all.

## Pacing

- No silent gap over about 0.7 s inside a section, a short pause before a new one.
- Trim transitions: a dismissed or "after" state needs about a second, not three.
- At 2:30–3:00, every beat earns its seconds. Cut a feature rather than rushing all of them.

## Process

- Draft voice (Kokoro) for every review round; pay for the real voice once the words are settled,
  and then only for lines that change.
- Version notes say what changed for each comment, so the reviewer can check quickly.
- Log decisions in `PLAN.md`, so a later round doesn't undo an earlier one.
- Leave the product as you found it: undo dismissals and test entries off camera, don't spend a
  team's run quotas, and say what you changed.
