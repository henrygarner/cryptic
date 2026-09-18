# Cryptic clue setter

PRESSURE

MYCELIUM

AWESOME

DISCOMBOBULATE

AMAZING

JUXTAPOSITION

```
Erotic parts excited horny old-timer (11)

Harass shy maths pioneer in prime line of enquiry (7, 10)

Halogen vented, absorbs last of ozone layer (3)

Trump starts to fire all reporters today (4)

Spawn from lyceum I'm cultivating (8)

Astonishing bit of Obama zinger (7)


```



A local agent workflow for setting cryptic crossword clues from a seed word. It
does the combinatorial spadework deterministically, fans out agents to
hypothesise wordplay routes and definitions in parallel, matchmakes them into
clues with smooth surfaces, and judges the result against Ximenean rules.

Invoke it as a skill:

```
/cryptic STAINER
/cryptic CARPET (6)
/cryptic ORCHESTRA — as a verb
```

Then steer in chat: "push the hidden-word one", "try a different definition",
"smoother surface on 3", "make it harder".

## How it works

1. **Dossier** (`tools/dossier.py`) runs the whole engine once and consolidates
   the material: anagrams, sub-anagrams with leftovers, word fragments,
   reversals, charade splits, hidden-across-a-join phrases, containers,
   definitions, synonyms, associations and homophones.
2. **Fan-out** — four wordplay agents (anagram; charade/container/deletion;
   hidden/reversal; homophone/whole-clue) and one definition agent hypothesise
   in parallel over that shared material.
3. **Matchmake** — routes are paired with definitions and drafted into full
   clues whose surfaces hide the seams.
4. **Judge** — an adversarial verifier checks each clue balances letter-for-
   letter, every operation is indicated, and the definition is fair, then scores
   surface, misdirection, economy and difficulty. Sound clues are ranked and
   returned annotated.

The orchestration lives in `.claude/skills/cryptic/SKILL.md`.

## The engine

Pure, offline, fast (~0.1s per query). JSON by default, `--text` for humans.

```
python3 tools/wordtools.py anagram    LETTERS
python3 tools/wordtools.py subanagram LETTERS --min 4
python3 tools/wordtools.py fragments  WORD
python3 tools/wordtools.py reversals  WORD
python3 tools/wordtools.py charade    WORD [--max-parts 4]
python3 tools/wordtools.py contains   WORD
python3 tools/wordtools.py spanning   WORD
python3 tools/wordtools.py abbrev     ["river"]
```

The semantic side (needs the network):

```
python3 tools/lookup.py syn WORD
python3 tools/lookup.py define WORD
python3 tools/lookup.py homophone WORD
python3 tools/lookup.py all WORD
```

Every returned word carries a familiarity rank (lower is more common; "obscure"
means it is not in the frequency list). Charades and spanning restrict
themselves to familiar pieces so the fodder reads fairly.

## Wordlists

- Base: `/usr/share/dict/words` (Webster's 2nd) + `web2a` variants + proper
  names, merged with a subtitle **frequency list** (`data/freq.txt`) that adds
  British spellings and inflections and drives the familiarity ranking.
- To use a better setter's list (UKACD, SCOWL), point the engine at it:
  `CRYPTIC_WORDLIST=/path/to/list python3 tools/dossier.py WORD`.
- Abbreviations and indicator words are curated in `tools/wordtools.py`
  (`ABBREV`) and `reference/indicators.md`; extend them freely.

## Fairness

The judge enforces the Ximenean standard in `reference/conventions.md`: one
accurate definition at an edge, complete and indicated wordplay, no indirect
anagrams, no padding. Misdirection and punning definitions are encouraged; they
are fair. Unfairness is not.
