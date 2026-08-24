#!/usr/bin/env python3
"""Validate every fish/*.yaml against the bible schema in fish/SCHEMA.md.

The seed script (conductor cthulhuquarium/t-008) upserts these files into
kind_robots Character rows, so a malformed entry here becomes a malformed row
there. Catch it in the repo instead.

Exit codes: 0 = every species is valid, 1 = at least one is not.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FISH_DIR = ROOT / "fish"

RARITIES = {"COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", "MYTHIC"}
# Movement modes the renderer implements. Silas's 2026-08-24 concept list needed five
# more than the original three: a pack that moves as one, things that never move at all,
# something that sits at the surface, a hoverer, and a folded thing that tumbles.
BEHAVIORS = {
    "drift",    # ambles, gentle sine
    "dart",     # bursts and stops
    "lurk",     # holds position, moves when unobserved
    "school",   # moves as one body with its packmates
    "anchor",   # does not move; the tank moves past it
    "surface",  # sits at the waterline
    "hover",    # holds depth precisely, rotates in place
    "tumble",   # rotates through discrete orientations
    "cling",    # on the inside of the glass, not in the water
}
CLASSES = {
    "minnow", "angler", "drifter", "predator", "anomaly",
    "crustacean",  # shelled things
    "bloom",       # anemone/coral-shaped, sessile, usually armed
    "construct",   # geometric, folded, does not read as biological
    "colony",      # a single specimen that is visibly several
}
GAMES = {"cthulhuquarium", "ruler-hooked"}
STATS = ("charm", "empathy", "grace", "might", "wits")

REQUIRED = (
    "slug", "name", "species", "class", "field_note", "quirks", "alignment",
    "rarity", "stats", "tier", "size", "yield", "interval", "unlock_cost", "behavior",
    "hue", "games", "art_prompt",
)

# Optional. `evolves_to` names the slug this species becomes; `evolves_from` is its
# inverse. A species reached only by evolution is not purchasable, so it carries
# unlock_cost 0 and is expected to declare evolves_from.
OPTIONAL = ("evolves_to", "evolves_from")

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def check(path: Path, seen_slugs: dict[str, Path]) -> list[str]:
    problems: list[str] = []

    def bad(message: str) -> None:
        problems.append(f"{path.name}: {message}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        return [f"{path.name}: not parseable YAML — {error}"]

    if not isinstance(data, dict):
        return [f"{path.name}: top level must be a mapping"]

    for field in REQUIRED:
        if field not in data:
            bad(f"missing required field `{field}`")

    slug = data.get("slug", "")
    if slug and not SLUG_PATTERN.match(str(slug)):
        bad(f"slug `{slug}` must be lowercase kebab-case")
    if slug and slug != path.stem:
        bad(f"slug `{slug}` does not match filename `{path.stem}.yaml`")
    if slug in seen_slugs:
        bad(f"slug `{slug}` already defined in {seen_slugs[slug].name}")
    elif slug:
        seen_slugs[slug] = path

    if data.get("class") not in CLASSES and "class" in data:
        bad(f"class `{data['class']}` is not one of {sorted(CLASSES)}")
    if data.get("rarity") not in RARITIES and "rarity" in data:
        bad(f"rarity `{data['rarity']}` is not one of {sorted(RARITIES)}")
    if data.get("behavior") not in BEHAVIORS and "behavior" in data:
        bad(f"behavior `{data['behavior']}` is not one of {sorted(BEHAVIORS)}")

    stats = data.get("stats")
    if isinstance(stats, dict):
        for stat in STATS:
            if stat not in stats:
                bad(f"stats is missing `{stat}`")
            elif stats[stat] not in RARITIES:
                bad(f"stats.{stat} `{stats[stat]}` is not a Rarity value")
        for extra in set(stats) - set(STATS):
            bad(f"stats has unknown key `{extra}`")
    elif "stats" in data:
        bad("stats must be a mapping")

    games = data.get("games")
    if isinstance(games, list):
        if not games:
            bad("games must name at least one game")
        for game in games:
            if game not in GAMES:
                bad(f"games contains unknown game `{game}`")
    elif "games" in data:
        bad("games must be a list")

    for field, low, high in (
        ("tier", 1, 5),
        ("size", 1, 12),
        ("yield", 1, 10_000),
        ("interval", 1, 3_600),
        ("unlock_cost", 0, 10_000_000),
        ("hue", 0, 360),
    ):
        value = data.get(field)
        if field in data and (not isinstance(value, int) or isinstance(value, bool)):
            bad(f"{field} must be an integer")
        elif isinstance(value, int) and not low <= value <= high:
            bad(f"{field} `{value}` is outside {low}..{high}")

    note = str(data.get("field_note", "")).strip()
    if note:
        # The tone rules in SCHEMA.md are mostly a human judgement call; these two
        # are the ones a machine can hold the line on.
        if "!" in note:
            bad("field_note must not use an exclamation mark (see SCHEMA.md tone rules)")
        if len(re.findall(r"[.?]", note)) > 2:
            bad("field_note runs longer than two sentences")

    return problems


def check_evolution(files: list[Path]) -> list[str]:
    """Evolution links must resolve, and must agree with each other.

    A dangling `evolves_to` silently breaks the seed script's chain rather than
    failing, so it is caught here instead.
    """
    problems: list[str] = []
    loaded: dict[str, dict] = {}
    for path in files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and data.get("slug"):
            loaded[data["slug"]] = data

    for slug, data in sorted(loaded.items()):
        target = data.get("evolves_to")
        if target is not None:
            if target not in loaded:
                problems.append(f"{slug}.yaml: evolves_to `{target}` is not a known species")
            elif loaded[target].get("evolves_from") != slug:
                problems.append(
                    f"{slug}.yaml: evolves_to `{target}`, but {target}.yaml does not "
                    f"declare `evolves_from: {slug}`"
                )
            elif data.get("tier", 0) >= loaded[target].get("tier", 0):
                problems.append(
                    f"{slug}.yaml: evolves_to `{target}`, which must be a higher tier"
                )

        source = data.get("evolves_from")
        if source is not None:
            if source not in loaded:
                problems.append(f"{slug}.yaml: evolves_from `{source}` is not a known species")
            elif loaded[source].get("evolves_to") != slug:
                problems.append(
                    f"{slug}.yaml: evolves_from `{source}`, but {source}.yaml does not "
                    f"declare `evolves_to: {slug}`"
                )
            elif data.get("unlock_cost") != 0:
                problems.append(
                    f"{slug}.yaml: reached by evolution, so unlock_cost must be 0 "
                    f"(it is not purchasable)"
                )
    return problems


def main() -> int:
    files = sorted(FISH_DIR.glob("*.yaml"))
    if not files:
        print("no fish/*.yaml files found", file=sys.stderr)
        return 1

    seen_slugs: dict[str, Path] = {}
    problems: list[str] = []
    for path in files:
        problems.extend(check(path, seen_slugs))
    problems.extend(check_evolution(files))

    if problems:
        for problem in problems:
            print(f"✗ {problem}", file=sys.stderr)
        print(f"\n{len(problems)} problem(s) across {len(files)} species", file=sys.stderr)
        return 1

    parsed = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in files]
    shared = sum(1 for d in parsed if "ruler-hooked" in d["games"])
    chains = sum(1 for d in parsed if d.get("evolves_to"))
    total_size = sum(d["size"] for d in parsed)
    print(
        f"✓ {len(files)} species valid "
        f"({shared} shared with ruler-hooked, {chains} evolution chain(s), "
        f"{total_size} tank units to stock one of everything)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
