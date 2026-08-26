# Cross-game creature sharing

Date: 2026-08-26
Source: Silas, in session

This document clarifies the older shorthand in `SCHEMA.md` that called the `games` field
the "whole sharing mechanism." The `games` field is the **eligibility switch for sharing a
creature identity**. It is not the place for one game's mechanics to leak into another.

## One creature, multiple games

If Cthulhuquarium and The Ruler Is Hooked both use a creature, they share the same stable
identity:

- slug;
- name;
- species/taxonomic joke;
- core silhouette/concept;
- canonical rarity;
- general field note / creature identity;
- canonical bestiary art where appropriate.

Do not create near-duplicates merely because the projects have different mechanics. If
the shared concept is Rustfish, both games use Rustfish rather than inventing Iron Fish,
Copper Fish, or another renamed stand-in.

The current bible already demonstrates the intended selectivity. `parlour-rustfish` and
`drowned-carp` are tagged for both games, while many other species remain
Cthulhuquarium-only. Sharing is not a 1:1 roster mirror, and even stages of the same
evolution line may be shared selectively.

## What remains game-specific

The shared Creature record must not accumulate fields that only make sense to one game.

Cthulhuquarium owns aquarium mechanics such as:

- tank placement and capacity;
- hunger/feeding state;
- coin yield and drop interval;
- purchase/evolution progression;
- rivalry and tank behavior.

The Ruler Is Hooked owns fishing/kingdom mechanics such as:

- caught/discovered state;
- habitat and lure availability;
- catch weighting and specimen records;
- Fishopedia state;
- kingdom-choice unlock conditions;
- Ruler-specific ecology affinity.

That last field is deliberately **not** this bible's free-text `alignment`. Ruler Hooked
uses a three-way gameplay classification, `GOOD | NEUTRAL | EVIL`, describing what kind
of transformed kingdom permits a fish to appear. It does not declare the creature itself
morally good or evil. A personable undead fish may belong to an `EVIL` ecosystem because
the lake conditions that allow it are grim.

## Rarity stays canonical

Shared creatures keep the same rarity label across projects:

`COMMON | UNCOMMON | RARE | EPIC | LEGENDARY | MYTHIC`

A game that needs a shared fish to be harder or easier to encounter should change its
local unlock conditions, weights, habitat requirements, gear requirements, or progression,
not silently relabel the creature's rarity.

## Art identity versus presentation variants

A shared creature should remain visually recognizable across projects, but rendered
assets may differ by presentation.

Cthulhuquarium may use an Ichthyonomicon plate while Ruler Hooked uses a catch card or a
lake-context illustration. These should be keyed as variants of the same creature slug,
not as separate species concepts.

Example:

```text
parlour-rustfish / bestiary
parlour-rustfish / ruler-catch-card
parlour-rustfish / ruler-silhouette
```

## Meaning of `games`

`games: [cthulhuquarium, ruler-hooked]` means both games are allowed to reference this
canonical creature identity.

It does **not** mean:

- both games must use the creature;
- both games use the same progression mechanics;
- both games use the same availability rules;
- the creature belongs to a moral category in Cthulhuquarium;
- all evolution stages automatically cross into both games.

Per-game overlays should reference the stable creature slug. This keeps the ecosystem
coherent across projects without turning either game into a skin of the other.
