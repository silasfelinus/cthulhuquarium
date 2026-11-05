#!/usr/bin/env python3
"""Cut out the console UI art (ui/ui.yaml) for the kind_robots front end.

    ui/raw/<key>.webp   render on a flat backdrop (scripts/render_art.py ... ui)
      -> ui/built/<key>.webp   backdrop removed, trimmed, `long_edge` px (default 256)

`cutout: false` on an item keeps the whole render (a texture or panel fill) and only
resizes it. scripts/sync_cthulhuquarium_canon.mjs in kind_robots copies ui/built/ to
assets/images/cthulhuquarium/ui/.

    python3 scripts/build_ui.py            # every item with a raw render, not yet built
    python3 scripts/build_ui.py --force    # rebuild all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_sprites import cutout_image  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("keys", nargs="*")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    spec = yaml.safe_load((ROOT / "ui/ui.yaml").read_text())
    out = ROOT / "ui/built"
    out.mkdir(parents=True, exist_ok=True)
    session = None
    built = missing = 0
    for item in spec["items"]:
        key = item["key"]
        if args.keys and key not in args.keys:
            continue
        raw, dest = ROOT / "ui/raw" / f"{key}.webp", out / f"{key}.webp"
        if not raw.exists():
            missing += 1
            continue
        if dest.exists() and not args.force:
            continue
        image = Image.open(raw)
        if item.get("cutout", True):
            if session is None:
                from rembg import new_session

                session = new_session("isnet-general-use")
            image = cutout_image(image, session)
        long_edge = item.get("long_edge", spec["defaults"].get("long_edge", 256))
        scale = long_edge / max(image.size)
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
        image.save(dest, "WEBP", quality=90, method=6)
        built += 1
        print(f"built ui/{key}")
    print(f"{built} built, {missing} without a raw render yet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
