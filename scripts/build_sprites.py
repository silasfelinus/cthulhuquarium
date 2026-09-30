#!/usr/bin/env python3
"""Turn raw sprite renders into the tank's cut-out sprites and their animation.

    raw render (sprites/raw/<slug>.webp, flat studio backdrop)
      -> cut-out: backdrop removed, alpha cleaned, trimmed, facing right
      -> sprites/<slug>.webp            static, transparent, 320px on the long edge
      -> sprites/anim/<slug>.webp       animated preview, looping, same motion the tank plays

The motion is the species' own `sprite.motion` (fish/SCHEMA.md "Sprites"). The
deformation below is the canonical definition of each motion: the kind_robots
swim canvas plays the same maths live on the static sprite (strip-slicing, so
nothing but the static file has to ship), and the animated preview here is the
same function baked to frames, so the listing and the tank never disagree.

    python3 scripts/build_sprites.py                 # every species with a raw render
    python3 scripts/build_sprites.py drifting-bell   # just these
    python3 scripts/build_sprites.py --anim-only     # re-bake animation from existing cut-outs

Needs: pillow, numpy, rembg (pip install "rembg[cpu]"); the isnet model downloads once.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FISH = ROOT / "fish"
RAW = ROOT / "sprites" / "raw"
OUT = ROOT / "sprites"
ANIM = ROOT / "sprites" / "anim"

LONG_EDGE = 320
ANIM_LONG_EDGE = 200  # previews only; the tank animates the 320px static live
FRAMES = 12

# Amplitudes are fractions of the sprite's own size, so a 40px shrimp and a
# 300px leviathan move in proportion. Keep in sync with MOTIONS in kind_robots
# utils/cthulhuquariumSprites.ts -- same numbers, same shapes.
MOTIONS = {
    # fish: the body is still up front and the tail does the work.
    "tailbeat": {"axis": "x", "amp": 0.055, "waves": 0.6, "weight": "tail", "period": 900},
    # eels, worms, anything long: one travelling wave down the whole body.
    "undulate": {"axis": "x", "amp": 0.07, "waves": 1.3, "weight": "even", "period": 1400},
    # rays, nudibranchs, frilled things: a fine, fast ripple at small amplitude.
    "ripple": {"axis": "x", "amp": 0.03, "waves": 2.2, "weight": "even", "period": 800},
    # jellies and bells: the bell squeezes, the trailing parts follow late.
    "pulse": {"axis": "y", "amp": 0.05, "waves": 0.9, "weight": "trail", "squash": 0.06, "period": 1800},
    # rooted or stalked things: base still, the top sways.
    "sway": {"axis": "y", "amp": 0.05, "waves": 0.4, "weight": "crown", "period": 3200},
    # crabs, snails, limpets, sessile things: a breath and a shuffle.
    "breathe": {"axis": "none", "squash": 0.03, "period": 3600},
    # rigid things that tumble: the renderer rotates them; the sprite itself holds still.
    "rigid": {"axis": "none", "squash": 0.0, "period": 1000},
}


def load_species(slugs: list[str] | None) -> list[dict]:
    out = []
    for path in sorted(FISH.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if slugs and data["slug"] not in slugs:
            continue
        out.append(data)
    return out


def cutout(raw: Path, session) -> Image.Image:
    cut = cutout_image(Image.open(raw), session)
    scale = LONG_EDGE / max(cut.size)
    cut = cut.resize((max(1, round(cut.width * scale)), max(1, round(cut.height * scale))), Image.LANCZOS)
    return with_rim(cut)


# A faint pale rim, so a black-bodied creature (every scraperboard species, the
# ink rubbings) still reads against dark water at 60px -- SCHEMA.md sprite rule 5.
# Light enough that a pale creature just looks slightly lit from behind.
RIM_PX = 2
RIM_RGBA = (225, 240, 232, 110)


def with_rim(sprite: Image.Image) -> Image.Image:
    from PIL import ImageFilter

    pad = RIM_PX + 1
    canvas = Image.new("RGBA", (sprite.width + 2 * pad, sprite.height + 2 * pad))
    canvas.paste(sprite, (pad, pad))
    alpha = canvas.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    grown = alpha.filter(ImageFilter.MaxFilter(RIM_PX * 2 + 1)).filter(ImageFilter.GaussianBlur(0.8))
    rim = Image.new("RGBA", canvas.size, RIM_RGBA[:3] + (0,))
    rim.putalpha(grown.point(lambda v: v * RIM_RGBA[3] // 255))
    rim.alpha_composite(canvas)
    return rim


def cutout_image(image: Image.Image, session) -> Image.Image:
    """Remove the flat backdrop, clean the matte, trim to the subject."""
    from rembg import remove

    cut = remove(image.convert("RGB"), session=session, post_process_mask=True)
    rgba = np.asarray(cut).astype(np.float32)
    alpha = rgba[..., 3] / 255.0
    # Soft-matte cleanup: kill the faint haze rembg leaves on a flat backdrop,
    # keep the anti-aliased edge.
    alpha = np.clip((alpha - 0.08) / 0.84, 0, 1)
    rgba[..., 3] = alpha * 255
    cut = Image.fromarray(rgba.astype(np.uint8), "RGBA")
    box = cut.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    if not box:
        raise RuntimeError("cut-out is empty")
    return cut.crop(box)


def _weight(profile: str, n: int) -> np.ndarray:
    t = np.linspace(0.0, 1.0, n)
    if profile == "tail":  # sprite faces right: tail is at x=0
        return (1 - t) ** 2
    if profile == "trail":  # bell at the top, trailing parts below
        return t ** 1.5
    if profile == "crown":  # rooted at the bottom
        return (1 - t) ** 1.5
    return np.full(n, 0.6)


def deform(src: np.ndarray, motion: str, phase: float) -> np.ndarray:
    """One frame of `motion` at `phase` (0..1). src is HxWx4 float, padded."""
    spec = MOTIONS.get(motion, MOTIONS["tailbeat"])
    h, w = src.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    squash = spec.get("squash", 0.0)
    if squash:
        s = 1 + squash * math.sin(2 * math.pi * phase)
        cy, cx = h / 2, w / 2
        ys = cy + (ys - cy) / s
        xs = cx + (xs - cx) * s if spec["axis"] != "y" else xs
    if spec["axis"] == "x":
        weight = _weight(spec["weight"], w)
        amp = spec["amp"] * max(h, w)
        shift = amp * weight * np.sin(2 * math.pi * (phase - spec["waves"] * np.linspace(0, 1, w)[::-1]))
        ys = ys - shift[None, :]
    elif spec["axis"] == "y":
        weight = _weight(spec["weight"], h)
        amp = spec["amp"] * max(h, w)
        shift = amp * weight * np.sin(2 * math.pi * (phase - spec["waves"] * np.linspace(0, 1, h)))
        xs = xs - shift[:, None]
    return _sample(src, ys, xs)


def _sample(src: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
    h, w = src.shape[:2]
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    fx = (xs - x0)[..., None]
    fy = (ys - y0)[..., None]
    out = np.zeros_like(src)
    for dy, dx, wgt in ((0, 0, (1 - fy) * (1 - fx)), (0, 1, (1 - fy) * fx), (1, 0, fy * (1 - fx)), (1, 1, fy * fx)):
        yy, xx = y0 + dy, x0 + dx
        ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
        px = np.zeros_like(src)
        px[ok] = src[yy[ok], xx[ok]]
        out += px * wgt
    return out


def animate(static: Image.Image, motion: str) -> list[Image.Image]:
    pad = round(max(static.size) * 0.12)
    canvas = Image.new("RGBA", (static.width + 2 * pad, static.height + 2 * pad))
    canvas.paste(static, (pad, pad))
    # premultiply so interpolation never drags backdrop colour into the edge
    src = np.asarray(canvas).astype(np.float32)
    src[..., :3] *= src[..., 3:4] / 255.0
    frames = []
    for i in range(FRAMES):
        f = deform(src, motion, i / FRAMES)
        a = f[..., 3:4]
        f[..., :3] = np.where(a > 0, f[..., :3] * 255.0 / np.maximum(a, 1e-3), 0)
        frames.append(Image.fromarray(np.clip(f, 0, 255).astype(np.uint8), "RGBA"))
    return frames


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slugs", nargs="*")
    parser.add_argument("--anim-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="rebuild cut-outs that already exist")
    args = parser.parse_args()

    ANIM.mkdir(parents=True, exist_ok=True)
    session = None
    built = missing = 0
    for fish in load_species(args.slugs or None):
        slug = fish["slug"]
        motion = (fish.get("sprite") or {}).get("motion", "tailbeat")
        static_path = OUT / f"{slug}.webp"
        raw = RAW / f"{slug}.webp"
        if not args.anim_only and (args.force or not static_path.exists()):
            if not raw.exists():
                missing += 1
                continue
            if session is None:
                from rembg import new_session

                session = new_session("isnet-general-use")
            cutout(raw, session).save(static_path, "WEBP", quality=88, method=6)
        if not static_path.exists():
            missing += 1
            continue
        static = Image.open(static_path).convert("RGBA")
        scale = ANIM_LONG_EDGE / max(static.size)
        static = static.resize((max(1, round(static.width * scale)), max(1, round(static.height * scale))), Image.LANCZOS)
        frames = animate(static, motion)
        frames[0].save(
            ANIM / f"{slug}.webp", "WEBP", save_all=True, append_images=frames[1:],
            duration=round(MOTIONS.get(motion, MOTIONS['tailbeat'])['period'] / FRAMES), loop=0, quality=80, method=6,
        )
        built += 1
        print(f"built {slug} ({motion})")
    print(f"{built} built, {missing} without a raw render yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
