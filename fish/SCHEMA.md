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

Stocking one of every current species would take **524 units** across all 151 — which is
not the number a tank progression should be designed against, because nobody stocks one
of everything at once. Design against a *representative* tank instead: the largest tank
should hold a satisfying handful of the big ones or a crowd of the small ones, and stay
far below the collection total, or the packing problem stops being a problem.

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

**One exception, decided 2026-08-25: eggs.** Silas: *"an egg should be consumed. it isn't
technically against my rules, as it evolves into another Monster of that size."* An egg
bought from the shop (cthulhuquarium/t-041) **is** consumed when it hatches, unlike every
other base form. The rule it looks like it breaks is the paragraph directly above, and the
two reasons it does not are worth stating so nobody reverts this later:

1. **Size is conserved.** N tank units of egg become at most N units of Monster. The
   player's holdings transform rather than diminish — which is Silas's own argument, and
   it is the same conservation the t-041 size rule already relies on.
2. **The record survives.** Nothing the player *collects* is lost, because what is
   collected is the entry, not the object. That is precisely the job t-031 gives the
   Ichthyonomicon — "the record that makes everything else safe" is not a decorative
   subtitle.

Two things follow, and both bind whoever implements it:

- **The hatch must be shown, never silent.** The difference between *my egg became a fish*
  and *my egg vanished* is entirely presentation, and only the first is the rule being
  honoured rather than merely argued.
- **An egg is an ITEM, not a bestiary species.** It is evolution-*shaped* in the fiction
  and in the argument above, but it is **not** an `evolves_to` edge. That field is
  single-valued and validated — target must exist, be a higher tier, and declare the
  reciprocal `evolves_from` — while an egg resolves to one of a pool of dozens, which the
  edge cannot express. Modelling eggs as species would also take the bestiary to 157, and
  151 was deliberate. Eggs follow the set-piece precedent: a thing you buy that is not a
  creature, sharing the set pieces' trade-catalogue art lineage.

**Fifty-five lines, 147 of 151 species.** Two run the full COMMON→MYTHIC span: the
rustfish line, which is Silas's "magikarp to gyarados" and the one the bible is built
around, and the sump line that batch 2 completed. (This section previously called the
rustfish line *the only one* running all five tiers; that stopped being true one batch
before anyone updated the sentence.) The eight the merge produced, which are still the
spine of the bestiary:

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

**151 authored. The target is met.** The shape it landed on, against the targets this
table carried from the start:

| rarity | final | target |
|---|---|---|
| COMMON | 32 | ~32 |
| UNCOMMON | 40 | ~40 |
| RARE | 36 | ~36 |
| EPIC | 26 | ~26 |
| LEGENDARY | 13 | ~13 |
| MYTHIC | 4 | ~4 |

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

Silas's 2026-08-24 concept list is fully authored, the 2026-08-25 merge brought the bible
to 44, and batches 1-3 carried it to **151**. The road to 151 (cthulhuquarium/t-037) is
closed.

Nothing is queued. This section stays as the place a future batch lands before anyone
writes files — a line of intent is enough; the authoring pass turns it into a file. Note
that **151 is a target, not a cap**: it is the number this bible committed to, and going
past it needs a reason rather than momentum. The next work on the bestiary is more likely
to be balance (see the two open items above) or seeding it into the Monster table
(t-008) than more species.

**A note on FUNCTIONAL species.** The Sexton cleans the glass, which makes it the first
creature valued for what it *does* rather than what it produces. That is a precedent to
handle carefully — a functional species risks becoming mandatory, and a mandatory
species is one less real choice. The rule that keeps it optional is that debris has
three viable answers (manual clicking, the debris set, and the snail), none strictly
best. Any future functional species needs the same treatment: give its job at least one
other route.

### Gaps worth filling

A running ledger with what each batch actually moved, because "we fixed that" is only
credible with a number next to it.

- ~~Only one evolution chain exists.~~ **Fixed by the merge** — and 21 by batch 2.
- ~~Tier 1 is thin.~~ **Fixed**: 17 commons, most of them recognisable fish.
- ~~`tumble`, `surface` and `cling` have one specimen each.~~ **Fixed by batch 1** —
  cling 1→5, surface 1→3, tumble 1→2. Tumble is still thin at two.
- ~~`prey` underweighted, 7 against 22 predators.~~ **Fixed by batch 1** — 15 against 25.
- ~~Only 33 of 59 sit in a line (55%).~~ **Fixed by batch 2 — 58 of 74 (78%)**, past the
  two-thirds target. The efficient move turned out not to be writing more chain members
  but giving *existing standalones* a base form or a next stage: 15 new species pulled 13
  standalones into chains, converting 28 species for the price of 15. Standalones fell
  26 → 16.
- ~~LEGENDARY and MYTHIC have not moved.~~ **Partly fixed by batch 2** — LEGENDARY 4→6,
  MYTHIC 2→3. Still the furthest from target proportionally, and still the tier where
  hurried authoring shows most.

- ~~74 of 151, 77 to go.~~ **Closed by batch 3**, which authored the remaining 77 in one
  pass and hit every rarity target exactly. 32/40/36/26/13/4 against 32/40/36/26/13/4.
- ~~The bottom needs the most: COMMON 17 against ~32, UNCOMMON 19 against ~40.~~
  **Fixed** — and written first rather than last, which is why the commons are a limpet,
  a roach, a bream, a stickleback and a shop snail rather than fifteen more anomalies.

**Open, and honestly flagged rather than quietly left.** Two things batch 3 should be
judged on later, not now:

- **Line coverage overshot.** 147 of 151 sit in a line — 97%, against a two-thirds
  *floor*. That is past the point the floor was defending. Twenty-eight of the 55 lines
  are only two stages, so the commitment per line is modest, but this file warned that
  "forcing a chain onto every creature would be as mechanical as having none" and batch 3
  came close to testing that. Only four standalones remain: The Pleasant Island and The
  Long Consideration, which are terminal by nature and were deliberately left alone, plus
  Brass Tack Goby and Lint Shrimp. **A future balance pass should consider un-chaining a
  handful rather than adding more lines**, and no future batch should treat 97% as the
  new floor.
- **`angler` is the thinnest class at 3, and `tumble` the thinnest behavior at 5.**
  Neither is broken — both have enough specimens to read as a vocabulary rather than a
  one-off — but they are where a rebalance should start if the renderer wants more of
  either.

## Art prompt rules

**Read `ART-DIRECTION.md` before writing one.** It carries the reasoning; this is the
contract.

Every species declares a **`plate`** — which of eight visual lineages its art comes from.
The Ichthyonomicon is a *scrapbook*, not a catalogue: species recorded at different times
carry plates from different media, so the bestiary looks like a collection assembled over
eighty years rather than a batch rendered in one afternoon.

| plate | medium | used for |
|---|---|---|
| `gosse` | hand-coloured lithograph, 1850s | recognisable fish, the commons |
| `blaschka` | lampworked glass model on a wire mount | translucent, unpreservable things |
| `gyotaku` | direct ink rubbing pressed from the animal | shoals, flat bodies |
| `trade-card` | chromolithograph cigarette card, c.1900 | the collectible middle |
| `scraperboard` | white line cut out of solid black | predators and lurkers |
| `haeckel` | ornamental symmetry plate | colonies, geometry, anomalies |
| `moulage` | wet specimen in a jar of fluid | the evasive placards, high rarity |
| `riso` | two fluorescent spot inks, misregistered | MYTHIC and the unplaceable |

### The three rules the validator enforces

1. **The plate's medium must appear in the prompt.** A `gyotaku` species whose prompt
   never says "rubbing" is just a fish with a label.
2. **No negations. Any negation, not only the style ones.** `NOT photorealistic` is a
   positive prompt containing the word *photorealistic*, addressed to a model with no
   instruction layer and an inert negative at cfg 1. Name a medium instead — a sumi
   rubbing cannot come out as a photograph, and nothing has to say so.

   This check *was* narrow, matching only a negation attached to a style word. That let
   twenty-seven prompts through carrying `no face at all`, `no eyes anywhere`, `no
   midtones and no wash`, and — from this file's own gyotaku description — `coverage
   uneven where the body did not touch`. **`no face` is how you commission a face.** The
   guard now rejects `not`, `no`, `without`, `never`, `instead of`, `rather than` and
   their relatives outright. Every one of those had a positive form that was also a
   better prompt; the before/after table is in ART-DIRECTION.md rule 2.
3. **Monochrome plates own their palette.** `gyotaku`, `scraperboard` and `riso` dictate
   their own colour, so a subject clause naming crimson or turquoise is stripped. Colour
   words are concrete and win against a single medium noun otherwise.

### Two rules the validator cannot check

4. **Name the medium, never the mood.** "Hand-coloured lithograph on foxed paper" is a
   prompt. "Whimsical macabre vibe" is a wish.
5. **Keep the imperfection** — foxing, misregistration, uneven ink, plate scratches, dust
   on the glass. Surface perfection is itself a tell; real printed things have a process
   and processes leave marks.

### What does not vary

The **placard register**. Whatever the plate, the field note is still two dry sentences
from someone not telling you everything. Eight visual lineages and one voice reads as *one
collector*. The reverse would read as noise.
