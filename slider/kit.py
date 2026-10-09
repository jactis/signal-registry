#!/usr/bin/env python3
"""slider kit: pick the few plugins a build needs, so the user doesn't have to.

    slider/kit.py "add stripe checkout to the landing page"            # show the kit
    slider/kit.py "..." --project ~/code/app                           # read the repo's stack too
    slider/kit.py "..." --project ~/code/app --apply                   # load it (next session)
    slider/kit.py --project ~/code/app --drop paypal                   # never suggest again
    slider/kit.py --project ~/code/app --undo                          # unload the last kit

A kit is one vetted pick per need, at most MAX_PICKS, chosen from the ask, the
repo's stack and what the proof step needs to show "done". Stdlib only.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "catalog" / "claude-plugins-official.json"
NEEDS = HERE / "needs.json"
MARKETPLACE = "claude-plugins-official"
MAX_PICKS = 4  # beyond the build method; more than this is a menu, not a kit

# A fix works on what the repo already has; it shouldn't add new services.
FIX_WORDS = ["fix", "bug", "broken", "crash", "error", "fails", "failing", "keeps", "slow", "regression", "not working", "doesn't work"]


def load():
    catalog = {p["name"]: p for p in json.loads(CATALOG.read_text())["plugins"]}
    needs = json.loads(NEEDS.read_text())["needs"]
    return catalog, needs


# ---------- sensing ----------

def sense_stack(project):
    """Dependency names and root file names: cheap, local, no network."""
    if not project:
        return set()
    root = Path(project)
    found = {p.name for p in root.iterdir()} if root.is_dir() else set()
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text())
            for key in ("dependencies", "devDependencies"):
                found |= set(data.get(key, {}))
        except ValueError:
            pass
    for req in ("requirements.txt", "pyproject.toml"):
        f = root / req
        if f.is_file():
            for m in re.finditer(r"^\s*\"?([A-Za-z0-9_.\-]+)", f.read_text(), re.M):
                found.add(m.group(1).lower())
    return found


def taste_path(project):
    return Path(project or ".") / ".slider" / "taste.json"


def read_taste(project):
    try:
        return json.loads(taste_path(project).read_text())
    except (OSError, ValueError):
        return {"dropped": [], "kept": []}


def installed(project):
    names = set()
    paths = [Path.home() / ".claude" / "settings.json"]
    if project:
        paths += [Path(project) / ".claude" / n for n in ("settings.json", "settings.local.json")]
    for p in paths:
        try:
            for key, on in json.loads(p.read_text()).get("enabledPlugins", {}).items():
                if on:
                    names.add(key.split("@")[0])
        except (OSError, ValueError):
            pass
    return names


# ---------- choosing ----------

def hits(words, text):
    return [w for w in words if re.search(r"(?<![a-z])" + re.escape(w), text)]


def trust(plugin):
    src = plugin.get("source")
    author = (plugin.get("author") or {}).get("name", "")
    if author == "Anthropic" or isinstance(src, str):
        tier = "Anthropic"
    else:
        url = src.get("url", "")
        org = url.split("github.com/")[-1].split("/")[0].lower() if "github.com/" in url else ""
        tier = "vendor" if org and (org in plugin["name"] or plugin["name"].split("-")[0] in org) else "reviewed"
    pinned = isinstance(src, str) or bool(src.get("sha"))
    return tier, pinned


def choose(ask, stack, catalog, needs, taste, have):
    text = " " + ask.lower() + " "
    fixing = bool(hits(FIX_WORDS, text))
    fired = []
    for n in needs:
        ask_hits = hits(n.get("ask", []), text)
        stack_hits = [s for s in n.get("stack", []) if s in stack]
        if fixing and n.get("domain") and not stack_hits:
            continue
        if n.get("always") or ask_hits:
            fired.append((n, len(ask_hits) * 2 + len(stack_hits), ask_hits, stack_hits))
    # The proof step needs to see a UI to call it done.
    ids = {n["id"] for n, *_ in fired}
    if ids & {"ui", "payments", "auth"} and "browser" not in ids:
        b = next(n for n in needs if n["id"] == "browser")
        fired.append((b, 1, ["proof"], []))

    fired.sort(key=lambda f: (not f[0].get("always"), -f[1]))
    kit, skipped = [], []
    for n, score, ask_hits, stack_hits in fired:
        options = [p for p in n["picks"] if p in catalog and p not in taste["dropped"]]
        for dep, name in n.get("stack_pick", {}).items():
            if dep in stack and name in options:
                options.remove(name)
                options.insert(0, name)
        options.sort(key=lambda p: p not in taste["kept"])  # stable: keeps editorial order otherwise
        if not options:
            continue
        name = options[0]
        p = catalog[name]
        tier, pinned = trust(p)
        reason = "stack: " + ", ".join(stack_hits) if stack_hits and n.get("stack_pick") else (
            "needed to prove it works" if ask_hits == ["proof"] else n["why"])
        entry = {
            "need": n["label"], "plugin": name, "why": reason, "tier": tier, "pinned": pinned,
            "login": bool(n.get("account")), "have": name in have,
            "alternatives": options[1:3], "install": f"{name}@{MARKETPLACE}",
        }
        if len([k for k in kit if not k.get("method")]) >= MAX_PICKS and not n.get("always"):
            skipped.append(entry)
            continue
        entry["method"] = bool(n.get("always"))
        kit.append(entry)
    return kit, skipped


# ---------- acting ----------

def apply(project, kit):
    """Local-scope enable: fetched on next start, kept out of the repo, undoable."""
    root = Path(project)
    settings = root / ".claude" / "settings.local.json"
    settings.parent.mkdir(exist_ok=True)
    data = json.loads(settings.read_text()) if settings.is_file() else {}
    enabled = data.setdefault("enabledPlugins", {})
    added = [k["install"] for k in kit if not k["have"] and not enabled.get(k["install"])]
    for key in added:
        enabled[key] = True
    settings.write_text(json.dumps(data, indent=2) + "\n")
    state = root / ".slider"
    state.mkdir(exist_ok=True)
    (state / "kit.json").write_text(json.dumps({"added": added, "kit": kit}, indent=2) + "\n")
    return added


def undo(project):
    root = Path(project)
    last = json.loads((root / ".slider" / "kit.json").read_text())
    settings = root / ".claude" / "settings.local.json"
    data = json.loads(settings.read_text())
    for key in last["added"]:
        data.get("enabledPlugins", {}).pop(key, None)
    settings.write_text(json.dumps(data, indent=2) + "\n")
    return last["added"]


def remember(project, field, name):
    taste = read_taste(project)
    other = "kept" if field == "dropped" else "dropped"
    taste[other] = [n for n in taste[other] if n != name]
    if name not in taste[field]:
        taste[field].append(name)
    path = taste_path(project)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(taste, indent=2) + "\n")


def render(kit, skipped):
    lines = []
    for k in kit:
        badge = k["tier"] + (" · pinned" if k["pinned"] else "")
        mark = "✓" if k["have"] else "+"
        lines.append(f" {mark} {k['need']:<26} {k['plugin']:<22} {k['why']}")
        lines.append(f"   {'':<26} {'':<22} {badge}" + ("  · asks for your login once" if k["login"] else ""))
    if skipped:
        lines.append(" … also relevant, held back to keep it small: " + ", ".join(s["plugin"] for s in skipped))
    lights = [k["plugin"] for k in kit if k["login"] and not k["have"]]
    lines.append("")
    lines.append(" ● needs you: sign in to " + ", ".join(lights) if lights else " Nothing needs you.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ask", nargs="?", default="")
    ap.add_argument("--project")
    ap.add_argument("--stack", default="", help="comma-separated deps, instead of reading --project")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", action="store_true")
    ap.add_argument("--drop")
    ap.add_argument("--keep")
    a = ap.parse_args(argv)

    if a.drop or a.keep:
        remember(a.project, "dropped" if a.drop else "kept", a.drop or a.keep)
        print(f"Got it: {'never suggesting' if a.drop else 'preferring'} {a.drop or a.keep}.")
        return 0
    if a.undo:
        print("Unloaded: " + (", ".join(undo(a.project)) or "nothing"))
        return 0

    catalog, needs = load()
    stack = sense_stack(a.project) | {s.strip() for s in a.stack.split(",") if s.strip()}
    kit, skipped = choose(a.ask, stack, catalog, needs, read_taste(a.project), installed(a.project))
    if a.json:
        print(json.dumps({"kit": kit, "held_back": skipped}, indent=2))
    else:
        print(render(kit, skipped))
    if a.apply:
        if not a.project:
            sys.exit("--apply needs --project")
        added = apply(a.project, kit)
        print(f"\n Loaded {len(added)} for next session (or type /reload-plugins).  undo: --undo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
