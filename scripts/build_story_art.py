#!/usr/bin/env python3
"""Build the web-ready story art from raw renders (scripts/render_art.py).

    characters/raw/<who>-<pose>.webp -> characters/portraits/<who>-<pose>.webp   cut out, 560px tall
    characters/raw/<who>-hero.webp  -> characters/portraits/hero/<who>.webp     full plate, 720px tall
    backgrounds/raw/<key>.webp      -> backgrounds/built/<key>.webp             1280px wide
    story/raw/<key>.webp            -> story/built/<key>.webp                   1280px wide
    videos/raw/<key>.webp           -> videos/built/<key>.webp                  640px wide, animated

Portraits are cut out because they stand in front of the dialogue box and the tank;
the hero plates and backgrounds keep their painted backdrops.

    python3 scripts/build_story_art.py            # build whatever has a raw render
    python3 scripts/build_story_art.py --force    # rebuild everything
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageSequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sprites import cutout_image  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def trim_paper(image: Image.Image, limit: float = 0.08) -> Image.Image:
    """Cut away a pale printed-paper margin (lithograph plates sometimes arrive with
    one, and a gibberish caption in it) from any edge, up to `limit` of that edge.
    A row or column counts as paper when nearly all of it is light and unsaturated."""
    rgb = image.convert("RGB")
    small = rgb.resize((max(1, rgb.width // 4), max(1, rgb.height // 4)))
    hsv = small.convert("HSV")
    w, h = small.size
    px, hs = small.load(), hsv.load()

    def paper(points) -> bool:
        pts = list(points)
        light = sum(1 for x, y in pts if sum(px[x, y]) / 3 > 200 and hs[x, y][1] < 60)
        return light >= 0.6 * len(pts)

    top = 0
    while top < h * limit and paper((x, top) for x in range(w)):
        top += 1
    bottom = h
    while h - bottom < h * limit and paper((x, bottom - 1) for x in range(w)):
        bottom -= 1
    left = 0
    while left < w * limit and paper((left, y) for y in range(h)):
        left += 1
    right = w
    while w - right < w * limit and paper((right - 1, y) for y in range(h)):
        right -= 1
    if (top, left, bottom, right) == (0, 0, h, w):
        return image
    # The scan runs at quarter size, so shave a few more real pixels off any edge it
    # moved, or a sliver of the caption survives.
    pad = 8
    return image.crop((
        left * 4 + (pad if left else 0),
        top * 4 + (pad if top else 0),
        right * 4 - (pad if right < w else 0),
        bottom * 4 - (pad if bottom < h else 0),
    ))


def fit(image: Image.Image, *, width: int | None = None, height: int | None = None) -> Image.Image:
    scale = (width / image.width) if width else (height / image.height)
    return image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    session = None
    built = 0

    def fresh(dest: Path) -> bool:
        return args.force or not dest.exists()

    for raw in sorted((ROOT / "characters/raw").glob("*.webp")):
        stem = raw.stem
        if stem.endswith("-hero"):
            dest = ROOT / "characters/portraits/hero" / f"{stem[:-5]}.webp"
            if fresh(dest):
                dest.parent.mkdir(parents=True, exist_ok=True)
                fit(Image.open(raw).convert("RGB"), height=720).save(dest, "WEBP", quality=84, method=6)
                built += 1
            continue
        dest = ROOT / "characters/portraits" / f"{stem}.webp"
        if fresh(dest):
            if session is None:
                from rembg import new_session

                session = new_session("isnet-general-use")
            dest.parent.mkdir(parents=True, exist_ok=True)
            fit(cutout_image(Image.open(raw), session), height=560).save(dest, "WEBP", quality=86, method=6)
            built += 1

    for src_dir, out_dir in (("backgrounds/raw", "backgrounds/built"), ("story/raw", "story/built")):
        for raw in sorted((ROOT / src_dir).glob("*.webp")):
            dest = ROOT / out_dir / f"{raw.stem}.webp"
            if fresh(dest):
                dest.parent.mkdir(parents=True, exist_ok=True)
                image = Image.open(raw).convert("RGB")
                # Backgrounds fill the tank edge to edge, so a paper margin is a flaw;
                # story plates are objects drawn on the paper, so theirs is kept.
                if src_dir == "backgrounds/raw":
                    image = trim_paper(image)
                fit(image, width=1280).save(dest, "WEBP", quality=80, method=6)
                built += 1

    # WAN delivers 832px animated WebPs of 3.5-7 MB; the game shows them no wider than
    # the dialogue plate (~770px CSS, far less on a phone), so they ship at 640px and
    # a lighter quality, every frame and its timing kept.
    for raw in sorted((ROOT / "videos/raw").glob("*.webp")):
        dest = ROOT / "videos/built" / f"{raw.stem}.webp"
        if fresh(dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(raw) as clip:
                durations = []
                frames = []
                for frame in ImageSequence.Iterator(clip):
                    durations.append(frame.info.get("duration", 62))
                    frames.append(fit(frame.convert("RGB"), width=640))
            frames[0].save(dest, "WEBP", save_all=True, append_images=frames[1:],
                           duration=durations, loop=0, quality=60, method=4)
            built += 1

    print(f"{built} built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
