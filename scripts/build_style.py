#!/usr/bin/env python3
"""
build_style.py -- build a second art style's stills for delivery (conductor t-107).

Reads styles/<style>/raw/<folder>/*.webp (harvested by render_art.py) and writes
styles/<style>/built/<folder>/*.webp, which kind_robots' sync mirrors into
assets/images/cthulhuquarium/styles/<style>/<folder>/. Each folder gets exactly the
treatment its Classic counterpart gets, using the same functions:

  sprites      cut out, scaled and rimmed (build_sprites.cutout); flipped if the fish faces left
  portraits    cut out and fitted to 560px tall (build_story_art)
  heroes       the full plate fitted to 720px tall
  backgrounds  paper margin trimmed, 1280px wide
  plates       1280px wide, paper kept
  ui           cut out (unless ui.yaml says otherwise) and scaled to its long edge (build_ui)

A built file is redone when its raw changed since it was built (content hashes in
styles/<style>/built/built.yaml, the same rule as sprites/built.yaml: never file times).

Usage:
    python3 scripts/build_style.py illustrious [--folder sprites] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sprites import cutout, cutout_image  # noqa: E402
from build_story_art import fit, trim_paper  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ("sprites", "portraits", "heroes", "backgrounds", "plates", "ui")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("style")
    parser.add_argument("--folder", choices=FOLDERS)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    base = ROOT / "styles" / args.style
    record_path = base / "built" / "built.yaml"
    record = (yaml.safe_load(record_path.read_text()) or {}) if record_path.exists() else {}
    faces = {}
    for path in (ROOT / "fish").glob("*.yaml"):
        fish = yaml.safe_load(path.read_text())
        faces[fish["slug"]] = (fish.get("sprite") or {}).get("faces")
    ui_spec = yaml.safe_load((ROOT / "ui/ui.yaml").read_text())
    ui_items = {item["key"]: item for item in ui_spec["items"]}
    session = None
    built = 0

    def rembg():
        nonlocal session
        if session is None:
            from rembg import new_session

            session = new_session("isnet-general-use")
        return session

    for folder in FOLDERS:
        if args.folder and folder != args.folder:
            continue
        for raw in sorted((base / "raw" / folder).glob("*.webp")):
            stem = raw.stem
            dest = base / "built" / folder / f"{stem}.webp"
            raw_hash = hashlib.sha1(raw.read_bytes()).hexdigest()[:12]
            key = f"{folder}/{stem}"
            if dest.exists() and record.get(key) == raw_hash and not args.force:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if folder == "sprites":
                image = cutout(raw, rembg())
                if faces.get(stem) == "left":
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                image.save(dest, "WEBP", quality=88, method=6)
            elif folder == "portraits":
                fit(cutout_image(Image.open(raw), rembg()), height=560).save(dest, "WEBP", quality=86, method=6)
            elif folder == "heroes":
                fit(Image.open(raw).convert("RGB"), height=720).save(dest, "WEBP", quality=84, method=6)
            elif folder in ("backgrounds", "plates"):
                image = Image.open(raw).convert("RGB")
                if folder == "backgrounds":
                    image = trim_paper(image)
                fit(image, width=1280).save(dest, "WEBP", quality=80, method=6)
            else:  # ui
                item = ui_items.get(stem, {})
                image = Image.open(raw)
                if item.get("cutout", True):
                    image = cutout_image(image, rembg())
                long_edge = item.get("long_edge", ui_spec["defaults"].get("long_edge", 256))
                scale = long_edge / max(image.size)
                image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                                     Image.LANCZOS)
                image.save(dest, "WEBP", quality=90, method=6)
            record[key] = raw_hash
            built += 1
            print(f"built {args.style} {key}", flush=True)

    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text("# Content hash of the raw each built file was made from (scripts/build_style.py).\n"
                           + yaml.safe_dump(dict(sorted(record.items())), sort_keys=False))
    print(f"{built} built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
