# Fish bible schema

One YAML file per species: `fish/<slug>.yaml`. This directory is the **canonical
source of truth** for every creature in Cthulhuquarium and for the twisted-ecosystem
catches in Ruler is Hooked. The database is downstream of these files, never the
other way around.

Validate before committing:

```bash
python3 scripts/validate_fish.py
```

## Why YAML and not the database

The bestiary has to survive a schema migration, an offline build, and a future port
that has no Kind Robots behind it. Plain files are diffable, reviewable in a PR, and
editable by a human who is not running a server. The seed script (conductor
cthulhuquarium/t-008) reads these files and upserts rows in kind_robots' bestiary table
keyed on `slug`; re-running it after an edit updates rows rather than duplicating them.

## The bestiary table is not `Character` — corrected 2026-08-25

This document previously said every field had to map onto a kind_robots `Character`
column, and the seed script wrote `Character` rows. **That was wrong**, and Silas
overturned it: *"why do our characters have size? These monsters are not meant to be
added as characters. characters are our website's chattable personalities and npcs for
story based games. the monsters are something new."*

The mistake was reusing `Character` because its **columns** fit, when what decides a
shared model is what it **means**. `Character` is the chattable-personality table the
rest of Kind Robots reads — Charlotte and Wilbur belong in it; a fish does not. The
cost was not theoretical: fish needed a capacity weight, so a `size` column was added to
`Character`, and that migration shipped to the client without reaching the database,
500-ing every `prisma.character.findUnique()` in production.

Creatures get their own table. Working name **`Creature`** — broad enough that not
everything in it has to be monstrous (the Parlour Goldfish isn't) and reusable by Ruler
is Hooked. Conductor **cthulhuquarium/t-035** owns building it and settles the final
name; `Monster` is the standing alternative. Nothing about the YAML shape below changes
— the same fields, the same six `Rarity` stats, the same `games` list. Only the table
they land in changes, and `size` finally lives somewhere it belongs.

The rule worth keeping: **shared models are shared because of what they mean, not
because their columns happen to line up.**

## Field reference

Every field maps onto a column of the bestiary table. That constraint is deliberate — a
field with nowhere to land is a field the seed script has to drop. Column names below
are the ones inherited from the `Character` shape and are what t-035 carries over.

| Field | Column | Notes |
|---|---|---|
| `slug` | `slug` | Unique, kebab-case, stable forever. Renaming a slug orphans a row. |
| `name` | `name` | Display name. |
| `species` | `species` | The taxonomic-sounding lie. |
| `class` | `class` | Broad family: `minnow`, `angler`, `drifter`, `predator`, `anomaly`. |
| `field_note` | `backstory` | One line, museum-placard register. See the tone rules below. |
| `quirks` | `quirks` | Behavioral oddities, free text. |
| `alignment` | `alignment` | Flavor only; no mechanical effect. |
| `rarity` | `luck` | `COMMON` \| `UNCOMMON` \| `RARE` \| `EPIC` \| `LEGENDARY` \| `MYTHIC`. |
| `stats.charm` etc. | `charm`, `empathy`, `grace`, `might`, `wits` | Same `Rarity` enum. |
| `art_prompt` | `artPrompt` | Generation prompt. Silhouette-forward — see below. |
| `theme` | `theme` | Optional daisyUI theme for the card. |

## Game-facing fields

These have no equivalent in the `Character` shape the columns above came from. Under
`Creature` they are real columns rather than a payload blob — which is the whole point
of the correction above: `size` is a property of a creature, and it never should have
been bolted onto `Character` to make it fit.

| Field | Meaning |
|---|---|
| `tier` | 1–5. Roughly how deep into the game it appears. |
| `size` | 1–12 tank units. Fish capacity is measured by total size, not by count. |
| `yield` | Coins produced per drop cycle when fed. |
| `interval` | Seconds between drops. |
| `unlock_cost` | Coins to unlock. `0` means starting stock. |
| `behavior` | `drift` \| `dart` \| `lurk`. Drives the renderer; not a hardcoded switch. |
| `hue` | 0–360. Base hue for prototype rendering and art direction consistency. |
| `games` | List. Which games this creature appears in: `cthulhuquarium`, `ruler-hooked`. |

## Size, and why capacity is weighed rather than counted

Decided 2026-08-24. Set slots are **counted** (start with three, buy up to about five).
Fish capacity is **weighed**: a tank holds a total number of size units, not a number of
fish. Silas: *"fish could be say different sizes and an aquarium can accommodate more or
less."*

That asymmetry is deliberate. Counted set slots stay easy to hold in your head; weighed
fish capacity turns stocking into a **packing problem** — six small fish or one enormous
one — which is a far more interesting decision than "pick six." It also gives the big
tier-5 creatures a cost beyond their price. The Long Patience is size 10 and should eat
most of a tank.

Assign `size` from what the creature physically **is**, not mechanically from its tier. A
shoal is many small bodies moving together (Tithe Shoal is 4). An island is enormous
regardless of where it sits in the progression (The Pleasant Island is 9). A snail on the
glass takes almost nothing (The Sexton is 1).

Stocking one of every current species would take **89 units**, which is the number a tank
progression should be designed against — the largest tank should stay well under it, or
the packing problem stops being a problem.

## Movement modes

`behavior` is read by the renderer, so adding a value here means adding a motion to the
canvas. Eight exist:

| Value | Motion |
|---|---|
| `drift` | Ambles on a gentle sine. The default. |
| `dart` | Bursts, then stops dead. |
| `lurk` | Holds position; moves when unobserved. |
| `school` | Moves as one body with its packmates, never independently. |
| `anchor` | Does not move at all. The tank moves past it. |
| `surface` | Sits at the waterline, mostly above it. |
| `hover` | Holds depth precisely and rotates in place. |
| `tumble` | Rotates through discrete orientations rather than turning smoothly. |
| `cling` | On the inside of the glass rather than in the water. Renders in front of everything. |

`cling` is the one that is not just a motion: a clinging species renders in front of the
whole tank rather than within it, so it needs its own draw pass, and it is the first
species type the player looks *at* the glass to see rather than through it.

Do not invent a tenth without adding the motion to the renderer in the same change — a
species whose behavior has no implementation silently falls back to drifting, which is
worse than being obviously broken.

## Evolution chains

Two optional fields, added for Silas's "magikarp to gyarados" concept: a most basic fish
that becomes a complete killer.

- `evolves_to: <slug>` — the species this one becomes.
- `evolves_from: <slug>` — the inverse, on the target.

Both halves are required and the validator enforces the pair, that the target is a higher
tier, and that a species reached by evolution carries `unlock_cost: 0` — it is not
purchasable, only arrived at. A dangling `evolves_to` would otherwise break the seed
script's chain silently rather than failing.

Evolution is a **gain**, never a replacement. Per the no-degradation rule, evolving must
not remove the base species from a player's collection: both count, both stay collected.
The base form is not consumed.

Currently one chain: `parlour-goldfish` → `the-long-patience`.

## The `games` field is the whole sharing mechanism

A creature tagged `[cthulhuquarium, ruler-hooked]` is read by both games. There is no
sync layer, no duplicated art, and no second catalog — Silas's "we can have appropriate
ones appear in both games" costs exactly one list field.

This survived the move off `Character` unchanged. Sharing was never about which table
the row lived in; it was always this list. Ruler is Hooked keeps `Character` for its
actual characters — only its fish move.

Rules for shared creatures:

- A shared creature is **not one game's property**. Neither game may mutate the row;
  both read it. Per-game state (hunger, placement, whether it has been caught) belongs
  in that game's own tables.
- Ruler is Hooked's dark-ecosystem branch should query `games` contains `ruler-hooked`.
  A creature that only makes sense in a tank stays `[cthulhuquarium]`.
- Removing a creature from the bible sets `isActive: false` on its row. Never DELETE —
  someone's save may reference it.

## Tone rules for `field_note`

The register is a museum placard written by someone who is not telling you everything.

- One sentence, occasionally two. Never three.
- Dry and understated. The humor is in what is omitted, not in a punchline.
- Present tense, clinical vocabulary, faint concern.
- Never explain the joke. Never use an exclamation mark.
- Good: *"The light is not for you. It has never been for you."*
- Bad: *"This wacky fish has a glowing lure that tricks its prey — watch out!"*

## How weird a species may be

Decided by Silas, 2026-08-24: the ceiling is **clearly-not-a-fish**.

Common and uncommon tiers stay recognizable — a fish, but wrong. Rare and above may
escalate into things that only *resemble* fish: too many joints, mostly eye, something
wearing a fish. The restraint downstairs is what makes the escalation upstairs land, so
do not spend the ceiling early.

Two constraints hold at every tier:

- **Unsettling, never gross-out.** The tone is dread and dry humor, not viscera.
- **Still a legible silhouette.** A shape nobody can read at 256px is a failed design
  regardless of how strange it is. If a concept only works in detail, it does not work.

Nothing in the bestiary dies, and nothing the player collects is ever taken away —
that is a game rule, not a flavor note. A species may be unsettling about death; the
mechanics never enact it on the player's tank.

## The food is alive

Also decided 2026-08-24: fish food is **live and wriggling**, not pellets. Silas: *"i
guess in that sense, something will die, but that's just because our fish food should be
wriggling."*

This matters to the bible because it is the one place the game's cheerful cruelty is
mechanical rather than written. Nothing is ever taken from the player; the only cost in
the game is one they pay to something else, by the handful, without comment. Keep it
that way — the food is never described sympathetically, and it is never gore. It squirms
on the way down and stops when eaten.

Feed creatures are not bestiary species. They have no `slug`, no field note, and are
never collectible. If a future task needs them catalogued, they get their own file, not
a `fish/` entry.

## Concepts still to be authored

Silas's 2026-08-24 concept list is fully authored — all fifteen landed, which took the
bible from 7 to 22 species and past the 20-species MVP bar. He flagged the list itself as
open ("more to be developed"), so this section is where the next batch lands before
anyone writes files.

Nothing is queued right now. When adding concepts here, a line of intent is enough — the
authoring pass turns it into a file. A note on FUNCTIONAL species, now that one exists: The Sexton cleans the glass, which
makes it the first creature valued for what it does rather than what it produces. That is
a precedent to handle carefully — a functional species risks becoming mandatory, and a
mandatory species is one less real choice. The rule that keeps it optional is that debris
has three viable answers (manual clicking, the debris set, and the snail), none strictly
best. Any future functional species needs the same treatment: give its job at least one
other route.

Gaps worth filling, observed while writing the
current set rather than assigned by anyone:

- Nothing yet uses `tumble` except `the-quire`, and nothing uses `surface` except
  `the-pleasant-island`. Two motions with one specimen each read as one-offs rather than
  as a vocabulary.
- Tier 1 is thin: three species, and two of them are the goldfish line's base form and a
  minnow. The early game is where the tone gets established and it currently has the
  least to look at.
- Only one evolution chain exists. A second would confirm the mechanic is a system rather
  than a special case.

## Art prompt rules

Read `ART-PROMPTS.md` in the conductor repo before writing one. The short version, both
learned the hard way:

1. **No conditionals.** Krea 2 has no instruction-following layer; "include X only when
   the scene calls for it" gets painted literally. State what is in the frame, once.
2. **Lead with the physical subject** — material, shape, scale, framing, light — before
   any statement of what the creature means.
3. **Say what it is NOT.** Both engines default hard toward nature photography for
   anything fish-shaped. Without an explicit negative they will hand back a competent
   photo of a real animal.

For this bestiary specifically, corrected 2026-08-25: **vibrant saturated cartoon
creature illustration** — thick confident outlines, exaggerated asymmetric anatomy,
glossy wet highlights, playful macabre storybook monster, bold colour, dark water
behind it, explicitly *not photorealistic, not a nature photograph*, unpeopled frame,
no text.

This replaces the silhouette-forward direction this section carried until 2026-08-25.
Silhouettes were chosen on the theory that they would survive generation inconsistency
better than detailed creature art. The first real batch disproved it — Silas, on ten
returned renders: *"they almost all look like real animals, not misshapen horrors from
the deep with a cartoonish playfulness... I want creative, colorful, and vibrant monster
fish and backgrounds."* A dark, low-detail, rim-lit prompt reads to the model as
*underwater photograph*, so restraint in the prompt bought realism, which is the one
thing this bestiary cannot be. Saturated cartoon language pushes the other way and gives
the model no photographic reading to fall back on.

Krea 2 is the preferred engine here — its bias toward bold colour and stylisation is an
advantage for this project rather than something to correct for.

A species that will not generate consistently gets redesigned, not shipped as an
outlier.
