# signal-registry

Public rule packs for [Signal](https://github.com/jactis/signal) — a LiteLLM proxy that learns your Claude Code preferences and shares prompt-cache warmth across sessions.

## What this is

Signal's attunement daemon extracts preference rules from your sessions (e.g. "Always use absolute imports in pipeline.py"). This registry lets engineers share curated packs of those rules so new Signal installs start warm, not cold.

## Using packs

```bash
signal-share pull --topic python-tests     # import a curated pack
signal-share pull --topic commit-style     # another pack
signal-share submit my-rules.json          # open a PR with your rules
```

## Pack format

Each pack lives in a subdirectory under `packs/`:

```
packs/
  python-tests/
    pack.yaml
    rules.json
  commit-style/
    pack.yaml
    rules.json
```

**`pack.yaml`**
```yaml
name: python-tests
version: "1.0"
description: Rules for writing pytest suites with Claude Code
topics:
  - python
  - testing
  - pytest
maintainer: jactis
signal_min_version: "1.0"
```

**`rules.json`** — array of Signal schema v2 rule objects:
```json
[
  {
    "rule": "Always use pytest fixtures over setup/teardown methods",
    "project": null,
    "user": null,
    "hits": 0,
    "friction_delta": null,
    "last_seen": null,
    "source_trace_id": null,
    "polarity": "positive"
  }
]
```

Rules must have `project: null` and `user: null` (anonymized). Rules referencing specific file paths, repo names, or internal hostnames are rejected at submission time.

## Submitting rules

1. Export your rules: `signal-traces attunement export --anonymize > my-rules.json`
2. Submit: `signal-share submit my-rules.json --topic python-tests`

This opens a GitHub PR. A maintainer reviews and merges. Curation is editorial.

## Safety

- `signal-share pull` runs Signal's extraction quality gate on every imported rule before writing it to `preferences.json`
- Rules matching "tool-breaking" or "meta-instruction" patterns are dropped with a warning
- All rules in this registry must have `project: null` and `user: null`

## Available packs

| Pack | Topics | Rules | Description |
|------|--------|-------|-------------|
| [commit-style](packs/commit-style/) | commit, git | 5 | Conventional commit conventions |
| [python-tests](packs/python-tests/) | python, testing, pytest | 4 | pytest best practices |
