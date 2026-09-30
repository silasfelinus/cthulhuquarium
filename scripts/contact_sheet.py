#!/usr/bin/env python3
"""Lay built sprites out on dark water for review, each labelled with its slug.

    python3 scripts/contact_sheet.py                 # every built sprite -> /tmp/sprites.png
    python3 scripts/contact_sheet.py --since 60      # only those built in the last hour
    python3 scripts/contact_sheet.py -o sheet.png goby eel   # slugs containing these

What to look for: facing (every sprite must face RIGHT -- mark `sprite.faces: left`
and rebuild if not), a leftover backdrop or halo, a missing body part, and whether the
creature reads at the small size in the bottom row of each cell.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
CELL = 220
WATER = (20, 70, 62, 255)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("match", nargs="*")
    parser.add_argument("-o", "--out", default="/tmp/sprites.png")
    parser.add_argument("--since", type=float, help="minutes")
    parser.add_argument("--cols", type=int, default=6)
    args = parser.parse_args()
    files = sorted((ROOT / "sprites").glob("*.webp"))
    if args.match:
        files = [f for f in files if any(m in f.stem for m in args.match)]
    if args.since:
        cutoff = time.time() - args.since * 60
        files = [f for f in files if f.stat().st_mtime >= cutoff]
    if not files:
        print("no sprites match")
        return
    rows = (len(files) + args.cols - 1) // args.cols
    sheet = Image.new("RGBA", (args.cols * CELL, rows * (CELL + 20)), WATER)
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(files):
        x = (index % args.cols) * CELL
        y = (index // args.cols) * (CELL + 20)
        sprite = Image.open(path).convert("RGBA")
        big = sprite.copy()
        big.thumbnail((CELL - 20, CELL - 80))
        sheet.alpha_composite(big, (x + (CELL - big.width) // 2, y + 8))
        small = sprite.copy()
        small.thumbnail((60, 60))
        sheet.alpha_composite(small, (x + (CELL - small.width) // 2, y + CELL - 66))
        draw.text((x + 6, y + CELL + 2), path.stem[:30], fill=(230, 240, 230, 255))
    sheet.convert("RGB").save(args.out)
    print(f"{len(files)} sprites -> {args.out}")


if __name__ == "__main__":
    main()
