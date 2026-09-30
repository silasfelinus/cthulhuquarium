#!/usr/bin/env python3
"""Build the web-ready story art from raw renders (scripts/render_art.py).

    characters/raw/<who>-<pose>.webp -> characters/portraits/<who>-<pose>.webp   cut out, 560px tall
    characters/raw/<who>-hero.webp  -> characters/portraits/hero/<who>.webp     full plate, 720px tall
    backgrounds/raw/<key>.webp      -> backgrounds/built/<key>.webp             1280px wide
    story/raw/<key>.webp            -> story/built/<key>.webp                   1280px wide

Portraits are cut out because they stand in front of the dialogue box and the tank;
the hero plates and backgrounds keep their painted backdrops.

    python3 scripts/build_story_art.py            # build whatever has a raw render
    python3 scripts/build_story_art.py --force    # rebuild everything
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sprites import cutout_image  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


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
                fit(Image.open(raw).convert("RGB"), width=1280).save(dest, "WEBP", quality=80, method=6)
                built += 1

    print(f"{built} built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
