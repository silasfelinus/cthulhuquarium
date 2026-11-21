#!/usr/bin/env python3
"""
art_ledger.py -- one row per required asset, from prompt to the game (conductor
cthulhuquarium/t-093).

For every render the canon asks for (render_art.jobs(): sprites, heroes,
portraits and their floor variants, backgrounds, UI, plates, fish clips and
videos) it records:

  key          canon key, e.g. portraits/wilbur-stint-wince-f3
  prompt_hash  the hash of the prompt and size render_art uses
  job          the in-flight ArtJob id (art/jobs.yaml), if any
  raw          the raw render is on disk and was made from the current prompt
  built        the built file the sync copies (path, or missing)
  bundled      where kind_robots serves it (assets/images/cthulhuquarium/...),
               and whether that file is there when --kind-robots is given
  bound        what in the game uses it: a scene, a fish, a background entry,
               a UI name found in kind_robots, or nothing

Writes art/LEDGER.md (a summary and every row that is not finished) and
art/ledger.json (every row).

Usage:
    python3 scripts/art_ledger.py [--kind-robots ../kind_robots] [--check]

--check exits 1 when a required asset is unfinished or unbound, for CI or a
release review. Without it the ledger is informational.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_art  # noqa: E402

ROOT = render_art.ROOT

# group -> (built path for an id, kind_robots asset path for an id)
BUILT = {
    "sprites": (lambda i: ROOT / "sprites" / f"{i}.webp", lambda i: f"sprites/{i}.webp"),
    "clips": (lambda i: ROOT / "clips" / f"{i}.webp", lambda i: f"clips/{i}.webp"),
    "portraits": (lambda i: ROOT / "characters/portraits" / f"{i}.webp", lambda i: f"portraits/{i}.webp"),
    "heroes": (lambda i: ROOT / "characters/portraits/hero" / f"{i[:-5]}.webp",
               lambda i: f"cthulhuquarium-char-{i[:-5]}.webp"),
    "backgrounds": (lambda i: ROOT / "backgrounds/built" / f"{i}.webp", lambda i: f"backgrounds/{i}.webp"),
    "plates": (lambda i: ROOT / "story/built" / f"{i}.webp", lambda i: f"plates/{i}.webp"),
    "ui": (lambda i: ROOT / "ui/built" / f"{i}.webp", lambda i: f"ui/{i}.webp"),
    "videos": (lambda i: ROOT / "videos/built" / f"{i}.webp", lambda i: f"videos/{i}.webp"),
}


def bindings(kind_robots: Path | None) -> dict[str, set[str]]:
    """What the game uses, by group: ids found in the canon's own data, plus UI names in kind_robots."""
    scenes = yaml.safe_load((ROOT / "story/scenes.yaml").read_text())
    scene_map = scenes.get("scenes", scenes) if isinstance(scenes, dict) else {}
    plates: set[str] = set()
    poses: set[str] = set()
    text = (ROOT / "story/scenes.yaml").read_text()
    plates.update(re.findall(r"\b(screen-[a-z0-9-]+)\b", text))
    for speaker, pose in re.findall(r"speaker:\s*(\w+)\s*\n\s*pose:\s*([\w-]+)", text):
        poses.add(f"{'charlotte-fishmonger' if speaker == 'charlotte' else 'wilbur-stint'}-{pose}")
    fish = {yaml.safe_load(p.read_text())["slug"] for p in (ROOT / "fish").glob("*.yaml")}
    bgs = {b["key"] for b in yaml.safe_load((ROOT / "backgrounds/backgrounds.yaml").read_text())["backgrounds"]}
    ui: set[str] = set()
    if kind_robots:
        for path in list((kind_robots / "components/cthulhuquarium").glob("*.vue")) + list(
                (kind_robots / "utils").glob("cthulhuquarium*.ts")):
            ui.update(re.findall(r"""(?:name=|art:\s*)["']([a-z0-9-]+)["']""", path.read_text()))
        # Decorations and the collector are named by pattern (utils/cthulhuquariumDecorArt.ts):
        # `decor-<kind>` for every kind in the server's DECOR_CATALOG, and `swimmer-collector`.
        decor_art = kind_robots / "utils/cthulhuquariumDecorArt.ts"
        economy = kind_robots / "server/utils/aquariumEconomy.ts"
        if decor_art.exists() and economy.exists():
            catalog = economy.read_text()
            start = catalog.find("DECOR_CATALOG")
            kinds = re.findall(r"kind: '([a-z_]+)'", catalog[start:start + 4000]) if start >= 0 else []
            ui.update(f"decor-{kind.replace('_', '-')}" for kind in kinds)
            if "swimmer-collector" in decor_art.read_text():
                ui.add("swimmer-collector")
        # Plates the kind_robots code names directly (title card, endings shelf, finale).
        for path in list((kind_robots / "components/cthulhuquarium").glob("*.vue")) + list(
                (kind_robots / "utils").glob("cthulhuquarium*.ts")) + list(
                (kind_robots / "stores/helpers").glob("cthulhuquarium*.ts")):
            body = path.read_text()
            plates.update(re.findall(r"\b(screen-[a-z0-9-]+)\b", body))
            # Plates named by other keys ('upgrade-food', 'set-peace-ward').
            plates.update(re.findall(r"['\"]((?:upgrade|set)-[a-z0-9-]+)['\"]", body))
    videos = {v["key"] for v in yaml.safe_load((ROOT / "videos/videos.yaml").read_text())["videos"]}
    _ = scene_map
    return {"sprites": fish, "clips": fish, "portraits": poses, "heroes": {"charlotte-fishmonger-hero",
            "wilbur-stint-hero"}, "backgrounds": bgs, "plates": plates, "ui": ui, "videos": videos}


def bound_for(job: dict, binds: dict[str, set[str]]) -> str:
    group, ident = job["group"], job["id"]
    if group == "portraits":
        base = re.sub(r"-f\d$", "", ident)
        if base in binds["portraits"]:
            return "scene pose" + (f" (floor {ident[-1]})" if base != ident else "")
        return ""
    if group == "plates":
        return "scene or code" if ident in binds["plates"] else ""
    if group == "ui" and not binds["ui"]:
        return "unknown (no --kind-robots)"
    return {"sprites": "fish", "clips": "fish", "heroes": "intro", "backgrounds": "background catalog",
            "ui": "kind_robots UI", "videos": "videos.yaml"}[group] if ident in binds[group] else ""


def main() -> int:
    args = sys.argv[1:]
    kind_robots = Path(args[args.index("--kind-robots") + 1]).resolve() if "--kind-robots" in args else None
    check = "--check" in args
    # t-107: Classic by default; --style <id> reports a second art style's stills instead.
    style = args[args.index("--style") + 1] if "--style" in args else None
    out_md = ROOT / "art" / (f"LEDGER-{style}.md" if style else "LEDGER.md")
    out_json = ROOT / "art" / (f"ledger-{style}.json" if style else "ledger.json")
    rendered = render_art.load_rendered()
    manifest = render_art.load_manifest()
    binds = bindings(kind_robots)
    rows = []
    for job in render_art.jobs():
        if job.get("style") != style:
            continue
        built_path, bundled_rel = BUILT[job["group"]]
        built = built_path(job["id"])
        bundled = f"assets/images/cthulhuquarium/{bundled_rel(job['id'])}"
        if style:
            built = ROOT / "styles" / style / "built" / job["folder"] / f"{job['stem']}.webp"
            bundled = f"assets/images/cthulhuquarium/styles/{style}/{job['folder']}/{job['stem']}.webp"
        if job["group"] == "heroes" and not style:
            bundled = f"assets/images/cthulhuquarium/{bundled_rel(job['id'])}"
        entry = manifest.get(job["key"]) or {}
        row = {
            "key": job["key"],
            "group": job["group"],
            "prompt_hash": job["hash"],
            "job": entry.get("job") if isinstance(entry, dict) else entry,
            "raw": render_art.is_current(job, rendered),
            "built": str(built.relative_to(ROOT)) if built.exists() else None,
            "bundled": bundled,
            "bundled_present": (kind_robots / bundled).exists() if kind_robots else None,
            "bound": bound_for(job, binds) or None,
        }
        row["done"] = bool(row["raw"] and row["built"] and row["bound"] and row["bundled_present"] is not False)
        rows.append(row)

    out_json.write_text(json.dumps(rows, indent=1) + "\n")
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["group"], []).append(row)
    lines = [f"# Art ledger{f' ({style})' if style else ''}", "",
             "Generated by `scripts/art_ledger.py`" + (" against a local kind_robots" if kind_robots else "")
             + ". Every required render, from prompt to the game; `art/ledger.json` has every row.", "",
             "| Group | Required | Raw current | Built | Bundled | Bound | Done |", "|---|---|---|---|---|---|---|"]
    for group, items in groups.items():
        lines.append(f"| {group} | {len(items)} | {sum(r['raw'] for r in items)} | {sum(bool(r['built']) for r in items)} | "
                     f"{sum(bool(r['bundled_present']) for r in items) if kind_robots else '-'} | "
                     f"{sum(bool(r['bound']) for r in items)} | {sum(r['done'] for r in items)} |")
    total_done = sum(r["done"] for r in rows)
    lines += ["", f"**{total_done} of {len(rows)} done.**", ""]
    pending = [r for r in rows if not r["done"]]
    if pending:
        lines += ["## Not finished", "", "| Key | Job | Raw | Built | Bundled | Bound |", "|---|---|---|---|---|---|"]
        for r in pending:
            lines.append(f"| `{r['key']}` | {r['job'] or ''} | {'yes' if r['raw'] else 'no'} | "
                         f"{'yes' if r['built'] else 'no'} | "
                         f"{'-' if r['bundled_present'] is None else ('yes' if r['bundled_present'] else 'no')} | "
                         f"{r['bound'] or 'nothing'} |")
    out_md.write_text("\n".join(lines) + "\n")
    print(f"art ledger{f' ({style})' if style else ''}: {total_done} of {len(rows)} done; "
          f"{len(pending)} not finished -> {out_md.relative_to(ROOT)}")
    return 1 if (check and pending) else 0


if __name__ == "__main__":
    sys.exit(main())
