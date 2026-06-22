#!/usr/bin/env python3
"""Codex hook entry point.

Bootstraps `sys.path` so the bundled `agents_md_plus` package is importable
when Codex invokes this script with `python3 ${PLUGIN_ROOT}/src/hook.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents_md_plus.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
