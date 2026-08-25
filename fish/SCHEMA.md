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
everything in it has to be monstrous (the Parlour Rustfish isn't) and reusable by Ruler
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
| `unlock_cost` | Coins to unlock. `0` means starting stock **or** reached only by evolution. |
| `behavior` | How it **moves**. One of the nine modes below. Drives the renderer; not a hardcoded switch. |
| `hue` | 0–360. Base hue for prototype rendering and art direction consistency. |
| `diet_role` | `prey` \| `predator` \| `neutral`. What it eats, and what eats it. |
| `school_role` | `shoaling` \| `solitary` \| `territorial`. How it relates to other fish. |
| `rivals` | List of slugs it squabbles with. Mutual and validated — see below. |
| `games` | List. Which games this creature appears in: `cthulhuquarium`, `ruler-hooked`. |

### `diet_role`, `school_role`, `rivals` — the social layer

These arrived with the 2026-08-25 bible merge and feed t-025's rivalry system and
t-027's feeding. `diet_role` is the authored half of rivalry: a predator and its prey
in one tank is a squabble waiting to happen, without anyone hand-listing the pair.

**`school_role` is not `behavior`.** It was called `school_role: school | solitary |
anchor` in the bible it came from, which collided with `behavior`'s own `school` and
`anchor` values and invited exactly the wrong reading. They are different axes: a
species can shoal *socially* while drifting *visually*. Renamed at the merge to
`shoaling | solitary | territorial` so the two can never be confused again.

**Rivalry is mutual and the validator enforces it.** A one-sided entry is nearly
always a typo — the tank cannot render A squabbling with B while B ignores A — so
`rivals` on one species requires the reciprocal entry on the other. Add the other
half; don't delete the first.

Keep authored rivalries scarce. Three exist (Lamplight Angler ↔ Chandelier Lion, both
competing light-bearers; Ledger Crab ↔ Bailiff Eel, a jurisdictional dispute; The
Committee ↔ The Auditor, which needs no explanation). Most rivalry should emerge from
`diet_role` and tank composition rather than from this list — a bible where every
species names a rival is one where rivalry means nothing.

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
- `evolution_kind:` — **required on anything carrying `evolves_to`.** Says *how* it is
  reached: `growth` (time and feeding), `breeding` (two parents, t-029), or `secret`
  (a hidden individual-stat roll, t-029). A chain link with no stated mechanism is a
  design hole that only shows up when someone tries to implement it.

Both halves are required and the validator enforces the pair, that the target is a higher
tier, and that a species reached by evolution carries `unlock_cost: 0` — it is not
purchasable, only arrived at. A dangling `evolves_to` would otherwise break the seed
script's chain silently rather than failing.

Evolution is a **gain**, never a replacement. Per the no-degradation rule, evolving must
not remove the base species from a player's collection: both count, both stay collected.
The base form is not consumed.

**Eight chains, twenty species.** The rustfish line is the flagship and the only one
running all five tiers — it is Silas's "magikarp to gyarados", and the merge gave it
the middle stages it was missing:

| line | stages |
|---|---|
| Rustfish | Parlour Rustfish → Elder Rustfish → The Unlidded Rustfish → The Founding Rustfish → **The Long Patience** |
| Angler | Lamplight Angler → The Seven Lights → The Foyer → **The Receiving Line** |
| Sardine | Harbor Sardine → Tithe Shoal → **The Single Fish** |
| Eel | Culvert Eel → The Testimony → **The Committee** |
| Bell | Drifting Bell → **The Reading Bell** |
| Catfish | Bottom Catfish → **Whiskered Elder** |
| Crawdad | Ditch Crawdad → **Marsh Sovereign** |
| Auditor | The Auditor → **The Reconciliation** |

**On the name.** This line was the Goldfish line until 2026-08-25, when Silas called
goldfish *"a terrible terrible name"* and offered Brassfish or Rustfish. Rustfish, because
brass is already the aquarium's fitting material — every set piece is brass — so spending
that word on the starter fish wastes a distinctive term on the least distinctive creature.
Rust is oxidation, which is time made visible, which is what a line ending in The Long
Patience is actually about. "Parlour Rustfish" is also the better joke: rust in a parlour
is *wrong*. The palette moved with the name (hue 32→22, gold→corroded rust) because a fish
named for oxidation rendered in bright gold is incoherent. `Carassius domesticus` stayed on
both ends of the line — the taxonomy still says domestic carp, which is the whole gag
against *"The ocean is a container."*

A line is worth more than the same number of standalone species: it gives the player a
reason to keep one fish rather than trade up, and it is where the collection stops
being a shopping list. Prefer extending a line to inventing an unrelated creature when
both would fill the same slot.

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

## The 2026-08-25 merge, and what it dropped

Two bibles were written against the same task by two sessions working in parallel,
sharing **zero** slugs. One lived here (23 species, one file each); the other lived in
`conductor/projects/cthulhuquarium/fish/` grouped by rarity (24 species), written there
because that session's GitHub access was scoped without this repo. Neither was wrong —
the cross-repo handoff protocol had no step for "check whether the canonical artifact
is already being written."

They were merged rather than one being picked, on Silas's call. This format won (it is
where every other document points, it is validated, and it carries the economy fields
the game actually needs); the other bible's **structure** won, which was the better
half of it: it was built as evolution lines running COMMON→MYTHIC, and that backbone is
now the bible's.

**Three of its species were dropped as duplicates, not as rejects:**

| dropped | because |
|---|---|
| `goldfish-common` | `parlour-rustfish` (then `parlour-goldfish`) is the same fish, better written, and already the line's base |
| `minnow-common` (Culvert Minnow) | `gutter-minnow` is the same fish |
| `lure-bearer-uncommon` | `lamplight-angler` is the same anglerfish; *"The light is not for you"* beats *"Carries its own light so visitors don't need one"* |

**One was renamed:** its "The Chandelier" collided with this bible's existing
`chandelier-lion` at the same rarity. It became **The Seven Lights**, which its own
field note had already handed us.

**Three lines were spliced rather than run in parallel**, because both bibles had
independently invented them: the rustfish line (this bible's base and terminus, the
other's two middle stages), the angler line, and the sardine/shoal line. Splicing kept
every distinct creature and produced longer chains than either bible had alone.

Everything else ported unchanged in substance — field notes kept verbatim where they
passed the tone rules, three tightened from three sentences to two, and every art
prompt rewritten from the rejected silhouette direction to the cartoon one.

## The target is 151

Silas, 2026-08-25: *"a real game should have at least 100 fish, but I think 151 is the
right number for…reasons :)"*

**The reason, stated plainly so nobody has to guess:** 151 is the number of original
Pokémon, Mew included. This is a monster-collecting game and that is the number a
monster-collecting game commits to. Do not round it to 150 for tidiness and do not
propose 200 for scope — the specific number is the point, and it is the reason evolution
lines matter more here than raw species count. A collection of 151 unrelated creatures is
a list; 151 across roughly forty lines is a Pokédex.

(This was originally recorded as an unexplained in-joke. Silas: *"Make it explicit. The
joke was for you, not for me to read ten days from now that each agent communicates they
refused to examine why we are committing to 151 monsters as instructed."* Fair — an
undocumented magic number that every reader is told not to question is exactly the thing
this file exists to prevent.)

**44 authored, 107 to go.** Rough shape to aim at, so batches do not all pile into the
same tier — treat as a target, not a quota to hit exactly:

| rarity | now | target |
|---|---|---|
| COMMON | 8 | ~32 |
| UNCOMMON | 11 | ~40 |
| RARE | 10 | ~36 |
| EPIC | 9 | ~26 |
| LEGENDARY | 4 | ~13 |
| MYTHIC | 2 | ~4 |

Two rules that matter more than the counts:

1. **Roughly two thirds of species should sit in an evolution line.** Currently 20 of
   44 do, which is too few. A line is the thing that makes a collection feel designed
   rather than accumulated, and it is cheaper to author well — the second and third
   stages come from asking "and then what happens to it", which is a far better prompt
   than a blank page.
2. **The weirdness ceiling still holds at every batch.** COMMON stays recognisably a
   fish. Authoring 107 species is exactly the pressure that pushes every new common
   toward being strange, and a bible whose bottom tier is all anomalies has spent the
   escalation it needs upstairs. If a batch's commons are getting weird, that is the
   signal to write more boring fish, not fewer.

## Concepts still to be authored

Silas's 2026-08-24 concept list is fully authored, and the 2026-08-25 merge brought the
bible to 44. This section is where the next batch lands before anyone writes files — a
line of intent is enough; the authoring pass turns it into a file.

Nothing is queued right now. The road to 151 is tracked as cthulhuquarium/t-037.

**A note on FUNCTIONAL species.** The Sexton cleans the glass, which makes it the first
creature valued for what it *does* rather than what it produces. That is a precedent to
handle carefully — a functional species risks becoming mandatory, and a mandatory
species is one less real choice. The rule that keeps it optional is that debris has
three viable answers (manual clicking, the debris set, and the snail), none strictly
best. Any future functional species needs the same treatment: give its job at least one
other route.

### Gaps worth filling

Observed while writing, rather than assigned by anyone. The first three were logged
before the merge; the merge fixed two of them outright, which is recorded here rather
than quietly deleted, because "what the merge actually bought us" is worth knowing.

- ~~Only one evolution chain exists.~~ **Fixed by the merge** — eight now, and the
  rustfish line runs all five tiers.
- ~~Tier 1 is thin: three species.~~ **Fixed by the merge** — eight, and five of them
  are recognisable fish, which is what tier 1 is for.
- **Still open: `tumble` and `surface` have one specimen each** (`the-quire` and
  `the-pleasant-island`). Two motions with a single user apiece read as one-offs rather
  than as a vocabulary. `cling` now has one too (`the-sexton`). Any batch of new
  species should spend some of its budget here rather than adding a fourth drifter.
- **New, from the merge: only 20 of 44 species sit in a line.** The target is roughly
  two thirds. Extending an existing line is usually better than starting a new one —
  three chains are still two stages long and want a third.
- **New: `prey` is underweighted** — 7 species against 22 predators. The food chain
  reads top-heavy, and t-025's rivalry system has little to work with at the bottom of
  it. Cheap to fix, since prey species are mostly small recognisable fish, which tier 1
  wants more of anyway.

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
