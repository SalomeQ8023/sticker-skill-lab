---
name: naive-crayon-sticker-set
description: Turn one user-provided person or pet photo into a warm, naive-crayon 3+7 transparent journaling sticker set. Use for a person or pet as the intended subject, not an object-only photo, product photo, food, place, or finished journal page.
---

# Naive Crayon Sticker Set

Create a reusable sticker set from one photo: `3` subject-led main elements and `7` related journaling elements.

Read [the style card](references/style-card.md) before generation. This candidate also bundles the author-owned `assets/pet-style-reference.png` to communicate style, material, character simplification, playfulness, and finish quality for both person and pet inputs.

The user's photo is the only identity and factual-content source. Related elements may extend from visible anchors into generic, non-factual, non-sensitive mood, scene, or page-use ideas. Do not imply a profession, relationship, health condition, identity, or specific lifestyle unless it is visibly supported or the user provides it. The bundled reference is a style-and-quality source only: do not copy its pet identity, pose, composition, props, text, background, or exact palette.

Only process photos the user owns or has permission to use. Do not recreate known characters, logos, or imitate a named artist.

## Input scope

Inspect the uploaded image before planning or generation.

- Proceed when exactly one person or one pet is visibly the intended primary subject. Objects held, worn, or used by that subject may inform the seven related elements.
- If multiple people, multiple pets, or both a person and pet could be the primary subject, ask the user to choose one and provide a crop or a new image centered on that subject. Do not select one silently.
- If the image is readable but its intended primary subject is not a person or pet, identify it only at a confident broad level, explain that this skill currently supports person or pet photos, and stop without generating. Do not force an object-only input into the pet or person workflow.
- If the file cannot be read or the intended subject cannot be judged reliably because it is too unclear, obstructed, or ambiguous, ask for a clearer image or a short clarification. Do not guess.

## Produce

1. Inspect the photo for a few visible identity anchors. Do not invent unseen high-identity details; when facial features are obscured, the style's low-information facial grammar may complete the character.
   For a person, keep the person section's construction guidance and full avoid-list in the generation prompt. Build a simplified sticker character before restoring identity anchors; do not trace a realistic portrait and merely cover it with crayon texture.
   For a pet, keep the pet section's construction guidance and full avoid-list in the generation prompt. Do not reduce them to generic “naive crayon” wording.
2. Give the set one coherent page story or use case before choosing its elements. Keep it simple and let it guide the set rather than forcing a literal scene. Plan three main elements as complete sticker compositions. They may vary through scene relationship, props, ground, or page role when useful; do not default to full-body, half-body, and bust crops. Natural repetition remains allowed when it better preserves identity and comfortable anatomy. Do not fill a fixed seven-slot template or force pose differences. For a pet, when the source permits natural variation, make the intended behavior or silhouette change explicit; changing only the mat, ledge, or other support while keeping the same head, body arrangement, and expression does not create a new main moment.
   Before generation, make an internal ten-item manifest. For each `M01`–`M03` and `A01`–`A07`, record its content, page function, relative visual weight (`light`, `medium`, or `heavy`), intended use, and whether it receives an outer sticker cutline. Review the seven related elements as one designed set: they may draw freely from direct anchors, scene semantics, generic non-factual context, page tools, mood, and decoration. Do not require every item to be visibly present in the photo, set a source quota, turn the set into a literal inventory, or repeat one source or theme across all seven. Seek useful variation in color, scale, silhouette, and composition. A shared-base or shared-cutline mini-cluster may be one logical element when its parts form one usable design. Use the style card's function vocabulary. Reject and revise the plan when all three main elements have the same visual weight, when all seven related elements are light micro-decorations, or when a medium/heavy related element is only an undesigned blank shape. At least one related element must have medium or heavy visual weight and serve a non-micro page function. Each manifest row must produce exactly one connected sticker silhouette or one visibly shared-base or shared-cutline cluster. Do not combine separate objects that would receive separate cutlines unless the design visibly joins them. These are relational composition rules, not printer dimensions or fixed pixel quotas.
3. Submit the user's photo and `assets/pet-style-reference.png` in the same image-generation request, assigning their roles explicitly. Include the ten-item manifest in the request so relative weight and cutline decisions survive generation. Use flat opaque `#FF00FF` as the extraction background and exclude magenta from the artwork palette. Generate one landscape source board with exactly ten visibly separated logical elements on that solid color. Actual painted shapes and any outer sticker cutlines must not touch; their axis-aligned bounding rectangles may cross when long or diagonal elements remain visibly separate. Prefer one generation; repair deterministic file problems locally and ask before aesthetic regeneration.
4. Deliver:
   - a clean preview;
   - one transparent master board;
   - `elements/M01.png`–`M03.png` and `elements/A01.png`–`A07.png`.

Keep every element complete, non-overlapping, and separated by enough empty space for independent cropping. A decoration cluster may be one logical element when its parts belong together.

## Transparency and splitting

For both a true-Alpha source and an opaque RGB source on the declared solid extraction color, create a `boxes.json` containing ten crop boxes in source-pixel coordinates, then run the script. Each box must fully contain its target with transparent margin. Boxes may overlap when two visibly separate elements have crossing axis-aligned bounds: the script discards neighboring visible components that enter from a crop edge. It preserves existing Alpha; for an opaque source it removes only the explicitly supplied background color. If the model returns a baked checkerboard or another undeclared background, stop instead of guessing.

Requires Python 3 with Pillow and NumPy already available. In Codex desktop, call `load_workspace_dependencies` first and use the bundled Python path it returns when that interpreter provides both libraries; do not assume the system `python3` is the workspace interpreter. If no compatible interpreter is available, stop and tell the user; do not install dependencies without permission.

```bash
/absolute/path/to/python-with-pillow-and-numpy scripts/prepare_sticker_set.py \
  --source /absolute/path/to/source.png \
  --boxes /absolute/path/to/boxes.json \
  --output /absolute/path/to/output \
  --diagnostics-dir /absolute/path/to/private-diagnostics \
  --background-color "#FF00FF"
```

`boxes.json` is a list such as:

```json
[
  {"id": "M01", "box": [40, 40, 430, 460]},
  {"id": "A07", "box": [470, 40, 860, 460]}
]
```

Include all ten IDs exactly once. Keep `boxes.json` outside the delivery directory. Adjust boxes when the script reports that a crop cuts visible pixels; do not erase artwork to force a pass. Omit `--background-color` only when the source already has meaningful Alpha.

Keep the diagnostics directory outside the delivery directory. After processing, inspect its `background-check.png` on both light and dark backgrounds. Stop instead of delivering when any element is missing visible content or retains detached fragments. Do not link or return the diagnostics directory.

## Acceptance before delivery

Record technical and visual verdicts separately. A valid Alpha channel, ten files, and clean crops prove only technical integrity; they do not prove that the sticker set is acceptable.

Before calling the set successful, inspect the preview and the light/dark background check against the style card and selected style reference. Judge shared visual grammar and quality, not literal similarity to the reference subject or layout. Stop and report a visual failure when any of these is true:

- the subject loses readable body, face, or identity anchors on an ordinary light background;
- faceted mosaic, low-poly, photographic, or other rendering artifacts replace the intended rough crayon marks;
- a person remains an overall detailed crayon portrait, with realistic face modeling or accumulated hair, clothing, anatomy, and footwear detail replacing the intended low-information rounded character; isolated readable garment or footwear details are not a failure when the overall character remains rounded and low-information;
- the three main elements are too weak or repetitive to function as three usable subject stickers;
- a pet set changes only supports or props while the head, body arrangement, and expression remain template-identical across all three main elements;
- a pet's two eyes do not follow one coherent gaze target, unless that asymmetry is visibly present in the source photo;
- the three main elements are mechanically equal in visual weight instead of offering at least two readable weight levels; size is one signal, not the only one;
- the related elements satisfy the count but are mostly empty, illegible, uniformly tiny, or not useful as journaling material;
- the related elements form a literal inventory or repeat one source or theme, instead of a varied, complementary mix of contextual, page-use, mood, and decorative material;
- cuttable stickers are missing their warm white/cream outer cutline, or page-integrating textures, partitions, and connectors have been incorrectly enclosed by one.
- the board contains more or fewer than ten visible logical elements; any isolated object with its own cutline counts as another element even when the manifest called it part of a cluster.

Any visual failure makes the overall set fail even when technical checks pass. Do not silently regenerate: show the failed preview, state the separate verdicts, and ask before an aesthetic rerun.

## User-facing response

Show the preview and link the transparent master and elements directory. State once that the set contains AI-assisted generated content. Do not expose the ten-item manifest, `background-check.png`, internal diagnostic labels, prompts, crop coordinates, or run reports unless the user asks. After the deliverables, add this attribution once: `本工作流由作者“球是发散家”提供。`

Do not put watermarks, account handles, or advertising inside generated images, and do not add promotional copy beyond the single attribution above. Do not add printer-specific sizing or B7 QA artifacts. Do not claim exact likeness or pixel-perfect preservation. Treat the user's natural-language aesthetic judgment as the gate for any aesthetic rerun.
