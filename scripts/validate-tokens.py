#!/usr/bin/env python3
"""Enforce the BAi token contract.

A product theme may override only its theme layer. The `$locked` paths in the
core system are fixed ecosystem-wide, because cross-product consistency of
status colour, type scale and accessibility floors is a trust property.

Exits non-zero on violation. Wired into CI.
"""
from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "packages" / "tokens" / "src"
CORE = SRC / "bai-core.tokens.json"


def flatten(node: object, prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    if isinstance(node, dict):
        if "$value" in node:
            out[prefix] = node["$value"]
            return out
        for k, v in node.items():
            if k.startswith("$"):
                continue
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    return out


def main() -> int:
    if not CORE.exists():
        print(f"✖ core token file missing: {CORE}", file=sys.stderr)
        return 1

    core = json.loads(CORE.read_text())
    core_paths = flatten(core)
    errors: list[str] = []
    checked = 0

    for theme_file in sorted(SRC.glob("*.theme.json")) + sorted(SRC.glob("_*.theme.template.json")):
        theme = json.loads(theme_file.read_text())
        locked = theme.get("$locked", {}).get("paths", [])
        if not locked:
            errors.append(f"{theme_file.name}: no $locked block — theme contract missing")
            continue

        overrides = flatten({k: v for k, v in theme.items() if not k.startswith("$")})
        for path in overrides:
            for pattern in locked:
                if fnmatch.fnmatch(path, pattern):
                    errors.append(f"{theme_file.name}: '{path}' overrides locked path '{pattern}'")
            # a theme may only write under product.* or theme.*
            if not path.startswith(("product.", "theme.")):
                errors.append(
                    f"{theme_file.name}: '{path}' is outside the permitted theme layer"
                )
        checked += 1

    # every alias must resolve
    for path, value in core_paths.items():
        if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            target = value[1:-1]
            if target not in core_paths:
                errors.append(f"bai-core: '{path}' aliases '{target}', which does not exist")

    if errors:
        print(f"✖ token validation failed ({len(errors)} issue(s)):", file=sys.stderr)
        for e in errors:
            print(f"   {e}", file=sys.stderr)
        return 1

    print(f"✓ tokens valid — {len(core_paths)} core tokens, {checked} theme file(s), 0 violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
