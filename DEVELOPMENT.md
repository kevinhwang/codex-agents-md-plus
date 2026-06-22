# Development

The plugin itself is stdlib-only — no Python dependencies needed to install or run it. Dev tooling (`pytest`, `ruff`) is only required for working on the code.

## Dev environment

Recommended: [`uv`](https://docs.astral.sh/uv/) for a fast, isolated dev environment.

```shell
uv venv
source .venv/bin/activate
uv pip install pytest ruff
```

Plain `python -m venv` + `pip install pytest ruff` works too. The repo doesn't ship a lockfile; CI installs the latest of each.

## Commands

```shell
just test            # run pytest suite
just lint            # ruff format --check + ruff check (matches CI)
just format          # apply ruff format in place
just syntax-check    # AST-parse all sources (no-deps smoke test)
just manifest-check  # JSON-parse marketplace, plugin, hooks manifests
just smoke-test      # exercise the hook against a Codex-shaped stdin payload
```

CI runs `lint` → `manifest-check` → AST parse → `test` on every push/PR.

## Layout

```
.agents/plugins/marketplace.json                              -- local marketplace manifest
plugins/codex-agents-md-plus/
  .codex-plugin/plugin.json                                   -- plugin manifest
  hooks/hooks.json                                            -- SessionStart / SubagentStart hooks
  src/hook.py                                                 -- single-file entry point
  src/agents_md_plus/                                       -- python package (stdlib only)
  tests/                                                      -- per-module + end-to-end tests
```

Modules under `src/agents_md_plus/`:

| Module         | Responsibility                                                                                  |
|----------------|-------------------------------------------------------------------------------------------------|
| `config`       | Parse env vars into a `Config`.                                                                 |
| `models`       | Typed dataclasses + enums shared across modules.                                                |
| `paths`        | Path utilities (`normalize`, `chain_to`, `is_within_any`).                                      |
| `reader`       | Read a file under a byte budget.                                                                |
| `transcript`   | Read `session_meta.cwd` from a Codex rollout transcript.                                        |
| `gitworktree`  | Pure-Python `.git` linkfile parser → main worktree resolution.                                  |
| `hookio`       | `HookPayload` dataclass + stdin/stdout JSON protocol.                                           |
| `scanroots`    | Plan the primary/parallel directories to scan.                                                  |
| `instructions` | Per-directory file lookup (`AGENTS.override.md` / `AGENTS.md` / `AGENTS.local.md` + fallbacks). |
| `references`   | `@`-reference tokenizer (markdown-aware) + path resolver.                                       |
| `refgraph`     | BFS expansion of `@`-references with budget + cycle tracking.                                   |
| `nativepull`   | Predicate: "would Codex's native discovery have loaded this file?"                              |
| `overlay`      | Orchestrator: pipeline from scan roots through rendering.                                       |
| `renderer`     | Render an `Overlay` to the `additionalContext` markdown body + SHA-256 marker.                  |
| `main`         | Hook entry point: stdin → parse → build → render → stdout.                                      |
