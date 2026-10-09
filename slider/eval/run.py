#!/usr/bin/env python3
"""Score slider kit against a plain directory search on the same vague asks.

    python3 slider/eval/run.py            # summary
    python3 slider/eval/run.py -v         # every case

Directory search = what a user gets today by typing their ask into a plugin
search box: top-K catalog plugins by word overlap with name + description.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kit  # noqa: E402

K = 4
STOP = set("a an the to of for my our on in so is it this that and or with from by be as are do make me us i we you".split())


def words(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2]


def directory_search(ask, catalog, k=K):
    q = set(words(ask))
    scored = []
    for name, p in catalog.items():
        doc = words(name.replace("-", " ") + " " + p["description"])
        score = sum(doc.count(w) for w in q) + 3 * sum(w in name for w in q)
        if score:
            scored.append((-score, name))
    return [n for _, n in sorted(scored)[:k]]


def score(picks, case, always_ok):
    picks = set(picks)
    covered = all(picks & set(need) for need in case["must"])
    allowed = set(always_ok) | set(case["ok"]) | {p for need in case["must"] for p in need}
    noise = len(picks - allowed)
    return covered, noise


def main():
    verbose = "-v" in sys.argv
    data = json.loads((Path(__file__).parent / "cases.json").read_text())
    catalog, needs = kit.load()
    taste = {"dropped": [], "kept": []}
    rows = {"slider kit": [], "directory search": []}
    for c in data["cases"]:
        chosen, _ = kit.choose(c["ask"], set(c["stack"]), catalog, needs, taste, set())
        s_picks = [k["plugin"] for k in chosen]
        d_picks = directory_search(c["ask"], catalog)
        for arm, picks in (("slider kit", s_picks), ("directory search", d_picks)):
            cov, noise = score(picks, c, data["always_ok"])
            rows[arm].append((cov, noise, len(picks)))
        if verbose:
            s = score(s_picks, c, data["always_ok"])
            d = score(d_picks, c, data["always_ok"])
            print(f"{'✓' if s[0] else '✗'}{'✓' if d[0] else '✗'}  {c['ask']}")
            print(f"     slider:    {', '.join(s_picks)}" + (f"   (noise {s[1]})" if s[1] else ""))
            print(f"     directory: {', '.join(d_picks) or '—'}" + (f"   (noise {d[1]})" if d[1] else ""))
    n = len(data["cases"])
    print(f"\n{n} vague asks · K={K}\n")
    print(f"{'':<18}{'right tools':>12}{'wrong picks/ask':>17}{'picks/ask':>11}")
    for arm, r in rows.items():
        cov = sum(x[0] for x in r) / n
        noise = sum(x[1] for x in r) / n
        size = sum(x[2] for x in r) / n
        print(f"{arm:<18}{cov:>11.0%}{noise:>17.1f}{size:>11.1f}")
    return rows


if __name__ == "__main__":
    main()
