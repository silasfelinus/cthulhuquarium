# The 2020 prototype

`prototype-2020/` is the original Memequarium sketch, preserved as it was found on
2026-08-24 when the project was picked back up. Nothing in it is wired into the current
game and nothing should be — it is kept because it is where the tone was first written
down, and because it works.

## What it is

A framework-free p5.js-style sketch (`prototype-2020/js/aquarium.js`, ~1 file) plus a
static landing page. It generates fish procedurally: random body/tail colors biased
toward blue, random body dimensions scaled by a size class (small/mid/big), random
speed and starting position, and a bubble system. `makeFish(count, size)` returns an
array of positional arrays; there are arrays for `bubbles`, `fishFood`, and
`hungryFish`, so feeding was clearly the intended next step and never arrived.

Header comment, verbatim:

```
//Virtual Aquarium
//By Silas Knight
//v0.01 Added bubbles
```

## What was worth keeping

Two things, both carried forward into the current design:

1. **The landing copy.** The curiosity-shop framing in `prototype-2020/index.html` —
   "Why can't I find any of these fish on wikipedia?", "It's all squishy, and smells
   like meat", "But this is my aquarium, and it is mine" — is the tone the whole
   project is now built around. It is quoted in the README and in the design brief.
2. **The navigation the sketch never had a game behind.** Its nav bar lists Home,
   Aquarium, Fish Shop, Collection, Medals. That is, near enough, the shipping feature
   list: tank, shop, bestiary, achievements. The 2020 version knew the shape.

## What was not

Procedural random-color fish. The current direction is a hand-authored bestiary of
distinct, named creatures with field notes and rarity — collection is the point, and
you cannot collect a thing that is randomly generated each load. The generative
approach is why the 2020 build had no reason to keep playing it.
