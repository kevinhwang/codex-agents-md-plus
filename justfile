# Local install / dev targets for codex-agents-md-plus.

# Default: list targets.
default:
    @just --list

# Run the test suite.
test:
    python3 -m pytest -q

# Apply ruff formatting in place.
format:
    ruff format .

# Check formatting + lint (matches CI).
lint:
    ruff format --check .
    ruff check .

# AST-parse the hook sources (cheap smoke test).
syntax-check:
    @python3 -c 'import ast, glob; [ast.parse(open(p).read()) for p in sorted(glob.glob("plugins/codex-agents-md-plus/src/agents_md_plus/*.py"))]; print("OK")'

# JSON-parse plugin manifest, marketplace, and hooks files.
manifest-check:
    @python3 -c "import json; [json.load(open(p)) for p in ('.agents/plugins/marketplace.json','plugins/codex-agents-md-plus/.codex-plugin/plugin.json','plugins/codex-agents-md-plus/hooks/hooks.json')]; print('OK')"

# Smoke-test the hook against a Codex-style payload using the current repo as cwd.
smoke-test:
    @printf '{"session_id":"s","transcript_path":null,"cwd":"%s","hook_event_name":"SessionStart","model":"gpt-test","permission_mode":"workspace-write","source":"startup"}\n' "$(pwd)" \
      | python3 plugins/codex-agents-md-plus/src/hook.py

# Register this directory as a Codex marketplace and install the plugin.
install:
    codex plugin marketplace add "$(pwd)"
    codex plugin add codex-agents-md-plus@codex-agents-md-plus

# Uninstall the Codex plugin and remove the marketplace registration.
uninstall:
    codex plugin remove codex-agents-md-plus@codex-agents-md-plus
    codex plugin marketplace remove codex-agents-md-plus
