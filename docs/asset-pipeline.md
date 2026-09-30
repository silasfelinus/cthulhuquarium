# Asset pipeline — what actually works

date: 2026-08-24
source: cthulhuquarium/t-005, measured rather than assumed

---

## The working recipe

```yaml
# projects/art-generate.yaml in the conductor repo
batch:
  entries:
    - project: cthulhuquarium
      engine: flux
      flux_variant: schnell
      size: 1024x1024
      image_path: projects/process/cthulhuquarium-fish-<slug>.webp
      prompt: >-
        <the species' art_prompt from its fish/<slug>.yaml>
```

Then, from the conductor repo:

```bash
python scripts/consume_art_queue_core.py --live --limit 1 --timeout 480
python scripts/distribute_images.py --dry-run
```

The consumer POSTs to `https://kindrobots.org/api/art/queue`, the home-box relay renders,
and the result lands in `projects/process/`. Auth is `KR_API_TOKEN` from the environment —
the same token `fetch_todos.py` uses. Nothing else needs configuring.

**Confirmed working end to end on 2026-08-24**: job 9184, ArtImage 18439, the Lamplight
Angler. Roughly 4–7 minutes wall clock for one 1024×1024 image, which is why `--timeout`
wants to be generous.

## Engines: one of three works

Measured the same day, same prompt, same size, one entry each:

| Engine | Result |
|---|---|
| `flux` (`flux_variant: schnell`) | **Works.** Job 9184 rendered and downloaded cleanly. |
| `krea2` | **Fails.** Job 9179: `node 3 (CLIPTextEncode): hostbuf_file_reader_read failed` — the model is present enough to select but cannot be read. Reads like corruption or a partial download. |
| `flux2-klein` | **Fails fast.** Job 9181: `ComfyUI has no matching file for CLIPLoader.clip_name='flux2_klein_text_encoder_fp8_scaled.safetensors'`. Simply not installed. |

**`krea2` is the repo-wide default and it is the broken one.** Anything queued without an
explicit `engine:` will fail until the box is fixed. Set `engine: flux` explicitly on every
Cthulhuquarium entry until conductor/cthulhuquarium t-033 is resolved.

Worth knowing: jobs 9177, 9178, 9180, 9182 and 9183 — none of them ours — were also
`FAILED` in the same window. The box is failing broadly, not just for our engine choices.

## The important finding: hero prompts make illegible sprites

The first render came back beautiful and **unusable in the tank**.

The Lamplight Angler's `art_prompt` is written for atmosphere — *"hanging motionless in
black water... thick particulate water fading to black"* — and flux honoured it exactly. The
result is a near-black frame with a glowing green lure and a lit jaw. As a bestiary card or
a hero image it is the best thing this project has produced. As a fish swimming at 60–120px
in a tank, it is a few green pixels.

**Two prompt registers are needed, and the bible currently only has one.**

| Use | Needs |
|---|---|
| **Card / hero / bestiary** | Atmosphere. Subject small in frame, heavy negative space, light used sparingly. The current prompts are already right for this. |
| **In-tank sprite** | Legibility. Subject *fills the frame*, strong rim light along the whole silhouette, minimal background, no fade-to-black, and enough interior value that the shape survives being scaled to 15% and composited over dark water. |

The existing `art_prompt` field should be understood as the **card** prompt. Sprites need
either a second field or a documented transform applied at queue time — that decision belongs
to whoever picks up the full art pass.

This does not invalidate the silhouette-forward direction. It confirms it: the silhouette
generated cleanly and consistently on the first try, with no anatomy artefacts and no
misread of the concept. It just needs to be lit *for the size it will be seen at*.

## Costs and metadata

- One 1024×1024 image: ~4–7 minutes on the home box, no per-image monetary cost.
- The consumer records `resolvedSeed` on every job, so any image can be regenerated.
- Results land as `ArtImage` rows in Kind Robots (18439 here) and as files in
  `projects/process/`, routed onward by `distribute_images.py`.
- Generated art is covered by the standing 2026-07-06 rule — no per-image approval needed.

---

## Sprites, story art and backgrounds (2026-09-30)

Silas: *"cthulhuquarium deserves a real roster of fish, with animation, and invisible
background... custom, bespoke listings, static image and then animated."* The card
register above stays the card. The tank gets its own:

| Step | Command | Output |
|---|---|---|
| 1. Author | `sprite:` block per species (`fish/SCHEMA.md` "Sprites"), `characters/*.yaml`, `backgrounds/backgrounds.yaml`, `story/plates.yaml` | the canon |
| 2. Render | `python3 scripts/render_art.py --list`, then `python3 scripts/render_art.py all --par 3` | `*/raw/*.png`, resumable: an existing raw is skipped, delete one to redo it |
| 3. Cut out + animate | `python3 scripts/build_sprites.py` | `sprites/<slug>.webp` (transparent, 320px) and `sprites/anim/<slug>.webp` (looping preview) |
| 4. Story art | `python3 scripts/build_story_art.py` | cut-out portraits, hero plates, 1280px backgrounds and scene plates |
| 5. Deliver | in kind_robots: `node scripts/sync_cthulhuquarium_canon.mjs ../cthulhuquarium` | bundled assets + `utils/cthulhuquariumCanon.generated.ts` |

**Why cut out locally rather than ask the model for transparency.** A diffusion model
asked for "transparent" paints a checkerboard (conductor's
`build_ruler_hooked_art_queue.py` found this first). Every sprite prompt instead ends on
a named flat studio backdrop, and `rembg`'s `isnet-general-use` model removes it. Pale
grey for dark or saturated creatures, charcoal for pale, glassy and glowing ones. The
scraperboard plate is black-bodied, so it always takes pale grey.

**Why the animation is maths, not frames.** Each species declares a `sprite.motion`
(`tailbeat`, `undulate`, `ripple`, `pulse`, `sway`, `breathe`, `rigid`). The deformation
is a strip-wise travelling wave defined once in `build_sprites.py` (`MOTIONS`, `deform`)
and mirrored number-for-number in kind_robots `utils/cthulhuquariumSprites.ts`. The game
ships only the static sprite and plays the motion live, so 151 animated species cost 151
small files rather than 151 sprite sheets; the animated WebP previews here are the same
function baked to frames, for listings outside the game.

**Engine.** `render_art.py` defaults to `flux` (schnell). If the box's krea2 is healthy
it can be tried per run with `--engine krea2`; compare on a handful before switching the
whole roster.
