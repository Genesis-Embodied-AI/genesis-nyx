"""Regenerate _static/version_switcher.json by inspecting a deployed site root.

The PyData Sphinx Theme reads the switcher JSON to populate the version
dropdown. We keep a single switcher file at the site root (not per-version) so
every build resolves the same list.

Expected layout of the site root (typically the gh-pages worktree):

    <root>/
        latest/
        stable/
        v0.1.0/
        v0.2.0/
        _static/version_switcher.json   <-- this script writes here

The script lists ``v*`` subdirectories, sorts them by semantic version, and
emits a JSON array compatible with PyData Sphinx Theme's switcher.

Usage:

    python docs/scripts/update_switcher.py \\
        --site-root public \\
        --base-url https://genesis-embodied-ai.github.io/nyx-for-genesis
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from packaging.version import InvalidVersion, Version


VERSION_DIR_RE = re.compile(r"^v(\d+\.\d+\.\d+(?:[.\-+].*)?)$")


def discover_versions(site_root: Path) -> list[Version]:
    versions: list[Version] = []
    for child in site_root.iterdir():
        if not child.is_dir():
            continue
        match = VERSION_DIR_RE.match(child.name)
        if not match:
            continue
        try:
            versions.append(Version(match.group(1)))
        except InvalidVersion:
            continue
    versions.sort(reverse=True)
    return versions


def build_switcher(versions: list[Version], base_url: str) -> list[dict[str, object]]:
    base_url = base_url.rstrip("/")
    entries: list[dict[str, object]] = []

    if versions:
        newest_stable = next((v for v in versions if not v.is_prerelease), None)
        if newest_stable is not None:
            entries.append(
                {
                    "name": f"stable (v{newest_stable})",
                    "version": str(newest_stable),
                    "url": f"{base_url}/stable/",
                    "preferred": True,
                }
            )

    entries.append(
        {
            "name": "latest (dev)",
            "version": "dev",
            "url": f"{base_url}/latest/",
        }
    )

    for v in versions:
        entries.append(
            {
                "name": f"v{v}",
                "version": str(v),
                "url": f"{base_url}/v{v}/",
            }
        )

    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site-root",
        type=Path,
        required=True,
        help="Directory containing v*/ subdirectories (typically a gh-pages worktree).",
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Public base URL of the deployed docs site, e.g. "
             "https://genesis-embodied-ai.github.io/nyx-for-genesis",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path. Defaults to <site-root>/_static/version_switcher.json.",
    )
    args = parser.parse_args()

    output = args.output or (args.site_root / "_static" / "version_switcher.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    versions = discover_versions(args.site_root)
    entries = build_switcher(versions, args.base_url)
    output.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} with {len(entries)} entries")
    for e in entries:
        print(f"  - {e['name']:<20} -> {e['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
