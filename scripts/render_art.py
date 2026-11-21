#!/usr/bin/env python3
"""Render the bespoke art this repo describes, through the Kind Robots art queue.

Collects every render the canon asks for:

    sprites     fish/<slug>.yaml  sprite.prompt          -> sprites/raw/<slug>.webp
    portraits   characters/<who>.yaml art.portraits.*     -> characters/raw/<who>-<pose>.webp
    heroes      characters/<who>.yaml art.hero            -> characters/raw/<who>-hero.webp
    backgrounds backgrounds/backgrounds.yaml              -> backgrounds/raw/<key>.webp
    plates      story/plates.yaml                         -> story/raw/<key>.webp
    videos      videos/videos.yaml (WAN image-to-video)   -> videos/raw/<key>.webp  (animated)
    clips       every fish, from its sprite render (WAN)  -> clips/raw/<slug>.webp  (animated)
    ui          ui/ui.yaml (console UI art: tab icons, coin, plinth, ornaments) -> ui/raw/<key>.webp

A video is submitted only once its source still exists, so `submit` after each
`harvest` sends the clips whose stills just arrived.

The render box is a home gaming PC that renders when it is free, so rendering is
two steps that need not happen in the same session:

    python3 scripts/render_art.py submit        # enqueue everything missing, record job ids
    python3 scripts/render_art.py harvest       # download whatever has finished since
    python3 scripts/render_art.py status        # counts: missing / queued / done / failed

`art/jobs.yaml` is the committed record of what is in flight: one entry per render
with its ArtJob id and a hash of the prompt it was submitted with. `submit` skips
anything already raw from its current prompt (art/rendered.yaml) or already in flight
with the same prompt; editing a prompt makes the raw and any in-flight entry stale, and
`submit` sends the new one, which `harvest` writes over the old raw. `harvest` drops FAILED and
CANCELLED entries so the next `submit` retries them. Commit `art/jobs.yaml` and the
raw renders after each run, so any later session can pick up where this one left off.

Uses conductor's scripts/consume_art_queue_core.py for the queue protocol so there
is one client for the queue, not two. Needs KR_API_TOKEN.

    python3 scripts/render_art.py submit sprites --only drifting-bell
    python3 scripts/render_art.py list            # what is missing, nothing sent
    python3 scripts/render_art.py adopt --ledger ../conductor/projects/cthulhuquarium/art/X.yaml
                                                  # collect a conductor ledger's renders
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "art" / "jobs.yaml"
GROUPS = ("sprites", "portraits", "heroes", "backgrounds", "plates", "videos", "clips", "ui")
# Krea 2 since 2026-11-05 (t-099): Silas found the flux renders "too harsh and
# naturalistic", and the Krea 2 / Illustrious style test kept side profile and a clean
# backdrop on Krea 2 while Illustrious added legs and floor shadows. Override with --engine.
DEFAULT_ENGINE = "krea2"
# Below the Daily Dream lane (200) and Mandarin curriculum art (80): this queue is
# large and patient, and should never hold up time-sensitive work.
PRIORITY = 20
# Fish clips come after every still: the sprite itself is what the tank needs.
CLIP_PRIORITY = 10

# What each body motion (fish/SCHEMA.md "Sprites") looks like as a clip prompt.
FISH_CLIP_MOTION = {
    "tailbeat": "the fish swims steadily in place, its tail sweeping side to side and its fins rippling",
    "undulate": "the long body ripples in a slow travelling wave from head to tail as it swims in place",
    "ripple": "the fins and frilled edges ripple in fine fast waves as it hangs in the water",
    "pulse": "the bell contracts and relaxes in a slow rhythmic pulse, the trailing parts swaying behind",
    "sway": "it sways gently from its base, the upper parts drifting in a slow current",
    "breathe": "it breathes slowly, its body swelling and settling, small parts stirring",
    "rigid": "it turns slowly in place, catching the light on its hard edges",
}


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
        # Per-floor variants (characters/wilbur-stint.yaml art.floor_variants, t-103):
        # the same poses with {base} grown by every floor's additions up to N.
        variants = art.get("floor_variants") or {}
        grown = fill["base"]
        for floor in sorted(variants, key=int):
            grown = f"{grown}, {_flat(variants[floor]['adds'])}"
            floor_fill = {**fill, "base": grown}
            for pose, spec in (art.get("portraits") or {}).items():
                # Rendered as Flux Kontext edits of the shipped base pose (conductor
                # projects/cthulhuquarium/art/WILBUR-FLOORS-KONTEXT-1-F*.yaml), which keeps
                # him the same man; a text render drew someone else (2026-11-21). `submit`
                # never sends these; `adopt` records the Kontext jobs and `harvest` lands them.
                out.append({"group": "portraits", "id": f"{who['slug']}-{pose}-f{int(floor)}",
                            "size": spec.get("size", "896x1152"),
                            "prompt": _flat(spec["prompt"]).format(**floor_fill),
                            "adopt_only": True,
                            "dest": ROOT / "characters/raw" / f"{who['slug']}-{pose}-f{int(floor)}.webp"})
    bgs = yaml.safe_load((ROOT / "backgrounds/backgrounds.yaml").read_text())
    for bg in bgs["backgrounds"]:
        out.append({"group": "backgrounds", "id": bg["key"], "size": bg.get("size", bgs["defaults"]["size"]),
                    "prompt": _flat(bg["prompt"]), "dest": ROOT / "backgrounds/raw" / f"{bg['key']}.webp"})
    ui_path = ROOT / "ui/ui.yaml"
    if ui_path.exists():
        ui = yaml.safe_load(ui_path.read_text())
        for item in ui["items"]:
            out.append({"group": "ui", "id": item["key"], "size": item.get("size", ui["defaults"]["size"]),
                        "prompt": _flat(f"{item['prompt']}, {ui['defaults']['suffix']}"),
                        "dest": ROOT / "ui/raw" / f"{item['key']}.webp"})
    for plate in yaml.safe_load((ROOT / "story/plates.yaml").read_text())["plates"]:
        out.append({"group": "plates", "id": plate["key"], "size": plate.get("size", "1344x768"),
                    "prompt": _flat(plate["prompt"]), "dest": ROOT / "story/raw" / f"{plate['key']}.webp"})
    # Every fish also gets a real swimming clip, animated from its own sprite
    # render (WAN image-to-video), submitted the moment that render exists.
    # build_fish_clips.py cuts the backdrop out of every frame, so the result
    # is an animated, transparent specimen for listings and the book; the
    # tank keeps its lighter procedural motion.
    for path in sorted((ROOT / "fish").glob("*.yaml")):
        fish = yaml.safe_load(path.read_text())
        sprite = fish.get("sprite") or {}
        if not sprite.get("prompt"):
            continue
        wide = sprite.get("motion") in ("tailbeat", "undulate", "ripple")
        width, height = (832, 576) if wide else (640, 640)
        out.append({"group": "clips", "id": fish["slug"],
                    "prompt": _flat(f"{FISH_CLIP_MOTION.get(sprite.get('motion'), FISH_CLIP_MOTION['tailbeat'])}, "
                                    f"{fish['name']}, the plain flat studio backdrop perfectly still, "
                                    f"the creature staying centred in view"),
                    "size": f"{width}x{height}", "seconds": 3, "fps": 16, "priority": CLIP_PRIORITY,
                    "source": ROOT / "sprites/raw" / f"{fish['slug']}.webp",
                    "dest": ROOT / "clips/raw" / f"{fish['slug']}.webp"})
    vids = yaml.safe_load((ROOT / "videos/videos.yaml").read_text())
    for clip in vids["videos"]:
        spec = {**vids["defaults"], **clip}
        out.append({"group": "videos", "id": clip["key"], "prompt": _flat(clip["prompt"]),
                    "size": f"{spec['width']}x{spec['height']}", "seconds": spec["seconds"],
                    "fps": spec["fps"], "source": ROOT / clip["source"],
                    "dest": ROOT / "videos/raw" / f"{clip['key']}.webp"})
    for job in out:
        job["key"] = f"{job['group']}/{job['id']}"
        job["hash"] = hashlib.sha1(f"{job['prompt']}|{job['size']}".encode()).hexdigest()[:12]
    # A fish clip is animated from its sprite render, so a re-rendered sprite makes the
    # clip stale too: fold the sprite's prompt hash into the clip's.
    sprite_hash = {j["id"]: j["hash"] for j in out if j["group"] == "sprites"}
    for job in out:
        if job["group"] == "clips" and job["id"] in sprite_hash:
            job["source_key"] = f"sprites/{job['id']}"
            job["hash"] = hashlib.sha1(f"{job['hash']}|{sprite_hash[job['id']]}".encode()).hexdigest()[:12]
    return out + styled_jobs(out)


STYLES = ROOT / "art" / "styles.yaml"
# A styled render's folder in styles/<id>/{raw,built}/ (and in kind_robots'
# assets/images/cthulhuquarium/styles/<id>/), by Classic group.
STYLE_FOLDERS = {"sprites": "sprites", "portraits": "portraits", "heroes": "heroes",
                 "backgrounds": "backgrounds", "plates": "plates", "ui": "ui"}


def load_styles() -> dict:
    if not STYLES.exists():
        return {}
    return (yaml.safe_load(STYLES.read_text()) or {}).get("styles") or {}


def styled_subject(job: dict, style: dict, sprite_style: dict, mediums: dict, ui_suffix: str) -> str | None:
    """The canon subject of a Classic job with its Classic style half removed (art/styles.yaml)."""
    group, prompt = job["group"], job["prompt"]
    if group == "sprites":
        # Anchored on the clause's first phrase: a few prompts carry the clause with a
        # folding glitch ("jewel- tone"), so the whole clause is not matched verbatim.
        anchor = _flat(sprite_style["clause"]).split(",")[0]
        return prompt.split(f", {anchor}")[0] if anchor in prompt else None
    if group in ("portraits", "heroes"):
        who = next((slug for slug in mediums if job["id"].startswith(slug)), None)
        medium = mediums.get(who)
        return prompt.replace(medium, "{medium}") if medium and medium in prompt else None
    if group == "ui":
        tail = f", {ui_suffix}"
        return prompt[: -len(tail)] if ui_suffix and prompt.endswith(tail) else prompt
    markers = (style.get("strip") or {}).get(group) or []
    cuts = [prompt.find(marker) for marker in markers if marker in prompt]
    return prompt[: min(cuts)].rstrip(" ,") if cuts else prompt


def styled_prompt(job: dict, subject: str, text: str, sprite_style: dict) -> str:
    group = job["group"]
    if group == "sprites":
        framings = [_flat(sprite_style[k]) for k in ("framing", "framing_mass") if sprite_style.get(k)]
        framing = next((f for f in framings if f in job["prompt"]), framings[0])
        return f"{subject}, {text}, {framing}"
    if group in ("portraits", "heroes"):
        return subject.replace("{medium}", text)
    return f"{subject}, {text}"


def styled_jobs(classic: list[dict]) -> list[dict]:
    """Every Classic still again in each art style of art/styles.yaml (t-107), adopt-only.

    Keyed `styles/<style>/<group>/<id>`; raws land in styles/<style>/raw/<folder>/. A style
    contributes no jobs until each group it renders has its `text` written (after its
    style check is chosen), so the Classic pipeline is unchanged until then.
    """
    styles = load_styles()
    if not styles:
        return []
    sprite_style = yaml.safe_load((ROOT / "art/sprite-style.yaml").read_text())
    mediums = {}
    for path in sorted((ROOT / "characters").glob("*.yaml")):
        who = yaml.safe_load(path.read_text())
        medium = (who.get("art") or {}).get("medium")
        if medium:
            mediums[who["slug"]] = _flat(medium)
    ui_path = ROOT / "ui/ui.yaml"
    ui_suffix = _flat(yaml.safe_load(ui_path.read_text())["defaults"]["suffix"]) if ui_path.exists() else ""
    out: list[dict] = []
    for style_id, style in styles.items():
        texts = style.get("text") or {}
        for job in classic:
            text_group = "portraits" if job["group"] == "heroes" else job["group"]
            folder = STYLE_FOLDERS.get(job["group"])
            text = texts.get(text_group)
            if not folder or not text:
                continue
            subject = styled_subject(job, style, sprite_style, mediums, ui_suffix)
            if subject is None:
                print(f"  {style_id}: no subject for {job['key']}", file=sys.stderr)
                continue
            stem = job["id"][: -len("-hero")] if job["group"] == "heroes" else job["id"]
            prompt = _flat(styled_prompt(job, subject, _flat(text), sprite_style))
            key = f"styles/{style_id}/{job['group']}/{job['id']}"
            out.append({
                "group": job["group"], "id": job["id"], "style": style_id, "folder": folder,
                "stem": stem, "size": job["size"], "prompt": prompt, "subject": subject,
                "negative": ((style.get("negative") or {}).get(text_group) or ""),
                "adopt_only": True, "key": key,
                "dest": ROOT / "styles" / style_id / "raw" / folder / f"{stem}.webp",
                "hash": hashlib.sha1(f"{style_id}|{prompt}|{job['size']}".encode()).hexdigest()[:12],
            })
    return out


RENDERED = ROOT / "art" / "rendered.yaml"


def load_rendered() -> dict:
    """key -> hash of the prompt that produced the raw file on disk.

    A raw whose recorded hash differs from its job's current hash is stale: its prompt
    was rewritten (t-099 restyled every sprite), so `submit` sends the new prompt and
    `harvest` overwrites the old raw when the new one lands. Nothing is deleted first;
    the old raw stays in git history. A raw with no record predates this file and is
    taken as current unless its group is listed in `stale_groups` there.
    """
    if not RENDERED.exists():
        return {"stale_groups": [], "hashes": {}}
    data = yaml.safe_load(RENDERED.read_text()) or {}
    return {"stale_groups": data.get("stale_groups") or [], "hashes": data.get("hashes") or {}}


def save_rendered(rendered: dict) -> None:
    header = ("# Which prompt produced each committed raw render (scripts/render_art.py).\n"
              "# Written by `harvest`. A raw whose hash differs from its prompt's is re-rendered.\n")
    RENDERED.write_text(header + yaml.safe_dump({"stale_groups": rendered["stale_groups"],
                                                 "hashes": dict(sorted(rendered["hashes"].items()))},
                                                sort_keys=False))


def is_current(job: dict, rendered: dict) -> bool:
    if not job["dest"].exists():
        return False
    recorded = rendered["hashes"].get(job["key"])
    if recorded is None:
        return job["group"] not in rendered["stale_groups"]
    return recorded == job["hash"]


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    return (yaml.safe_load(MANIFEST.read_text()) or {}).get("jobs") or {}


def save_manifest(entries: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    header = ("# In-flight ArtJobs for this repo's renders (scripts/render_art.py).\n"
              "# Written by `submit`, drained by `harvest`. Commit it.\n")
    MANIFEST.write_text(header + yaml.safe_dump({"jobs": dict(sorted(entries.items()))}, sort_keys=False))


def core_module(conductor: str):
    sys.path.insert(0, str(Path(conductor) / "scripts"))
    import consume_art_queue_core as core  # noqa: E402

    return core


def to_webp(data: bytes, dest: Path) -> None:
    # Raw renders are committed (a rebuild never re-renders), so they are kept as
    # near-lossless WebP rather than 1.5MB PNGs.
    import io

    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.open(io.BytesIO(data)).convert("RGB").save(dest, "WEBP", quality=94, method=6)


def video_first_frame(source: Path, size: str) -> str:
    """The source still, cover-cropped to the clip's size, as a PNG data URI."""
    import io

    from PIL import Image

    width, height = (int(v) for v in size.split("x"))
    image = Image.open(source).convert("RGB")
    scale = max(width / image.width, height / image.height)
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = (image.width - width) // 2
    top = (image.height - height) // 2
    image = image.crop((left, top, left + width, top + height))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def submit_video(job: dict, core) -> int:
    width, height = (int(v) for v in job["size"].split("x"))
    body = {
        "engine": "wan", "promptString": job["prompt"], "negativePrompt": "",
        "firstImageBase64": video_first_frame(job["source"], job["size"]),
        "width": width, "height": height, "fps": job["fps"],
        "durationSeconds": job["seconds"], "loop": True, "outputFormat": "webp",
        "projectSlug": "cthulhuquarium", "priority": job.get("priority", PRIORITY), "isPublic": True,
    }
    status, resp = core.http_json("POST", f"{core.KR_BASE_URL}/api/video/generate", body, timeout=120)
    if status not in (200, 201) or not resp or not resp.get("success"):
        raise RuntimeError(f"video enqueue failed: HTTP {status} {resp and resp.get('message')}")
    data = resp.get("data") or {}
    job_id = data.get("jobId") or (data.get("job") or {}).get("id")
    if not job_id:
        raise RuntimeError(f"video enqueue returned no job id: {str(resp)[:200]}")
    return int(job_id)


def submit(todo: list[dict], core, engine: str, manifest: dict, current_keys: set | None = None) -> None:
    current_keys = current_keys or set()
    sent = waiting = 0
    for job in todo:
        if job.get("adopt_only"):
            continue
        current = manifest.get(job["key"])
        if current and current.get("hash") == job["hash"]:
            continue
        if job["group"] in ("videos", "clips"):
            if not job["source"].exists() or (job.get("source_key") and job["source_key"] not in current_keys):
                waiting += 1
                continue
            job_id = submit_video(job, core)
            manifest[job["key"]] = {"job": job_id, "hash": job["hash"], "engine": "wan",
                                    "submitted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            sent += 1
            # A video enqueue can take minutes; record each one so a run killed
            # mid-batch never leaves a submitted job missing from the manifest.
            save_manifest(manifest)
            print(f"  submitted {job['key']} (job {job_id})", flush=True)
            continue
        entry = {"prompt": job["prompt"], "size": job["size"], "engine": engine, "project": "cthulhuquarium",
                 "priority": PRIORITY,
                 "image_path": f"projects/process/cthulhuquarium-{job['group']}-{job['id']}.webp",
                 "label": f"Cthulhuquarium {job['group']}: {job['id']}"}
        body = core.entry_to_job(entry)
        job_id = core.enqueue(body)
        manifest[job["key"]] = {"job": job_id, "hash": job["hash"], "engine": engine,
                                "submitted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        sent += 1
        if sent % 20 == 0:
            save_manifest(manifest)
            print(f"  submitted {sent}", flush=True)
    save_manifest(manifest)
    print(f"submitted {sent}" + (f" ({waiting} videos still waiting on their source still)" if waiting else ""))


def harvest(core, manifest: dict, by_key: dict, rendered: dict) -> None:
    done = failed = waiting = 0
    for key, entry in list(manifest.items()):
        job = by_key.get(key)
        # Drop entries for renders that no longer exist, or that an older prompt sent.
        if job is None or entry.get("hash") != job["hash"] or is_current(job, rendered):
            manifest.pop(key)
            continue
        status, resp = core.http_json("GET", f"{core.KR_BASE_URL}/api/art/queue/{entry['job']}")
        if status != 200 or not resp or not resp.get("success"):
            waiting += 1
            continue
        art = resp["data"]["job"]
        if art["status"] == "DONE" and art.get("artImageId"):
            try:
                data = base64.b64decode(core.fetch_image_b64(art["artImageId"]))
            except RuntimeError as error:
                # A DONE job whose image bytes cannot be fetched (2026-11-21: one of the
                # adopted Forge plates) must not stop the rest of the harvest.
                print(f"  unfetchable {key} (ArtImage {art['artImageId']}): {str(error)[:120]}", flush=True)
                waiting += 1
                continue
            if job["group"] in ("videos", "clips"):
                job["dest"].parent.mkdir(parents=True, exist_ok=True)
                job["dest"].write_bytes(data)
            else:
                to_webp(data, job["dest"])
            manifest.pop(key)
            rendered["hashes"][key] = job["hash"]
            done += 1
            print(f"  harvested {key} (ArtImage {art['artImageId']})", flush=True)
        elif art["status"] in ("FAILED", "CANCELLED"):
            manifest.pop(key)
            failed += 1
            print(f"  {art['status']} {key}: {(art.get('error') or '')[:120]}", flush=True)
        else:
            waiting += 1
    save_manifest(manifest)
    save_rendered(rendered)
    print(f"harvested {done}, failed {failed} (will resubmit), still queued {waiting}")


def adopt(ledger_path: str, mapping: dict, by_key: dict, manifest: dict, rendered: dict) -> None:
    """Take renders a conductor art ledger submitted into this repo's manifest.

    A conductor ledger with `auto_submit: true` is rendered by conductor's own workflow,
    with no KR_API_TOKEN in this session. Its job ids land in the ledger, not in
    art/jobs.yaml, so `harvest` (and deliver.sh) never collected them -- that is how
    the 2026-11-02 Forge scene plates rendered and then sat unused. `adopt` records
    those job ids against this repo's render keys, so the next `harvest` downloads them
    like any job `submit` sent. A subject names its key with `canon_key:` (for example
    `portraits/wilbur-stint-wince-f2`), or `--map subject=key` supplies it. Needs no token.
    """
    ledger = yaml.safe_load(Path(ledger_path).read_text())
    adopted = skipped = 0
    for subject in ledger.get("subjects") or []:
        key = mapping.get(subject.get("key")) or subject.get("canon_key")
        if not key:
            continue
        job = by_key.get(key)
        if job is None:
            print(f"  {subject['key']}: unknown render key {key}", file=sys.stderr)
            skipped += 1
            continue
        lane_jobs = subject.get("jobs") or {}
        lane_key = subject.get("lane") or (next(iter(lane_jobs), None) if lane_jobs else None)
        job_id = lane_jobs.get(lane_key) if lane_key else None
        if not job_id:
            skipped += 1
            continue
        if is_current(job, rendered):
            skipped += 1
            continue
        lanes = {lane.get("key"): lane for lane in ledger.get("lanes") or []}
        engine = (lanes.get(lane_key) or {}).get("engine") or "krea2"
        manifest[key] = {"job": int(job_id), "hash": job["hash"], "engine": engine,
                         "submitted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "adopted_from": str(ledger.get("round") or Path(ledger_path).name)}
        adopted += 1
        print(f"  adopted {key} (job {job_id})")
    save_manifest(manifest)
    print(f"adopted {adopted}, skipped {skipped}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("list", "status", "submit", "harvest", "adopt"))
    parser.add_argument("group", nargs="?", default="all", choices=("all",) + GROUPS)
    parser.add_argument("--only", nargs="*", help="ids to act on")
    parser.add_argument("--engine", default=DEFAULT_ENGINE)
    parser.add_argument("--conductor", default=str(ROOT.parent / "conductor"))
    parser.add_argument("--ledger", help="adopt: a conductor art ledger YAML")
    parser.add_argument("--map", nargs="*", default=[], help="adopt: subject=render-key pairs")
    parser.add_argument("--style", help="list/status: an art style of art/styles.yaml instead of Classic")
    args = parser.parse_args()

    every = jobs()
    by_key = {j["key"]: j for j in every}
    rendered = load_rendered()
    current_keys = {j["key"] for j in every if is_current(j, rendered)}
    todo = [j for j in every if (args.group == "all" or j["group"] == args.group)
            and (not args.only or j["id"] in args.only) and j["key"] not in current_keys
            and j.get("style") == args.style]
    manifest = load_manifest()

    if args.action == "list":
        for j in todo:
            print(f"{j['key']}{'  (queued)' if j['key'] in manifest else ''}")
        print(f"{len(todo)} missing")
        return 0
    if args.action == "status":
        stale = sum(1 for j in todo if j["key"] in manifest and manifest[j["key"]]["hash"] != j["hash"])
        queued = sum(1 for j in todo if j["key"] in manifest) - stale
        every = [j for j in every if j.get("style") == args.style]
        print(f"{len(every)} renders: {len(every) - len(todo)} done, {queued} queued, "
              f"{stale} queued with an outdated prompt, {len(todo) - queued - stale} not submitted")
        return 0
    if args.action == "adopt":
        if not args.ledger:
            print("adopt needs --ledger", file=sys.stderr)
            return 2
        mapping = dict(pair.split("=", 1) for pair in args.map)
        adopt(args.ledger, mapping, by_key, manifest, rendered)
        return 0
    if not os.environ.get("KR_API_TOKEN"):
        print("KR_API_TOKEN is not set", file=sys.stderr)
        return 2
    core = core_module(args.conductor)
    if args.action == "submit":
        submit(todo, core, args.engine, manifest, current_keys)
    else:
        harvest(core, manifest, by_key, rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
