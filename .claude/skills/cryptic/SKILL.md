---
name: cryptic
description: Turn a seed word into cryptic crossword clues. Fans out wordplay-strategy agents over a deterministic material dossier (anagrams, charades, hidden words, reversals, containers, deletions), proposes punning definitions, matchmakes them into full clues with smooth surfaces, and returns a Ximenean-judged, ranked, annotated set. Invoke with /cryptic WORD (optionally "/cryptic WORD (enumeration)" or with a target sense). Use whenever the user wants to set, compose, hypothesise or brainstorm cryptic clues for a word or phrase.
---

# Cryptic clue setter

Given a seed word, produce a ranked set of sound, satisfying cryptic clues with
smooth surfaces. The method mirrors how a human setter works: gather raw
material, hypothesise many wordplay routes and many definitions in parallel,
then matchmake a route to a definition into a clue whose surface hides the
seams, and judge it hard for fairness.

The house style is **Ximenean** (see `reference/conventions.md`): witty and
misleading is good, unfair is not. The prized effect is a *definition that
misdirects*, a word whose obvious surface sense is not the sense that defines
the answer (a verb read as a noun, "flower" meaning a river). That is fully
fair and is where the satisfaction lives.

Tools live under the project root (`/Users/hgarner/code/cryptic`). Run Python as
`python3`. All paths below are relative to that root.

## Step 1 — Parse the request

The seed is the argument. Accept `WORD`, `WORD (4,3)` with an enumeration, or a
note like `WORD — as a verb`. If the user named a target definition or sense,
carry it through. If no seed was given, ask for one. Normalise to the letters
of the answer; keep the enumeration if supplied.

## Step 2 — Build the material dossier (deterministic, once)

Run the engine once and save it, so every agent reasons over the same material:

```
python3 tools/dossier.py "WORD" --json --out <scratchpad>/dossier-WORD.json
python3 tools/dossier.py "WORD" > <scratchpad>/dossier-WORD.md
```

Read the markdown dossier yourself. It contains: whole-word anagrams (with a
familiarity rank; lower is more common), sub-anagrams with leftover letters,
word fragments inside the seed, reversals, charade splits (concatenations of
words and standard abbreviations), the seed hidden across a word-join, longer
words containing the seed, dictionary definitions by part of speech, synonyms,
associations and homophones.

If you need more of any category, call the underlying tools directly, e.g.
`python3 tools/wordtools.py --text --limit 40 charade WORD`, or
`python3 tools/wordtools.py abbrev "river"` to see what a plain word can signal,
or `python3 tools/lookup.py --text define WORD`.

## Step 3 — Fan out (parallel agents)

Spawn these agents **in one message so they run concurrently**. Give each the
seed, the path to the markdown dossier (tell them to Read it), and the paths to
`reference/indicators.md` and `reference/conventions.md`. Use the
`general-purpose` agent type.

Four **wordplay** agents, each hunting one family and returning *sound wordplay
skeletons only* (not finished clues):

1. **Anagram agent** — whole-word anagrams and partial-anagram-plus-extra
   routes (anagram of a sub-anagram, with the leftover letters supplied as a
   charade piece). Prefer familiar, vivid fodder.
2. **Charade / container / deletion agent** — build the answer by juxtaposing
   words and standard abbreviations (CAR+PET), by inserting one string in
   another, or by deleting indicated letters from a longer word.
3. **Hidden / reversal agent** — the answer hidden unbroken inside a longer word
   or across a natural word-join (use the "spanning" material), and reversals of
   the whole or of fragments (respect across vs down geometry).
4. **Homophone / double-def / &lit agent** — homophone routes, **double-definition**
   treatments, and **&lit** ("all-in-one") clues. Do **not** produce pure
   cryptic-definition clues: this house style requires wordplay in every clue,
   and a cryptic definition has none (an &lit is fine, its whole surface is
   wordplay). A double definition is the one allowed wordplay-free form.

Each wordplay agent returns a JSON list of candidates, every one with:

- `device` (anagram | charade | container | hidden | reversal | deletion |
  homophone | double-def | &lit | composite) — note **cryptic-def is not an
  allowed device**; every clue needs wordplay, double-def excepted
- `decomposition` — the exact route, e.g. `"anag(TREACLE) minus L"` or
  `"CAR + PET"` or `"hidden in osCAR PETer"`
- `letters` — the letters produced, which **must equal the answer exactly**
  (state the accounting; drop any candidate that does not balance)
- `indicator_type` needed and a `sample_indicator`
- `fodder` — the literal letters/words the solver is given
- `note` — why it is fair, and any surface hook it suggests
- `familiarity` — are all pieces common words / standard abbreviations?

One **definition** agent (runs concurrently with the four):

5. **Definition agent** — from the dossier's senses, synonyms and associations,
   propose 8–12 definitions of the answer. For each give: the definition
   phrase, its part of speech and number/tense, whether it needs a
   "definition-by-example" marker (say/perhaps), and crucially a **punning or
   part-of-speech-shifting** option where the word's obvious surface sense
   differs from the defining sense. Flag which are straight and which are
   misdirecting.

Tell every agent: stay strictly Ximenean, account for every letter, never rely
on an indirect anagram (fodder must be explicit letters), and return data, not
prose.

## Step 4 — Matchmake (you, inline)

You now hold many wordplay skeletons and many definitions. Marry them:

- A clue is `definition + wordplay` (in either order) joined by a fair link, or
  a double-definition, or an &lit where they coincide.
- Pick pairings whose **combined surface can be made to read as one natural
  phrase**. The art is choosing a definition and an indicator that both belong
  to the same imagined scene. Draft the surface, then sand it: swap the
  indicator for a synonym that fits the scene, reorder for rhythm, choose a link
  word that disappears.
- Follow the writing guidance: British spelling, no em-dashes, no Oxford commas,
  read it aloud. A clue that sounds like a real sentence beats a clever wreck.
- Aim for variety across devices in the final set, not five anagrams.

Produce 10–15 drafts, then keep the strongest ~10.

## Step 5 — Judge (adversarial check, then rank)

Spawn one **verifier** agent (`general-purpose`) on your shortlist. Give it the
answer, the drafts with their intended parses, and `reference/conventions.md`.
Its job is hostile: for each clue confirm the parse balances letter-for-letter,
every operation is indicated, the definition matches in sense/POS/number and
sits at an edge, there is no indirect anagram and no padding. It also enforces
the **wordplay rule**: every clue must contain wordplay (anagram, charade,
container, hidden, reversal, deletion, homophone or a combination, or an &lit
whose whole surface is wordplay). The only wordplay-free form allowed is a
double definition. Any clue that is a bare cryptic definition fails outright. It
returns, per clue, a soundness verdict (pass / fail with the specific fault) and
scores (0–5) for surface, misdirection, economy and difficulty.

Drop or fix anything the verifier fails on. Then rank by soundness first
(unsound is disqualified), then surface and wit.

## Step 6 — Present the ranked, annotated set

Return 6–10 clues, best first. For each:

> **1.  Clue text (enumeration)**
> Definition: _the defining word(s)_ → sense used.
> Wordplay: full parse with letter accounting, e.g. CAR (vehicle) + PET (tame animal).
> Indicator(s): which word signals which operation.
> Surface: one line on the misdirection — what the reader thinks it means vs what it does.
> Device: anagram / charade / … · Soundness: pass.

Keep annotations tight. Lead with your two or three favourites and say why.
Below the set, add a short **loose threads** line: any striking coincidence in
the dossier that did not resolve into a full clue, in case the user wants to
hack on it.

## Step 7 — Iterate in chat

After presenting, invite steering and act on it directly:
- "push the hidden-word one" → develop variants of that route.
- "try a different definition" → re-matchmake with other definitions.
- "smoother surface on 3" → re-sand that surface, keeping the parse.
- "make it harder / easier" → adjust definition obliqueness and indicator subtlety.
- "another anagram" → return to the dossier for fresh fodder.
You already hold the dossier; only re-run tools when you need material you do
not have.

## Guardrails

- Never present a clue whose letters do not balance, or with an unindicated
  operation, or an indirect anagram. Soundness is a gate, not a score.
- **Every clue must contain wordplay.** The only exception is the double
  definition. Pure cryptic definitions (a single witty definition, no wordplay)
  are not allowed, however tempting the surface. An &lit is fine because its
  whole surface doubles as the wordplay.
- The definition goes at the start or the end, never buried.
- If the dossier is thin (few anagrams, no clean charade), say so and lean on
  the routes that do exist rather than forcing a weak clue.
- Enumeration must match the answer's letter count (and word breaks for phrases).
