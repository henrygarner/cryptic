#!/usr/bin/env python3
"""Semantic lookups for cryptic clue setting: synonyms, definitions, homophones.

Uses the Datamuse API (no key, generous limits) and Wiktionary's REST API. These
feed the *definition* side of a clue and give synonyms that can serve as fodder
or as the surface's misdirection.

Usage
  lookup.py syn   WORD        synonyms and closely-related words (Datamuse ml=)
  lookup.py means WORD        words with a meaning like WORD, ranked (Datamuse)
  lookup.py assoc WORD        words associated with WORD (triggers, Datamuse rel_trg)
  lookup.py homophone WORD    words that sound like WORD (Datamuse sl=)
  lookup.py rhyme WORD        rhymes (Datamuse rel_rhy)
  lookup.py define WORD       dictionary senses and part(s) of speech (Wiktionary)
  lookup.py all   WORD        everything above, one JSON blob (used by dossier.py)

Network failures degrade gracefully to empty lists so a dossier still builds.
"""
import sys, json, argparse, urllib.parse, urllib.request

DM = "https://api.datamuse.com/words"
WIKT = "https://en.wiktionary.org/api/rest_v1/page/definition/"


def _get(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cryptic-clue-tool/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"__error__": str(e)}


def datamuse(**params):
    params.setdefault("max", 60)
    url = DM + "?" + urllib.parse.urlencode(params)
    data = _get(url)
    if isinstance(data, dict) and "__error__" in data:
        return []
    return [{"word": d["word"], "score": d.get("score"),
             "tags": d.get("tags", [])} for d in data]


def synonyms(word):
    return datamuse(ml=word, max=40)


def means_like(word):
    # ml gives semantic neighbours; filter to those tagged synonym-ish
    return datamuse(ml=word, max=60)


def associations(word):
    return datamuse(rel_trg=word, max=40)


def homophones(word):
    return datamuse(sl=word, max=30)


def rhymes(word):
    return datamuse(rel_rhy=word, max=30)


def define(word):
    """Wiktionary senses grouped by part of speech."""
    data = _get(WIKT + urllib.parse.quote(word))
    if isinstance(data, dict) and "__error__" in data:
        return {"senses": [], "error": data["__error__"]}
    senses = []
    langs = data.get("en", []) if isinstance(data, dict) else []
    import re
    tag = re.compile(r"<[^>]+>")
    for entry in langs:
        pos = entry.get("partOfSpeech", "")
        for d in entry.get("definitions", []):
            txt = tag.sub("", d.get("definition", "")).strip()
            if txt:
                senses.append({"pos": pos, "sense": txt})
    return {"senses": senses[:20]}


def cmd(a):
    fns = {"syn": synonyms, "means": means_like, "assoc": associations,
           "homophone": homophones, "rhyme": rhymes, "define": define}
    if a.what == "all":
        out = {
            "word": a.word,
            "synonyms": synonyms(a.word),
            "associations": associations(a.word),
            "homophones": homophones(a.word),
            "rhymes": rhymes(a.word),
            "definition": define(a.word),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    res = fns[a.what](a.word)
    if a.text and a.what != "define":
        print("\n".join(f'{r["word"]}  ({",".join(r.get("tags", []))})' for r in res))
    elif a.text:
        print("\n".join(f'[{s["pos"]}] {s["sense"]}' for s in res["senses"]))
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--text", action="store_true")
    p.add_argument("what", choices=["syn", "means", "assoc", "homophone", "rhyme", "define", "all"])
    p.add_argument("word")
    a = p.parse_args()
    cmd(a)


if __name__ == "__main__":
    main()
