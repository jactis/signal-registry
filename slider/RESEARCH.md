# Slider as the entry point to plugins: research notes (2026-10-09)

The question: can Slider find, vet and load the right plugins, skills, MCP servers and workflow packs for each build, so users never browse a store?

**Answer:** Finding them is solved. Choosing well and loading safely are not, and those gaps are where Slider wins.

## What loads, and when (Claude Code today)

| What | When it's live | Can Slider do it alone? |
|---|---|---|
| Skills in `.claude/skills` or `~/.claude/skills` | This session (hot reload) | Yes |
| Plugins (`enabledPlugins` in user or `settings.local.json`) | Next start, or `/reload-plugins` | It can write the setting; the user reloads. Claude Code never installs without the user confirming. |
| MCP server via `claude mcp add` | After a restart, in practice (`list_changed` bugs reported) | Partly. A Slider-owned gateway with a changing tool list avoids the restart (Docker Dynamic MCP pattern). |

Gotchas:

- `enabledPlugins: true` in a repo's `.claude/settings.json` does not fetch an external plugin. It must be set in user settings, `settings.local.json`, `--settings` or managed settings.
- Cloud sessions don't show the workspace-trust dialog, so they never add a repo's marketplaces.
- `claude plugin install` refuses to run inside a session without a TTY unless `--accept-command <sha256>` is passed. `-y` is ignored in-session.
- `/reload-plugins` can invalidate the prompt cache. In `-p`, desktop and SDK sessions it works only when the user types it.
- Managed policy can block all of this: `strictKnownMarketplaces`, `blockedMarketplaces`, `allowManagedHooksOnly`, `strictPluginOnlyCustomization`. Slider must detect it and say so.
- Claude Code's built-in `relevance` suggestions match on cwd, CLI, hosts, files read and manifest deps.
  - They only suggest, at most once per three sessions.
  - They work only for admin-allowlisted marketplaces.
  - No official plugin uses them yet.
- Hooks cannot rewrite another plugin's `SKILL.md` as it loads; `additionalContext` only appends. The `mods` `skill.prompt` event is the candidate for that, still unverified (spike 1 in the alignment-loop spec).

Docs:

- https://code.claude.com/docs/en/plugins/loading
- https://code.claude.com/docs/en/plugins/cli-reference
- https://code.claude.com/docs/en/plugins/relevance
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/plugin-evals

## Supply

**Official Claude marketplace:** 315 plugins today (snapshot in `catalog/`).

| Category | Plugins |
|---|---|
| development | 123 |
| productivity | 69 |
| database | 39 |
| monitoring | 22 |
| security | 18 |

- 164 of the 315 come from outside repos.
- Most are pinned to a commit sha.
- Superpowers is listed.

**Wider ecosystem** (third-party counts, unverified):

- claudemarket.ai claims 3,688 plugins in 1,463 marketplaces.
- skills.sh lists skills from install telemetry, with no review.

**MCP Registry:**

- More than 20k entries.
- The API has been frozen at v0.1 ("preview") since October 2025.
- Search is substring only, with no ranking or quality signal.
- Namespace proof shows who published an entry, not who runs the endpoint.

**Smithery:** semantic search and a `useCount` field.

**Skills:** the agentskills.io spec is shared by Claude Code, Codex, Gemini CLI, Cursor and Copilot. `.agents/skills/` is becoming the common directory.

**Workflow packs:** Superpowers, GitHub Spec Kit, BMAD v6 and Anthropic `feature-dev` overlap, and all of them try to own planning. Nothing arbitrates between them.

## Trust: the reason popularity can't be the ranking

- **ClawHavoc / ClawHub (Jan–Feb 2026):** 341–1,184 malicious skills, pushed up the rankings with faked install counts.
- **Snyk ToxicSkills:** 13.4% of 3,984 skills had critical issues. Plain-language instructions can be the payload.
- **postmark-mcp 1.0.16:** an update added a hidden BCC to every email. Users pinned to an older version were safe.
- **Claude Code hook abuse:**
  - PromptArmor: a marketplace plugin's hook auto-approved `curl`.
  - The npm package `claude-jar` wrote hooks into `~/.claude/settings.json`.
  - Several trust-dialog CVEs, all fixed.
- There is no general signing for plugins or skills. NVIDIA signs its own skills with Sigstore.

**Signals Slider uses now:**

- official marketplace only
- tier: Anthropic, vendor or reviewed
- pinned sha
- whether the plugin needs an account

**Signals to add next:**

- whether it has hooks or MCP servers, and how much they can reach
- a diff check on every version bump
- an LLM read of skill text for injected instructions
- endpoint domain matches the publisher's namespace
- **outcomes met**

## Gaps nobody fills, which Slider can

1. **Choosing from the outcome.** Every catalog searches on keywords. Slider knows the locked outcome and what the proof step will need.
2. **Ranking by outcomes met.** Only Slider sees whether the build passed proof with a given kit. Every user adds to that ranking, and fake installs can't move it.
3. **Arbitration.** One method and one pick per need, so overlapping packs don't fight.
4. **Re-vetting on update.** A pinned version only moves to a new one after a diff review.
5. **Across agents.** Kits written as skills reach Codex, Cursor and Gemini through `.agents/skills`.

## Prototype status

`kit.py` and `eval/run.py`:

- Kit reaches 96% right-tools vs 38% for directory search over 24 asks.
- Wrong picks: 0.3 per ask vs 3.4.
- The labels are in-distribution, so this proves the method, not real-world accuracy.

Next steps:

1. Infer needs from the outcome card in-session, instead of from keywords.
2. Record each kit and its proof result in this registry, and rank on outcomes met.
3. Replay Jason's real past asks through the hidden-intent user, with and without a kit.
