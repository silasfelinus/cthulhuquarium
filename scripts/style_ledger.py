#!/usr/bin/env python3
"""
style_ledger.py -- write a conductor art ledger for one group of a second art style (t-107).

render_art.py cannot submit an Illustrious render (its job path maps every engine to Krea 2),
so a styled round goes through conductor: this writes a lane ledger whose lane carries the
style's checkpoint and settings (art/styles.yaml), conductor's enqueue_art_requests.py submits
it, and `render_art.py adopt --ledger <it>` + `harvest` land the renders under
styles/<style>/raw/<folder>/. Each subject's `canon_key` is the styled render key.

The shared style text (and, for sprites, the shared framing) rides in the lane's `suffix`, and
each subject's `prompt_prose` holds only its own subject, so conductor's templated-prompt rule
(shared five-word runs across prompts) is satisfied. Character portraits keep the whole styled
sentence (the style sits mid-sentence) and are written one character per ledger, under the
rule's eight-subject floor. Wilbur's per-floor variants are not written here: like Classic,
they are Kontext edits of his styled base poses.

Usage:
    python3 scripts/style_ledger.py --style illustrious --group sprites --tier 1 \\
        --out ../conductor/projects/cthulhuquarium/art/ILLUSTRIOUS-SPRITES-T1.yaml
    python3 scripts/style_ledger.py --style illustrious --group portraits --who wilbur-stint --out ...
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_art  # noqa: E402

ROOT = render_art.ROOT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", required=True)
    parser.add_argument("--group", required=True, choices=sorted(render_art.STYLE_FOLDERS))
    parser.add_argument("--tier", type=int, help="sprites: one floor's fish (fish/*.yaml tier)")
    parser.add_argument("--who", help="portraits/heroes: one character slug")
    parser.add_argument("--only", nargs="*", help="render ids to include")
    parser.add_argument("--out", required=True)
    parser.add_argument("--priority", type=int, default=600)
    args = parser.parse_args()

    style = render_art.load_styles().get(args.style)
    if not style:
        print(f"unknown style {args.style}", file=sys.stderr)
        return 2
    if style.get("status") != "chosen" or not (style.get("lane") or {}).get("checkpoint"):
        print(f"{args.style} is not chosen yet (art/styles.yaml status/lane.checkpoint)", file=sys.stderr)
        return 2
    text_group = "portraits" if args.group == "heroes" else args.group
    text = render_art._flat((style.get("text") or {}).get(text_group) or "")
    if not text:
        print(f"{args.style} has no `text` for {text_group}", file=sys.stderr)
        return 2

    tiers = {}
    if args.tier is not None:
        for path in (ROOT / "fish").glob("*.yaml"):
            fish = yaml.safe_load(path.read_text())
            tiers[fish["slug"]] = int(fish.get("tier") or 0)
    rendered = render_art.load_rendered()
    jobs = [
        job for job in render_art.jobs()
        if job.get("style") == args.style and job["group"] == args.group
        and not re.search(r"-f\d+$", job["id"])
        and (args.tier is None or tiers.get(job["id"]) == args.tier)
        and (not args.who or job["id"].startswith(args.who))
        and (not args.only or job["id"] in args.only)
        and not render_art.is_current(job, rendered)
    ]
    if not jobs:
        print("nothing to render")
        return 0

    base_lane = dict(style["lane"])
    lanes: dict[str, dict] = {}
    subjects = []
    for job in jobs:
        if args.group in ("portraits", "heroes"):
            prose, suffix = job["prompt"], None
        elif args.group == "sprites":
            prose = job["subject"]
            suffix = job["prompt"][len(job["subject"]) + 2:]  # "<text>, <framing>"
        else:
            prose, suffix = job["subject"], text
        # One lane per distinct suffix (sprites framed singly or as a mass get two).
        existing = next((k for k, lane in lanes.items() if lane.get("suffix") == suffix), None)
        lane_key = existing or (base_lane["key"] if not lanes else f"{base_lane['key']}-{len(lanes) + 1}")
        if lane_key not in lanes:
            lane = {**base_lane, "key": lane_key, "label": f"{style.get('label', args.style)} ({args.group})"}
            if suffix:
                lane["suffix"] = suffix
            lanes[lane_key] = lane
        subjects.append({
            "key": job["id"],
            "lane": lane_key,
            "title": f"{style.get('label', args.style)}: {job['id']}",
            "canon_key": job["key"],
            "size": job["size"],
            "seed": int(job["hash"], 16) % 900000 + 100000,
            "prompt_prose": prose,
            "negative": job["negative"],
        })

    scope = args.tier and f"tier {args.tier}" or args.who or "all"
    header = (
        f"# Cthulhuquarium second art style ({args.style}), {args.group}, {scope} (conductor t-109).\n"
        f"# Written by cthulhuquarium scripts/style_ledger.py from art/styles.yaml; the canon adopts the\n"
        f"# finished jobs by canon_key (render_art.py adopt --ledger) and harvests them. Private.\n"
    )
    ledger = {
        "round": f"cthulhuquarium-{args.style}-{args.group}-{str(scope).replace(' ', '')}",
        "project_slug": "cthulhuquarium",
        "designer": f"Cthulhuquarium {style.get('label', args.style)} style (t-109)",
        "is_public": False,
        "is_mature": False,
        "cast_loras": False,
        "auto_submit": False,
        "priority": args.priority,
        "lanes": list(lanes.values()),
        "subjects": subjects,
    }
    out = Path(args.out)
    out.write_text(header + yaml.safe_dump(ledger, sort_keys=False, width=115))
    print(f"wrote {len(subjects)} subjects in {len(lanes)} lane(s) to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
