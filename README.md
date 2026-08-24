# Cthulhuquarium

**A darkly funny idle aquarium.** Click for coins, buy food, keep the occupants fed,
and find out what else is down there.

> It sits there, in the back of the curiosity shop.
> Where did it come from?
> Why can't I find any of these fish on Wikipedia?
> Where does this brackish food come from?
> It's all squishy, and smells like meat.
>
> But this is my aquarium, and it is mine.
>
> — the 2020 prototype's own landing copy, still correct

## What this repo is

**This repo is the data canon, not the game.** The game ships inside
[kind_robots](https://github.com/silasfelinus/kind_robots) at `/play/aquarium`, where
it gets accounts, persistence, the leaderboard, browsable public tanks, and the Comfy
art pipeline for free. Rebuilding all of that here would be rebuilding Kind Robots.

What lives here is everything that must outlive any one implementation:

| Path | What it holds |
|---|---|
| `fish/` | The **fish bible** — one YAML file per species. The canonical bestiary. |
| `fish/SCHEMA.md` | Field reference, the shared-creature contract, and the tone rules. |
| `economy/balance.yaml` | Every tunable number. Retuning the game is a commit to this file. |
| `scripts/validate_fish.py` | Schema validation. Run it before committing a species. |
| `prototype-2020/` | The original p5.js sketch, archived. It ran; it just never became a game. |

Keeping the bestiary in plain files means it survives a schema migration, an offline
build, and a future port that has no Kind Robots behind it. The seed script upserts
these files into kind_robots `Character` rows — the database is downstream of this
directory, never the reverse.

## The shared bestiary

Creatures carry a `games:` list. One tagged `[cthulhuquarium, ruler-hooked]` seeds into
the shared `abyssal-bestiary` Pack and **both games read the same record** — the
aquarium monster and the twisted lake catch in
[The Ruler is Hooked](https://github.com/silasfelinus/kind_robots) are literally the
same row. No sync layer, no duplicated art. See `fish/SCHEMA.md` for the rules
(the short version: neither game owns a shared creature, and neither may mutate it).

## Working on the bible

```bash
python3 scripts/validate_fish.py
```

Add a species by copying an existing `fish/*.yaml`, changing every field, and running
the validator. The filename must match the `slug`. Slugs are permanent — renaming one
orphans its database row and anything in a player's save that references it.

Read the tone rules in `fish/SCHEMA.md` before writing a `field_note`. The register is
a museum placard written by someone who is not telling you everything: one sentence,
dry, no exclamation marks, and never explain the joke.

## Status

Planned and tracked in Conductor as `cthulhuquarium` — roadmap, milestones, and the
design brief live at `projects/cthulhuquarium/` in
[silasfelinus/conductor](https://github.com/silasfelinus/conductor).

Formerly *Memequarium*, started 2020.
