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
