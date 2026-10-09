# slider kit

People don't know which plugins they need. Slider picks the few a build needs, loads them, and learns from what you keep.

```
$ slider/kit.py "let people pay monthly and save their notes" --project ~/code/app --apply

 + Build method               superpowers            test-first build, review loop, evidence before 'done'
 + Database                   supabase               stack: @supabase/supabase-js
 + Payments                   stripe                 vendor's own API knowledge, test-mode tooling
 + See it run in a browser    playwright             needed to prove it works

 ● needs you: sign in to supabase, stripe

 Loaded 4 for next session (or type /reload-plugins).  undo: --undo
```

## How it picks

1. **Needs, not keywords.** `needs.json` lists what a build can need: payments, sign-in, a browser for the proof step, and so on. Each need has the vetted plugins for it, best first. This list is the editorial layer.
2. **The repo decides between options.** If the repo already uses `@supabase/supabase-js`, the database pick is Supabase, not Neon.
3. **Fixing isn't building.** On "fix" or "crash", Slider loads tools only for services the repo already uses. It never adds new ones.
4. **The proof step gets what it needs.** If the work has a UI, a browser tool comes along so "done" can be shown, not claimed.
5. **Small on purpose.** At most 4 picks plus the build method. Anything else relevant is listed as held back.
6. **Taste sticks.** `--drop playwright` means it's never suggested again, and the next-best option takes its place. `--keep` prefers a pick.

## Trust

Every pick comes from the official Claude plugin marketplace (snapshot in `catalog/`, 315 plugins, 2026-10-09) and is labelled by tier:

- **Anthropic**: built by Anthropic.
- **vendor**: published by the service's own company.
- **reviewed**: listed in the marketplace, third-party.

**pinned** means the marketplace locks the plugin to a specific commit. Picks that connect to a service you sign in to are the only thing that lights up for you.

Loading writes `enabledPlugins` to the project's `.claude/settings.local.json`. That is local scope, so it stays out of git and is fetched on the next start. `--undo` reverses the last load.

## Eval

```
$ python3 slider/eval/run.py
24 vague asks · K=4
                   right tools  wrong picks/ask  picks/ask
slider kit                96%              0.3        2.7
directory search          38%              3.4        4.0
```

"Directory search" is what a user gets today from typing the ask into a plugin search box: the top 4 plugins by word overlap with name and description.

The labels were written by the same author as `needs.json`, so this checks the mechanism, not real-world accuracy. Known misses:

- Keyword brittleness: "scrape competitor **pricing page**s" pulls in Stripe, and "**signup** page" design pulls in Auth0.
- "my numbers in the spreadsheet don't add up" finds no data tool.

These are why need-inference should move to the session model in the product, using the outcome card. The kit engine keeps the deterministic parts: picking, trust and taste.
