#!/usr/bin/env python3
"""Cut every fish clip out of its backdrop, frame by frame.

    clips/raw/<slug>.webp   WAN image-to-video of the fish's own sprite render,
                            on its flat studio backdrop (scripts/render_art.py)
      -> clips/<slug>.webp  animated, transparent, 200px on the long edge,
                            cropped to the creature's full range of motion

The result is the fish actually swimming, with no background, for listings and
the Ichthyonomicon. The tank keeps drawing the static sprite with procedural
motion (build_sprites.py), which is lighter to draw sixty times a second.

    python3 scripts/build_fish_clips.py             # every clip not yet built
    python3 scripts/build_fish_clips.py --force     # rebuild all
    python3 scripts/build_fish_clips.py drifting-bell
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageSequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sprites import with_rim  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "clips" / "raw"
OUT = ROOT / "clips"
LONG_EDGE = 200
KEEP_EVERY = 2  # 16 fps source -> 8 fps; the loop is short and slow enough
FRAME_MS = 125


def cut_frames(path: Path, session) -> list[Image.Image]:
    from rembg import remove

    frames = []
    with Image.open(path) as clip:
        for index, frame in enumerate(ImageSequence.Iterator(clip)):
            if index % KEEP_EVERY:
                continue
            cut = remove(frame.convert("RGB"), session=session, post_process_mask=True)
            alpha = cut.getchannel("A").point(lambda v: 0 if v < 24 else v)
            cut.putalpha(alpha)
            frames.append(cut)
    return frames


def build(slug: str, session) -> bool:
    frames = cut_frames(RAW / f"{slug}.webp", session)
    if not frames:
        return False
    box = None
    for frame in frames:
        bbox = frame.getchannel("A").getbbox()
        if bbox:
            box = bbox if box is None else (
                min(box[0], bbox[0]), min(box[1], bbox[1]), max(box[2], bbox[2]), max(box[3], bbox[3]),
            )
    if box is None:
        return False
    scale = LONG_EDGE / max(box[2] - box[0], box[3] - box[1])
    size = (max(1, round((box[2] - box[0]) * scale)), max(1, round((box[3] - box[1]) * scale)))
    out = [with_rim(frame.crop(box).resize(size, Image.LANCZOS)) for frame in frames]
    out[0].save(
        OUT / f"{slug}.webp", "WEBP", save_all=True, append_images=out[1:],
        duration=FRAME_MS, loop=0, quality=72, method=6,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slugs", nargs="*")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    session = None
    built = 0
    for raw in sorted(RAW.glob("*.webp")) if RAW.exists() else []:
        slug = raw.stem
        if args.slugs and slug not in args.slugs:
            continue
        if not args.force and (OUT / f"{slug}.webp").exists():
            continue
        if session is None:
            from rembg import new_session

            session = new_session("isnet-general-use")
        if build(slug, session):
            built += 1
            print(f"built clip {slug}", flush=True)
    print(f"{built} clips built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
