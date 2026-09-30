#!/usr/bin/env python3
"""Render the bespoke art this repo describes, through the Kind Robots art queue.

Collects every render the canon asks for and submits the missing ones:

    sprites     fish/<slug>.yaml  sprite.prompt          -> sprites/raw/<slug>.webp
    portraits   characters/<who>.yaml art.portraits.*     -> characters/raw/<who>-<pose>.webp
    heroes      characters/<who>.yaml art.hero            -> characters/raw/<who>-hero.webp
    backgrounds backgrounds/backgrounds.yaml              -> backgrounds/raw/<key>.webp
    plates      story/plates.yaml                         -> story/raw/<key>.webp

A raw file that already exists is skipped, so a run is resumable and a bad render is
redone by deleting its raw file. Raw renders are the only input build_sprites.py and
build_story_art.py need; they are committed so a rebuild never re-renders.

Uses conductor's scripts/consume_art_queue_core.py for the queue protocol (enqueue,
poll, download) so there is one client for the queue, not two. Needs KR_API_TOKEN.

    python3 scripts/render_art.py --list                    # what is missing
    python3 scripts/render_art.py sprites --par 4           # render missing sprites
    python3 scripts/render_art.py all --only drifting-bell  # one id, any group
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import os
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GROUPS = ("sprites", "portraits", "heroes", "backgrounds", "plates")
# Measured 2026-09-30: flux schnell follows layout instructions (side profile, flat
# backdrop) far more reliably than krea2 for isolated subjects. Override per run.
DEFAULT_ENGINE = {"sprites": "flux", "portraits": "flux", "heroes": "flux",
                  "backgrounds": "flux", "plates": "flux"}


def _flat(text: str) -> str:
    return " ".join(str(text).split())


def jobs() -> list[dict]:
    out: list[dict] = []
    for path in sorted((ROOT / "fish").glob("*.yaml")):
        fish = yaml.safe_load(path.read_text())
        sprite = fish.get("sprite") or {}
        if sprite.get("prompt"):
            size = "1216x832" if sprite.get("motion") in ("tailbeat", "undulate", "ripple") else "1024x1024"
            out.append({"group": "sprites", "id": fish["slug"], "size": size,
                        "prompt": _flat(sprite["prompt"]), "dest": ROOT / "sprites/raw" / f"{fish['slug']}.webp"})
    for path in sorted((ROOT / "characters").glob("*.yaml")):
        who = yaml.safe_load(path.read_text())
        art = who.get("art") or {}
        fill = {"base": _flat(art.get("base", "")), "medium": _flat(art.get("medium", ""))}
        if art.get("hero"):
            out.append({"group": "heroes", "id": f"{who['slug']}-hero", "size": art["hero"].get("size", "832x1216"),
                        "prompt": _flat(art["hero"]["prompt"]).format(**fill),
                        "dest": ROOT / "characters/raw" / f"{who['slug']}-hero.webp"})
        for pose, spec in (art.get("portraits") or {}).items():
            out.append({"group": "portraits", "id": f"{who['slug']}-{pose}", "size": spec.get("size", "896x1152"),
                        "prompt": _flat(spec["prompt"]).format(**fill),
                        "dest": ROOT / "characters/raw" / f"{who['slug']}-{pose}.webp"})
    bgs = yaml.safe_load((ROOT / "backgrounds/backgrounds.yaml").read_text())
    for bg in bgs["backgrounds"]:
        out.append({"group": "backgrounds", "id": bg["key"], "size": bg.get("size", bgs["defaults"]["size"]),
                    "prompt": _flat(bg["prompt"]), "dest": ROOT / "backgrounds/raw" / f"{bg['key']}.webp"})
    for plate in yaml.safe_load((ROOT / "story/plates.yaml").read_text())["plates"]:
        out.append({"group": "plates", "id": plate["key"], "size": plate.get("size", "1344x768"),
                    "prompt": _flat(plate["prompt"]), "dest": ROOT / "story/raw" / f"{plate['key']}.webp"})
    return out


def render(job: dict, core, engine: str, timeout: int) -> str:
    entry = {"prompt": job["prompt"], "size": job["size"], "engine": engine, "project": "cthulhuquarium",
             "image_path": f"projects/process/cthulhuquarium-{job['group']}-{job['id']}.webp",
             "label": f"Cthulhuquarium {job['group']}: {job['id']}"}
    last = ""
    for _ in range(2):
        try:
            started = time.time()
            job_id = core.enqueue(core.entry_to_job(entry))
            done = core.wait_for_job(job_id, timeout)
            data = base64.b64decode(core.fetch_image_b64(done["artImageId"]))
            job["dest"].parent.mkdir(parents=True, exist_ok=True)
            tmp = job["dest"].with_suffix(".part")
            tmp.write_bytes(data)
            _to_webp(tmp, job["dest"])
            return f"ok  {job['group']}/{job['id']} job {job_id} ArtImage {done['artImageId']} {int(time.time() - started)}s"
        except Exception as error:  # noqa: BLE001 -- one retry, then report
            last = str(error)
    return f"FAIL {job['group']}/{job['id']}: {last}"


def _to_webp(src: Path, dest: Path) -> None:
    # Raw renders are committed (a rebuild never re-renders), so they are kept
    # as near-lossless WebP rather than 1.5MB PNGs.
    from PIL import Image

    Image.open(src).convert("RGB").save(dest, "WEBP", quality=94, method=6)
    src.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("group", nargs="?", default="all", choices=("all",) + GROUPS)
    parser.add_argument("--only", nargs="*", help="ids to render")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--par", type=int, default=4, help="jobs in flight at once")
    parser.add_argument("--engine", help="override the engine for every job")
    parser.add_argument("--timeout", type=int, default=5400)
    parser.add_argument("--conductor", default=str(ROOT.parent / "conductor"))
    args = parser.parse_args()

    todo = [j for j in jobs() if (args.group == "all" or j["group"] == args.group)
            and (not args.only or j["id"] in args.only) and not j["dest"].exists()]
    if args.list:
        for j in todo:
            print(f"{j['group']:<12} {j['id']}")
        print(f"{len(todo)} missing")
        return 0
    if not os.environ.get("KR_API_TOKEN"):
        print("KR_API_TOKEN is not set", file=sys.stderr)
        return 2
    sys.path.insert(0, str(Path(args.conductor) / "scripts"))
    import consume_art_queue_core as core  # noqa: E402

    failed = 0
    with cf.ThreadPoolExecutor(max(1, args.par)) as pool:
        futures = [pool.submit(render, j, core, args.engine or DEFAULT_ENGINE[j["group"]], args.timeout) for j in todo]
        for future in cf.as_completed(futures):
            line = future.result()
            failed += line.startswith("FAIL")
            print(line, flush=True)
    print(f"{len(todo) - failed} rendered, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
