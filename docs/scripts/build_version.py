"""Build the Sphinx docs for a single gs-nyx version into a target directory.

Used by the CI workflow. Can also be invoked locally:

    python docs/scripts/build_version.py \\
        --version 0.1.0 \\
        --extra-index-url https://user:token@host/.../simple \\
        --output-dir public/v0.1.0

When ``--version`` is ``dev`` (or ``latest``), the script skips the pip-install
step and builds against whichever ``gs-nyx`` is already installed in the
current environment.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_SOURCE = REPO_ROOT / "docs" / "source"
GENERATED_API = DOCS_SOURCE / "api_reference" / "generated"


def install_wheel(version: str, extra_index_url: str | None) -> None:
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", f"gs-nyx=={version}"]
    if extra_index_url:
        cmd.extend(["--extra-index-url", extra_index_url])
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def check_api_examples() -> None:
    """Verify every API-reference example sidecar compiles + runs.

    Run before ``sphinx-build`` so a broken snippet fails fast with the
    real Python traceback instead of an obscure rST warning later in the
    pipeline.
    """
    script = REPO_ROOT / "docs" / "scripts" / "check_api_examples.py"
    cmd = [sys.executable, str(script)]
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def build_html(version: str, output_dir: Path, switcher_url: str | None) -> None:
    if GENERATED_API.exists():
        shutil.rmtree(GENERATED_API)

    check_api_examples()

    env = os.environ.copy()
    env["DOCS_VERSION"] = version
    if switcher_url:
        env["DOCS_SWITCHER_URL"] = switcher_url

    cmd = [
        sys.executable,
        "-m",
        "sphinx",
        "-b",
        "html",
        "-W",
        "--keep-going",
        str(DOCS_SOURCE),
        str(output_dir),
    ]
    print(f"+ DOCS_VERSION={version} {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        required=True,
        help="gs-nyx version to install and document. Use 'dev' or 'latest' to "
             "skip installation and build against the currently-installed package.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory to write the built HTML into. Will be removed if it already exists.",
    )
    parser.add_argument(
        "--extra-index-url",
        default=os.environ.get("PIP_EXTRA_INDEX_URL"),
        help="Pip --extra-index-url, typically the internal JFrog PyPI repo. "
             "Defaults to $PIP_EXTRA_INDEX_URL.",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Skip the pip-install step and build against the currently-installed "
             "gs-nyx. --version is still used to stamp DOCS_VERSION in the build.",
    )
    parser.add_argument(
        "--switcher-url",
        default=None,
        help="Override the version-switcher JSON URL embedded in the built docs.",
    )
    args = parser.parse_args()

    skip_install = args.no_install or args.version in {"dev", "latest"}
    if not skip_install:
        install_wheel(args.version, args.extra_index_url)

    if args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    build_html(args.version, args.output_dir, args.switcher_url)
    print(f"Built docs for gs-nyx {args.version} into {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
