#!/usr/bin/env python3
"""Build a 'material dossier' for a seed word: run every deterministic tool plus
the semantic lookups and consolidate into one brief the strategy agents work from.

Usage
  dossier.py WORD               markdown dossier to stdout
  dossier.py WORD --json        JSON dossier (full structured material)
  dossier.py WORD --json --out FILE   write JSON to FILE, print the path

The point is to do all the combinatorial and lookup spadework ONCE, so the
fan-out agents reason over shared material instead of each recomputing it.
"""
import sys, os, json, argparse, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(tool, *args):
    cmd = [PY, os.path.join(HERE, tool), *[str(a) for a in args]]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if out.returncode != 0:
            return {"__error__": out.stderr.strip()}
        return json.loads(out.stdout) if out.stdout.strip() else {}
    except Exception as e:
        return {"__error__": str(e)}


def build(word, limit=25):
    w = word.lower().strip()
    d = {
        "seed": w,
        "length": len("".join(c for c in w if c.isalpha())),
        "wordplay": {
            "anagrams": run("wordtools.py", "--limit", limit, "anagram", w).get("anagrams", []),
            "subanagrams": run("wordtools.py", "--limit", limit, "subanagram", w, "--min", 3).get("subanagrams", []),
            "fragments": run("wordtools.py", "--limit", limit, "fragments", w).get("fragments", []),
            "reversals": run("wordtools.py", "reversals", w),
            "charades": run("wordtools.py", "--limit", limit, "charade", w).get("charades", []),
            "containers": run("wordtools.py", "--limit", limit, "contains", w).get("containers", []),
            "spanning": run("wordtools.py", "--limit", 12, "spanning", w).get("spans", []),
        },
        "meaning": run("lookup.py", "all", w),
    }
    return d


def md(d):
    w = d["seed"]
    L = []
    A = L.append
    A(f"# Clue material for **{w.upper()}** ({d['length']} letters)\n")
    wp = d["wordplay"]

    ana = wp["anagrams"]
    A("## Anagrams (whole word)")
    if ana:
        A(", ".join(f'{a["word"].upper()}' + (f' [{a["rank"]}]' if a.get("rank") else " [obscure]") for a in ana[:20]))
    else:
        A("_none_")
    A("")

    A("## Sub-anagrams (partial anagram + leftover letters)")
    for s in wp["subanagrams"][:16]:
        A(f'- {s["word"].upper()} + leftover `{s["leftover"].upper() or "-"}`')
    A("")

    A("## Word fragments inside the seed (charade / hidden material)")
    for f in wp["fragments"][:16]:
        A(f'- {f["fragment"].upper()}  = {f["before"].upper() or "·"}[{f["fragment"].upper()}]{f["after"].upper() or "·"}')
    A("")

    rev = wp["reversals"]
    A("## Reversals")
    if rev.get("whole_reversed"):
        A(f'- WHOLE: {w.upper()} is {rev["whole_reversed"].upper()} written backwards')
    for r in rev.get("fragment_reversals", [])[:12]:
        A(f'- {r["fragment"].upper()} is {r["reads_reversed_as"].upper()} reversed  ({r["before"].upper() or "·"}[..]{r["after"].upper() or "·"})')
    A("")

    A("## Charade splits (concatenations of words / abbreviations)")
    for c in wp["charades"][:16]:
        A(f'- {c["render"]}')
    A("")

    A("## Seed hidden across a word-join (hidden-word phrases)")
    for s in wp["spanning"][:8]:
        fw = ", ".join(x.upper() for x in s["first_words"][:4])
        sw = ", ".join(x.upper() for x in s["second_words"][:4])
        A(f'- …{s["head"].upper()}|{s["tail"].upper()}…  first: {fw}  second: {sw}')
    A("")

    A("## Longer words containing the seed (container / deletion)")
    A(", ".join(c.upper() for c in wp["containers"][:20]) or "_none_")
    A("")

    m = d["meaning"]
    A("## Definitions (candidate straight or punning definitions)")
    for s in m.get("definition", {}).get("senses", [])[:12]:
        A(f'- _{s["pos"]}_: {s["sense"]}')
    A("")
    A("## Synonyms (definition candidates / fodder)")
    A(", ".join(x["word"] for x in m.get("synonyms", [])[:25]) or "_none_")
    A("")
    A("## Associations (surface-reading colour)")
    A(", ".join(x["word"] for x in m.get("associations", [])[:20]) or "_none_")
    A("")
    A("## Homophones")
    A(", ".join(x["word"] for x in m.get("homophones", [])[:15]) or "_none_")
    A("")
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("word")
    p.add_argument("--json", action="store_true")
    p.add_argument("--out")
    p.add_argument("--limit", type=int, default=25)
    a = p.parse_args()
    d = build(a.word, a.limit)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(a.out)
    elif a.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        print(md(d))


if __name__ == "__main__":
    main()
