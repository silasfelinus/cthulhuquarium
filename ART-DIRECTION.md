# Cthulhuquarium — Art Direction

Companion to `fish/SCHEMA.md`. That file says what a prompt must contain; this one
says where the look comes from and why.

---

## The problem, stated honestly

Silas, 2026-08-25:

> *"There is a lot of pushback about AI generated text and art these days, mostly
> involving 'tells'. I want us to do our best to avoid that critique, not because I
> intend to hide our development, I believe 100% in transparency, but because I want
> this to feel free and unique... we need to pull inspiration from styles that aren't
> expected."*

Transparency is not in question. The goal is that the art is **actually distinctive**,
not that its origin is concealed.

### The biggest tell was ours, not the model's

Until this document, all 74 species prompts ended with the **same 40-word style
suffix** — *"vibrant saturated cartoon creature illustration, thick confident outlines,
exaggerated asymmetric anatomy, glossy wet highlights…"*.

Any individual image from that is fine. Seventy-four of them are a **batch**. Identical
lighting, identical palette temperature, identical framing, identical surface, across an
entire bestiary. Uniformity of process reads as machine-made far more reliably than any
single artefact does, and no amount of polish inside one image fixes it.

A second problem in the same string: **`glossy wet highlights` + `vibrant saturated` +
`bold colour` is a median attractor.** It is the mobile-game-icon look, one of the most
heavily represented styles in any image model's training data. Asking for it is asking
for the middle of the distribution.

### And the negation was doing nothing, or worse

Every prompt ended `NOT photorealistic, not a nature photograph`. The house guide
(`conductor/ART-PROMPTS.md`) is explicit that Krea 2 **has no instruction-following
layer** and its **negative prompt is inert at cfg 1** — every constraint has to survive
as a concrete noun in the positive prompt.

So that clause sits in a *positive* prompt, addressed to a model that cannot parse
negation, containing the words *photorealistic* and *nature photograph*. At best it does
nothing. At worst it is a prompt for the thing it forbids — which would explain the first
render batch coming back as competent nature photography rather neatly.

**The fix for both problems is the same fix**, and it is the one Silas asked for: stop
describing a *style* and start naming a **medium** and a **lineage**. A thing made of
lithograph ink on foxed paper cannot come out as a photograph, and no negation is needed
to say so.

---

## The idea: the Ichthyonomicon is a scrapbook

Not a catalogue. A **scrapbook**.

Species were recorded when they were first encountered, by whoever was doing the
recording, using whatever medium existed at the time. A specimen first described in 1853
has a hand-coloured lithograph. One first described in 1911 has a cigarette card. One
nobody could draw from life has a glass model. Somebody cut them all out and pasted them
into the same book.

**This is why the bestiary looks like eight different things, and it is the whole
anti-uniformity mechanism.** The variance is not decoration applied to dodge a critique —
it is what a real Victorian bestiary assembled over eighty years would actually look like.
It happens to also make a batch of images impossible to read as a batch.

Every species carries a **`plate`** field naming which lineage its art comes from. There
are eight.

---

## The eight plates

Each is a *medium with a history*, not a style adjective. Each has its own palette
discipline, its own surface, its own failure modes. Where they overlap is the subject
matter and the placard register — nothing else.

### 1. `gosse` — hand-coloured lithograph, 1850s

**Philip Henry Gosse**, who coined the word *aquarium* and wrote the book that made
keeping one a domestic craze. His plates are the literal ancestor of this game.

Fine engraved line under flat hand-laid watercolour washes. Period pigments only —
Prussian blue, madder lake, gamboge, sepia. Visible plate mark, foxed paper, the wash
slightly outside the line where the colourist was quick. Anatomy a little wrong in the way
of something drawn from a dead specimen by a man who never saw it swim.

*Gosse also wrote* Omphalos, *arguing the world was created already containing fossils of
things that never lived. "Everything out is in, or so they tell you." Nobody needs to know
this. It is why he is plate one.*

→ **Use for:** recognisable fish, tier 1–2, the commons. The plainest lineage for the
plainest creatures.

### 2. `blaschka` — lampworked glass model on a wire mount

**Leopold and Rudolf Blaschka** made thousands of glass sea-creature models for museums
between 1860 and 1930, because a jellyfish cannot be preserved and cannot be stuffed.

Transparent, hollow, impossibly fine. Light passes *through* the body and pools where the
glass is thick. Reads unmistakably as an **object**: it has a mount, a base, a wire
armature, a slight dust. The colours are in the glass, not on it.

→ **Use for:** jellies, translucent bodies, anything that would not survive being drawn
from a specimen. The bell line.

### 3. `gyotaku` — direct ink rubbing, pressed from the animal

Japanese fish printing, invented so a fisherman could record a catch's exact size. Sumi
ink applied to the fish, washi laid over, one impression taken.

Flat black on fibrous paper, coverage uneven where the body did not touch, fins printing
as fine radiating lines. Nothing is modelled because nothing was drawn — it is a contact
print. The eye is painted back in afterward by hand, because a rubbing cannot capture an
eye, and that one wet mark in a flat print is the whole image.

→ **Use for:** shoals, flat bodies, anything about *recording that you held it*. The
sardine line.

### 4. `trade-card` — chromolithograph cigarette card, c.1900

Player's, Wills's, Brooke Bond. **The ur-collectible** — numbered sets of small printed
cards, given away in packets, collected obsessively, a century before anyone thought to
put monsters on them.

Small format with a printed border and a name banner. Four-colour stone lithography with
visible misregistration and dot rosettes. Slightly garish, cheaply printed, and rounded at
the corners from being carried.

→ **Use for:** the mid tiers, the ones that feel most like *collection*. This is the
format the collection metaphor actually comes from.

### 5. `scraperboard` — white line scratched out of black

Mid-century natural history illustration (C. F. Tunnicliffe and after). A board coated
black; the image is *cut out of* the darkness with a blade.

No midtones. No wash. Only cut marks, hatched into form. Stark and linear and entirely
made of process. Any grey is an illusion made from spacing.

→ **Use for:** predators, lurkers, high contrast, anything that should read as a shape
before it reads as an animal.

### 6. `haeckel` — ornamental plate, radial symmetry

**Ernst Haeckel's** *Kunstformen der Natur*. Creatures arranged as **design** rather than
portraiture: obsessive symmetry, multiple views on one sheet, specimens laid out to fill
a rectangle beautifully rather than to sit naturally.

Fine line, restrained colour, ornamental border. The organism is treated as ornament and
the page composition matters more than the pose.

→ **Use for:** colonies, geometric things, anomalies, anything with repeating parts.

### 7. `moulage` — wet specimen in a jar

Anatomical preparation. The thing is in fluid, in glass, on a shelf, with a handwritten
label tied on with string.

Formalin yellow. Colours leached toward parchment. The jar's own refraction bending the
body where it presses the glass. It is dead and it is being kept, and the label is more
legible than the specimen.

→ **Use for:** the unsettling ones, high rarity, anything the placard is being evasive
about.

### 8. `riso` — two or three spot inks on cheap paper

The one modern lineage, used sparingly so it stays strange. Risograph duplication: a
handful of flat spot colours, deliberate misregistration, overprint multiplying where two
inks cross, paper showing through everywhere.

Fluorescent pink and a dull blue that were never meant to sit together. No blending is
possible; a third colour only exists where two overlap.

→ **Use for:** MYTHIC, and the small number of species that should feel like they were
recorded by someone with no access to any of the above.

---

## Rules

1. **Name the medium, never the mood.** "Hand-coloured lithograph on foxed paper" is a
   prompt. "Whimsical macabre vibe" is a wish. Krea 2 has no instruction layer; only
   concrete nouns survive.
2. **No negations, ever.** Not `NOT photorealistic`, not `no smooth gradients`. Krea 2
   reads them as subject matter. If you do not want a photograph, name a printing process.
   A gyotaku rubbing cannot come out as a photograph because a rubbing is not a photograph.
3. **One plate per species, and it is recorded in the bible.** Not chosen at render time,
   not varied per attempt. It is a property of the creature, like its tier.
4. **Palette is per plate, not per prompt.** `gosse` gets period pigments; `riso` gets two
   fluorescent inks. A creature does not get to be any colour it likes — the plate decides
   the range, which is what makes the bestiary cohere while looking varied.
5. **Keep the imperfection.** Foxing, misregistration, uneven ink, plate scratches, dust
   on the glass. Surface perfection is itself a tell: real printed things have a process
   and processes leave marks.
6. **The placard register does not change.** Whatever the plate, the field note is still
   two dry sentences from someone not telling you everything. The writing is the constant;
   the image is the variable. That is the correct way round — a bestiary with eight visual
   lineages and one voice reads as *one collector*. The reverse would read as noise.

---

## What this is not

Not an attempt to look hand-made, or to pass. Nothing here is about disguise — the
development of this game is public and the art is generated, and both of those stay true.

It is about **using references narrow enough to produce something specific**. The critique
of AI art that actually lands is not "a machine made it," it is "it looks like everything
else." Eight named lineages with real histories, one per creature, chosen for reasons a
person could argue with, is simply a better brief than one style string repeated
seventy-four times — and it would be the right call if every image were painted by hand.
