#!/usr/bin/env python3
"""Deterministic wordplay engine for cryptic clue setting.

All the combinatorial spadework a setter does by hand: anagrams, sub-anagrams
with leftover letters, word fragments, reversals, charade splits, hidden-word
material and containers. Pure and offline; the semantic side (synonyms,
definitions, homophones) lives in lookup.py.

Wordlists
  Base single-word list defaults to /usr/share/dict/words (web2). Override with
  CRYPTIC_WORDLIST=/path/to/list (one entry per line) to drop in UKACD or SCOWL.
  Phrase material comes from /usr/share/dict/web2a when present.

Usage
  wordtools.py anagram    LETTERS            full anagrams (same multiset)
  wordtools.py subanagram LETTERS [--min N]  words from a subset, with leftovers
  wordtools.py fragments  WORD               dictionary words inside WORD (contiguous)
  wordtools.py reversals  WORD               fragments whose reversal is a word; whole reversed
  wordtools.py charade    WORD [--max-parts K] splits into concatenated words/abbrevs
  wordtools.py contains   WORD               longer entries that contain WORD (hidden / deletion)
  wordtools.py spanning   WORD               word pairs where WORD hides across the join
  wordtools.py abbrev     [TEXT]             cryptic abbreviations (all, or for a meaning)

Every subcommand prints JSON to stdout unless --text is given.
"""
import sys, os, json, argparse
from collections import Counter, defaultdict

# --- cryptic abbreviations: letter(s) a setter may signal by a plain word ---
# meaning -> list of letter-strings it can become in wordplay
ABBREV = {
    "a": ["a", "an", "area", "answer", "ace", "adult"],
    "about": ["c", "ca", "re", "on", "approx"],
    "acid": ["ph"],
    "adult": ["a", "x"],
    "advanced": ["a", "adv"],
    "against": ["v", "vs", "con"],
    "america": ["us", "usa"], "american": ["us", "am"],
    "and": ["n"], "answer": ["a", "ans"],
    "are": ["r"], "area": ["a"],
    "at": ["at"], "atomic": ["a"],
    "bachelor": ["ba", "b"], "back": ["b"], "bad": ["ill"],
    "beginner": ["l"], "bishop": ["b", "rr"], "black": ["b", "bl"],
    "book": ["b", "bk", "ot", "nt", "bible"], "born": ["b", "nee"],
    "boy": ["b", "son", "lad"], "bridge": ["br"],
    "caught": ["c", "ct"], "cape": ["c"], "capacity": ["c"],
    "cardinal": ["n", "s", "e", "w", "red"],
    "celsius": ["c"], "cent": ["c"], "centigrade": ["c"],
    "century": ["c", "ton", "100"], "chapter": ["c", "ch", " chap"],
    "child": ["c"], "church": ["ch", "ce", "ri", "rc"],
    "circa": ["c", "ca"], "circle": ["o"], "city": ["ec", "la", "ny"],
    "class": ["cl", "form"], "clockwise": ["cw"], "club": ["c", "clubs"],
    "cold": ["c"], "college": ["c"], "company": ["co", "plc", "ltd", "inc", "ss"],
    "compass": ["n", "s", "e", "w", "ne", "nw", "se", "sw"],
    "conservative": ["c", "con", "tory"], "copper": ["cu", "cop", "d"],
    "current": ["i", "ac", "dc"],
    "date": ["d"], "daughter": ["d"], "day": ["d"], "dead": ["d"],
    "degree": ["d", "ba", "ma"], "democrat": ["d"], "diamond": ["d", "ice"],
    "died": ["d"], "direction": ["n", "s", "e", "w"], "doctor": ["dr", "mo", "gp"],
    "dog": ["cur"], "drive": ["dr"], "duke": ["d"], "duck": ["o"],
    "east": ["e"], "eastern": ["e"], "ecstasy": ["e"], "electric": ["e"],
    "energy": ["e"], "engineer": ["re", "eng", "be"], "england": ["e"],
    "english": ["e", "eng"], "european": ["e", "eu"], "excellent": ["a1"],
    "extra": ["bye", "wide"],
    "fahrenheit": ["f"], "false": ["f"], "family": ["kin"], "fellow": ["f"],
    "female": ["f", "she"], "fine": ["f"], "first": ["a", "1", "i"],
    "fifty": ["l"], "five": ["v"], "flat": ["b"], "florida": ["fl"],
    "following": ["f"], "foot": ["ft", "f"], "force": ["f"], "france": ["f"],
    "french": ["f", "fr"], "friday": ["fri"], "gallon": ["g", "gal"],
    "game": ["go", "ludo"], "gay": ["g"], "german": ["g", "ger"],
    "girl": ["g", "gal", "lass", "miss"], "gold": ["au", "or"], "good": ["g"],
    "grand": ["g", "k", "1000"], "gram": ["g"], "great": ["gt"], "greek": ["gr"],
    "hard": ["h"], "hearts": ["h"], "height": ["h"], "henry": ["h"],
    "her majesty": ["hm"], "high": ["hi", "h"], "hospital": ["h"], "hot": ["h"],
    "hour": ["h", "hr"], "house": ["ho"], "hundred": ["c", "h", "100"],
    "husband": ["h"], "id": ["id"], "in charge": ["ic"], "india": ["i"],
    "iron": ["fe"], "island": ["i", "is"], "italy": ["i"], "italian": ["it"],
    "jack": ["j", "ar", "tar"], "junior": ["jr", "jun"], "key": ["a", "b", "c", "d", "e", "f", "g"],
    "king": ["k", "r", "gr", "ky"], "knight": ["n", "kt"], "lake": ["l"],
    "large": ["l"], "latin": ["l", "lat"], "leader": ["l"], "learner": ["l"],
    "left": ["l"], "length": ["l"], "liberal": ["l", "lib"], "line": ["l", "ry", "row"],
    "little": ["l"], "litre": ["l"], "loch": ["l"], "loud": ["f"], "louisiana": ["la"],
    "love": ["o"], "low": ["lo"], "male": ["m", "he"], "man": ["m", "he", "gi"],
    "mark": ["m"], "married": ["m"], "mass": ["m"], "maiden": ["m"], "medium": ["m"],
    "member": ["mp", "mem", "leg", "arm"], "meridian": ["am", "pm"], "metre": ["m"],
    "mike": ["m"], "mile": ["m"], "million": ["m"], "minute": ["m", "min"],
    "model": ["t"], "moment": ["mo"], "monday": ["mon"], "money": ["m", "l", "lsd", "tin"],
    "month": ["m", "may", "mar", "jan"], "mother": ["ma", "mum", "mom"],
    "mountain": ["mt", "ben"], "name": ["n"], "napoleon": ["n"], "nationalist": ["n"],
    "navy": ["rn", "n"], "new": ["n"], "newton": ["n"], "nine": ["ix"], "no": ["no", "n"],
    "north": ["n"], "northern": ["n"], "note": ["a", "b", "c", "d", "e", "f", "g", "n", "te", "do", "re", "mi", "fa", "so", "la", "ti"],
    "nothing": ["o"], "novice": ["l"], "number": ["no", "n", "figure"], "nurse": ["n", "en", "sen"],
    "of": ["o"], "ohio": ["oh"], "old": ["o"], "one": ["i", "a", "an", "ace", "un"],
    "operation": ["op"], "opposed to": ["v"], "order": ["obe", "om"], "over": ["o", "re", "ovr"],
    "oxygen": ["o"], "page": ["p", "pg"], "parking": ["p"], "party": ["do", "con", "lab", "dem"],
    "pawn": ["p"], "peace": ["om"], "penny": ["p", "d", "c"], "pence": ["p", "d"],
    "phosphorus": ["p"], "piano": ["p"], "point": ["n", "s", "e", "w", "pt", "dot", "nib"],
    "pole": ["n", "s"], "police": ["ri", "cid", "pc", "met"], "pound": ["l", "lb"],
    "power": ["p"], "president": ["p"], "priest": ["eli", "fr"], "prince": ["p"],
    "professional": ["pro"], "quarter": ["n", "s", "e", "w", "q"], "queen": ["q", "r", "er", "hm"],
    "quiet": ["p", "sh", "mum"], "radius": ["r"], "railway": ["ry", "br", "l"],
    "recipe": ["r"], "record": ["ep", "lp", "cd", "log"], "red": ["r"], "republican": ["r"],
    "resistance": ["r"], "right": ["r", "rt"], "river": ["r", "po", "ex", "dee", "exe", "cam", "ouse"],
    "road": ["rd", "st"], "roman": ["r"], "romeo": ["r"], "round": ["o"], "royal": ["r"],
    "rugby": ["ru", "rl"], "run": ["r"], "runs": ["r"], "sailor": ["ab", "tar", "salt", "rn"],
    "saint": ["s", "st"], "saturday": ["sat"], "school": ["sch"], "scholar": ["ba"],
    "scottish": ["sc"], "second": ["s", "mo", "l", "b"], "see": ["ee", "lo"],
    "series": ["set"], "sex": ["m", "f", "it"], "shilling": ["s", "bob"], "ship": ["ss", "mv", "sub"],
    "short time": ["mo", "sec"], "sign": ["leo", "aries"], "silver": ["ag"], "singular": ["s"],
    "sister": ["sis", "nun"], "six": ["vi"], "small": ["s"], "society": ["s", "soc"],
    "soft": ["p"], "soldier": ["gi", "or", "ant", "para"], "son": ["s"], "soprano": ["s"],
    "south": ["s"], "southern": ["s"], "spades": ["s"], "special": ["sp"], "square": ["s"],
    "state": ["s"], "street": ["st"], "student": ["l"], "study": ["den", "con"], "sun": ["s"],
    "sunday": ["sun", "s"], "tan": ["t"], "tape": ["t"], "temperature": ["t"], "ten": ["x"],
    "tenor": ["t"], "the": ["t", "le", "la", "el"], "thousand": ["k", "m", "g", "1000"],
    "time": ["t"], "tenor": ["t"], "ton": ["t"], "tory": ["c", "con"], "tree": ["elm", "ash", "oak", "yew"],
    "trump": ["t"], "turn": ["u", "re"], "unfinished": ["u"], "union": ["tu"], "unit": ["u"],
    "university": ["u", "uni"], "up": ["u"], "upper class": ["u"], "us": ["us"],
    "vector": ["v"], "very": ["v"], "vice": ["v"], "victory": ["v"], "vitamin": ["a", "b", "c", "d", "e", "k"],
    "volt": ["v"], "volume": ["v", "vol"], "watt": ["w"], "way": ["st", "rd", "n", "s", "e", "w"],
    "week": ["wk"], "weight": ["wt", "g", "lb", "oz", "st"], "west": ["w"], "western": ["w"],
    "wicket": ["w"], "wide": ["w"], "wife": ["w"], "will": ["w"], "with": ["w"],
    "without": ["o", "sans"], "woman": ["w", "she"], "work": ["op", "job"], "year": ["y", "yr"],
    "yes": ["y", "si", "aye", "da"], "you": ["u", "thee"], "young": ["y"],
}
# reverse index: letters -> meanings, for annotating charade pieces
LETTERS_TO_MEANING = defaultdict(list)
for m, ls in ABBREV.items():
    for l in ls:
        LETTERS_TO_MEANING[l].append(m)
ABBREV_LETTERS = set(LETTERS_TO_MEANING)


HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def norm(s):
    return "".join(ch for ch in s.lower() if ch.isalpha())


_FREQ = None


def load_freq():
    """word -> rank (1 = most common). From data/freq.txt ('word count' per line)."""
    global _FREQ
    if _FREQ is not None:
        return _FREQ
    _FREQ = {}
    p = os.path.join(DATA, "freq.txt")
    if os.path.exists(p):
        rank = 0
        with open(p, encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.split()
                if w:
                    rank += 1
                    _FREQ.setdefault(w[0].lower(), rank)
    return _FREQ


def rankof(w):
    """Familiarity rank of a word, or None if not in the frequency list."""
    return load_freq().get(w.lower())


def familiar(w, max_rank):
    if max_rank is None:
        return True
    r = rankof(w)
    return r is not None and r <= max_rank


_WORDS = None


def load_words():
    """Broad set: system dict (web2 + web2a singles) plus every frequency-list word.
    Frequency words add British spellings and inflections web2 lacks."""
    global _WORDS
    if _WORDS is not None:
        return _WORDS
    words = set()
    sources = [os.environ.get("CRYPTIC_WORDLIST", "/usr/share/dict/words"),
               "/usr/share/dict/web2a", "/usr/share/dict/propernames"]
    for path in sources:
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    w = line.strip().lower()
                    if w and " " not in w and w.isalpha():
                        words.add(w)
    words.update(w for w in load_freq() if w.isalpha())
    _WORDS = words
    return words


def load_phrases():
    """Multi-word / phrase entries for hidden-word and definition material."""
    out = []
    p = "/usr/share/dict/web2a"
    if os.path.exists(p):
        with open(p, encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip()
                if w and " " in w:
                    out.append(w.lower())
    return out


def by_rank(w):
    """Sort key: familiar words first, unranked (obscure) last, then alphabetical."""
    r = rankof(w)
    return (r if r is not None else 10 ** 9, w)


def cmd_anagram(a):
    letters = norm(a.letters)
    key = Counter(letters)
    words = load_words()
    out = [w for w in words if w != letters and len(w) == len(letters)
           and Counter(w) == key and familiar(w, a.max_rank)]
    out.sort(key=by_rank)
    out = out[: a.limit]
    emit(a, {"seed": letters, "anagrams": [{"word": w, "rank": rankof(w)} for w in out]},
         [f'{w}  [{rankof(w) or "obscure"}]' for w in out])


def cmd_subanagram(a):
    letters = norm(a.letters)
    key = Counter(letters)
    minlen = a.min
    words = load_words()
    res = []
    for w in words:
        if len(w) < minlen or len(w) >= len(letters) or not familiar(w, a.max_rank):
            continue
        cw = Counter(w)
        if all(cw[c] <= key[c] for c in cw):
            leftover = key.copy()
            leftover.subtract(cw)
            left = "".join(sorted("".join(c * n for c, n in leftover.items() if n > 0)))
            res.append({"word": w, "uses": w, "leftover": left, "rank": rankof(w)})
    # prefer solutions that eat more of the word, then the more familiar
    res.sort(key=lambda r: (-len(r["uses"]), r["rank"] if r["rank"] else 10 ** 9, r["word"]))
    emit(a, {"seed": letters, "subanagrams": res[: a.limit]},
         [f'{r["word"]}  (leftover: {r["leftover"] or "-"})  [{r["rank"] or "obscure"}]' for r in res[: a.limit]])


def cmd_fragments(a):
    word = norm(a.word)
    words = load_words()
    n = len(word)
    frags = []
    for i in range(n):
        for j in range(i + 3, n + 1):  # words of length >=3
            piece = word[i:j]
            if piece != word and piece in words and familiar(piece, a.max_rank):
                frags.append({"fragment": piece, "start": i, "end": j,
                              "before": word[:i], "after": word[j:], "rank": rankof(piece)})
    frags.sort(key=lambda f: (f["rank"] if f["rank"] else 10 ** 9, -len(f["fragment"]), f["start"]))
    frags = frags[: a.limit]
    emit(a, {"seed": word, "fragments": frags},
         [f'{f["fragment"]}  = {f["before"] or "·"}[{f["fragment"]}]{f["after"] or "·"}  [{f["rank"] or "obscure"}]' for f in frags])


def cmd_reversals(a):
    word = norm(a.word)
    words = load_words()
    n = len(word)
    res = {"whole_reversed": None, "fragment_reversals": []}
    if word[::-1] in words and word[::-1] != word:
        res["whole_reversed"] = word[::-1]
    for i in range(n):
        for j in range(i + 3, n + 1):
            piece = word[i:j]
            rev = piece[::-1]
            if rev != piece and rev in words and familiar(rev, a.max_rank):
                res["fragment_reversals"].append(
                    {"fragment": piece, "reads_reversed_as": rev, "rank": rankof(rev),
                     "start": i, "end": j, "before": word[:i], "after": word[j:]})
    res["fragment_reversals"].sort(key=lambda f: (-len(f["fragment"]), f["rank"] if f["rank"] else 10 ** 9, f["start"]))
    res["fragment_reversals"] = res["fragment_reversals"][: a.limit]
    lines = []
    if res["whole_reversed"]:
        lines.append(f'WHOLE: {word} is {res["whole_reversed"]} reversed')
    for f in res["fragment_reversals"]:
        lines.append(f'{f["fragment"]} <- {f["reads_reversed_as"]} reversed  ({f["before"] or "·"}[..]{f["after"] or "·"})')
    emit(a, res, lines)


def _charade_splits(word, words, max_parts, max_rank):
    """All segmentations of word into pieces that are familiar words (len>=2) or abbrevs."""
    results = []

    def valid_piece(p):
        kinds = []
        if len(p) >= 2 and p in words and familiar(p, max_rank):
            kinds.append("word")
        if p in ABBREV_LETTERS:
            kinds.append("abbrev")
        return kinds

    def rec(pos, parts):
        if len(parts) > max_parts:
            return
        if pos == len(word):
            if len(parts) >= 2:
                results.append(list(parts))
            return
        for end in range(pos + 1, len(word) + 1):
            p = word[pos:end]
            kinds = valid_piece(p)
            if kinds:
                parts.append({"piece": p, "kinds": kinds,
                              "means": LETTERS_TO_MEANING.get(p, []) if "abbrev" in kinds else []})
                rec(end, parts)
                parts.pop()

    rec(0, [])
    return results


def cmd_charade(a):
    word = norm(a.word)
    words = load_words()
    # charades explode with obscure pieces; cap familiarity even if global is open
    max_rank = a.max_rank if a.max_rank is not None else 30000
    splits = _charade_splits(word, words, a.max_parts, max_rank)

    def score(sp):
        # prefer fewer pieces, longer & more familiar word-pieces, fewer bare abbreviations
        wordy = sum(len(p["piece"]) for p in sp if "word" in p["kinds"])
        abbr = sum(1 for p in sp if "word" not in p["kinds"])
        commonness = sum((rankof(p["piece"]) or 40000) for p in sp if "word" in p["kinds"])
        return (len(sp), -wordy, abbr, commonness)

    splits.sort(key=score)
    out = []
    for sp in splits[: a.limit]:
        parts = []
        for p in sp:
            if "word" in p["kinds"]:
                parts.append(p["piece"].upper())
            else:
                parts.append(f'{p["piece"].upper()}({"/".join(p["means"][:4])})')
        out.append(" + ".join(parts))
    emit(a, {"seed": word, "charades": [
        {"parts": sp, "render": r} for sp, r in zip(splits[: a.limit], out)]}, out)


def cmd_contains(a):
    word = norm(a.word)
    words = load_words()
    hits = [w for w in words if word in w and w != word and len(w) <= len(word) + 6
            and familiar(w, a.max_rank)]
    hits.sort(key=lambda w: (len(w), by_rank(w)))
    # show what wraps around the seed
    lines = []
    for w in hits[: a.limit]:
        i = w.find(word)
        lines.append(f'{w}  = {w[:i] or "·"}[{word}]{w[i+len(word):] or "·"}')
    emit(a, {"seed": word, "containers": hits[: a.limit]}, lines)


def cmd_spanning(a):
    """Words where the seed hides across a join: prefix ends a word, suffix starts the next.
    Good for 'hidden word' clues with a natural two-word phrase."""
    word = norm(a.word)
    words = load_words()
    n = len(word)
    # spanning wants familiar words either side of the join, else the hidden clue reads as gibberish
    mr = a.max_rank if a.max_rank is not None else 30000
    pool = [w for w in words if 3 <= len(w) <= 11 and familiar(w, mr)]
    res = []
    for cut in range(1, n):
        head, tail = word[:cut], word[cut:]  # head ends first word, tail starts second
        # first word must END with head, second must START with tail
        firsts = sorted([w for w in pool if w.endswith(head) and len(w) > len(head)], key=by_rank)
        seconds = sorted([w for w in pool if w.startswith(tail) and len(w) > len(tail)], key=by_rank)
        if firsts and seconds:
            res.append({"cut": cut, "head": head, "tail": tail,
                        "first_words": firsts[:8], "second_words": seconds[:8]})
    lines = []
    for r in res:
        lines.append(f'…{r["head"]}|{r["tail"]}…  e.g. {r["first_words"][0].upper()} + {r["second_words"][0].upper()}'
                     f'  ({len(r["first_words"])}×{len(r["second_words"])} combos)')
    emit(a, {"seed": word, "spans": res}, lines)


def cmd_abbrev(a):
    if a.text:
        m = a.text.lower().strip()
        letters = ABBREV.get(m, [])
        emit(a, {"meaning": m, "letters": letters}, [f'{m} -> {", ".join(letters) or "(none)"}'])
    else:
        lines = [f'{m}: {", ".join(ls)}' for m, ls in sorted(ABBREV.items())]
        emit(a, {"abbreviations": ABBREV}, lines)


def emit(a, obj, text_lines):
    if getattr(a, "text", False):
        print("\n".join(str(x) for x in text_lines))
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--text", action="store_true", help="human-readable output instead of JSON")
    p.add_argument("--limit", type=int, default=60, help="max results")
    p.add_argument("--max-rank", type=int, default=None,
                   help="only use words within this familiarity rank (e.g. 20000). "
                        "Default: unrestricted for anagrams/fragments, 30000 for charade/spanning.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("anagram"); s.add_argument("letters"); s.set_defaults(fn=cmd_anagram)
    s = sub.add_parser("subanagram"); s.add_argument("letters"); s.add_argument("--min", type=int, default=3); s.set_defaults(fn=cmd_subanagram)
    s = sub.add_parser("fragments"); s.add_argument("word"); s.set_defaults(fn=cmd_fragments)
    s = sub.add_parser("reversals"); s.add_argument("word"); s.set_defaults(fn=cmd_reversals)
    s = sub.add_parser("charade"); s.add_argument("word"); s.add_argument("--max-parts", type=int, default=4); s.set_defaults(fn=cmd_charade)
    s = sub.add_parser("contains"); s.add_argument("word"); s.set_defaults(fn=cmd_contains)
    s = sub.add_parser("spanning"); s.add_argument("word"); s.set_defaults(fn=cmd_spanning)
    s = sub.add_parser("abbrev"); s.add_argument("text", nargs="?"); s.set_defaults(fn=cmd_abbrev)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
