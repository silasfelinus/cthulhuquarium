#!/usr/bin/env python3
"""Rewrite every fish's sprite.prompt as subject + the house sprite style (t-099).

    python3 scripts/apply_sprite_subjects.py SUBJECTS.yaml

SUBJECTS.yaml maps slug -> [K|R, "subject"] (R = a new design for that species).
The shared clause and backdrop come from art/sprite-style.yaml, so the whole tank is
painted in one medium (ART-DIRECTION.md "The tank register"). Only the sprite block's
`prompt:` is rewritten; motion, faces and mass are kept, except `faces`, which is
dropped because the new prompt asks for a right-facing render (review re-adds it).
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

import yaml

# Where each book plate's medium clause starts in art_prompt. A redesign (R) swaps the
# subject in front of it and keeps the lineage, so the Ichthyonomicon card shows the
# same creature the tank does, still in its plate's medium.
PLATE_OPENERS = {
    "scraperboard": r", scraperboard illustration", "gosse": r", hand-? ?coloured lithograph",
    "gyotaku": r", gyotaku", "trade-card": r", chromolithograph", "riso": r", risograph print",
    "haeckel": r", ornamental natural history plate", "blaschka": r", lampworked glass",
    "moulage": r", (?:a )?(?:wet )?(?:anatomical )?(?:preserved|specimen)",
}

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    subjects = yaml.safe_load(Path(sys.argv[1]).read_text())
    style = yaml.safe_load((ROOT / "art/sprite-style.yaml").read_text())
    changed = 0
    for slug, (kind, subject) in subjects.items():
        path = ROOT / "fish" / f"{slug}.yaml"
        text = path.read_text()
        fish = yaml.safe_load(text)
        mass = (fish.get("sprite") or {}).get("mass")
        framing = style["framing_mass"] if mass else style["framing"]
        prompt = f"{subject}, {style['clause']}, {framing}"
        block = textwrap.fill(prompt, width=88, initial_indent="    ", subsequent_indent="    ")
        new, n = re.subn(r"(^sprite:\n(?:  (?!prompt:).*\n)*)  prompt: >\n(?:    .*\n)+",
                         lambda m: m.group(1) + "  prompt: >\n" + block + "\n", text, count=1, flags=re.M)
        if n != 1:
            print(f"!! {slug}: sprite.prompt block not found", file=sys.stderr)
            return 1
        new = re.sub(r"(^sprite:\n(?:  .*\n)*?)  faces: (?:left|right)\n", r"\1", new, count=1, flags=re.M)
        if kind == "R":
            card = " ".join(fish["art_prompt"].split())
            opener = re.search(PLATE_OPENERS[fish["plate"]], card)
            card = subject + card[opener.start():]
            card_block = textwrap.fill(card, width=90, initial_indent="  ", subsequent_indent="  ")
            new, n = re.subn(r"^art_prompt: >\n(?:  .*\n)+", "art_prompt: >\n" + card_block.replace("\\", "\\\\") + "\n",
                             new, count=1, flags=re.M)
            if n != 1:
                print(f"!! {slug}: art_prompt block not found", file=sys.stderr)
                return 1
            new = re.sub(r"(^sprite:\n)", r"\1  redesigned: '2026-11-05'\n", new, count=1, flags=re.M) \
                if "redesigned:" not in new else new
        if new != text:
            path.write_text(new)
            changed += 1
    print(f"rewrote {changed} sprite prompts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
