"""Verify every API-reference example sidecar compiles and runs.

Walks ``docs/source/api_reference/_examples/*.rst``, extracts each
``.. code-block:: python`` block from those files, and ``exec()``s it in
a fresh namespace. Returns a non-zero exit code if any block fails to
compile or raises at runtime, so the docs build never ships a broken
snippet to users.

The examples are pure ``gs_nyx`` SDK calls (no GPU, no renderer
boot), so a CPU-only environment that can ``import
gs_nyx.nyx_py_sdk`` is enough to run the check. The script is wired
into ``docs/Makefile``, ``docs/make.bat`` and
``docs/scripts/build_version.py`` so any docs build runs it
automatically; it can also be invoked directly:

    python docs/scripts/check_api_examples.py
"""

from __future__ import annotations

import re
import sys
import traceback
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "docs" / "source" / "api_reference" / "_examples"


_NYX_TEST_RE = re.compile(r"^\s*\.\.\s*nyx-test\s*:\s*(\S+)\s*$")


def extract_python_blocks(text: str) -> list[tuple[str, str]]:
    """Return ``(mode, source)`` tuples for every ``.. code-block:: python``.

    ``mode`` is ``"exec"`` (default) or ``"compile-only"``, set by an
    immediately-preceding rST comment of the form
    ``.. nyx-test: compile-only``. The comment uses a single colon so rST
    treats it as an inert comment (no Sphinx warning) while still being
    cheap to scan here.

    The parser is line-based rather than docutils-driven so the script has
    no Sphinx dependency, but it follows the standard rST directive rules:
    options on lines starting with ``:``, a blank separator line, then an
    indented body that ends at the first dedented non-blank line.
    """
    lines = text.splitlines()
    blocks: list[tuple[str, str]] = []
    pending_mode = "exec"
    i = 0
    while i < len(lines):
        marker = _NYX_TEST_RE.match(lines[i])
        if marker:
            pending_mode = marker.group(1)
            i += 1
            continue
        if lines[i].strip() != ".. code-block:: python":
            # Anything other than blanks between marker and directive resets
            # the mode — the marker only applies to the very next block.
            if lines[i].strip() != "":
                pending_mode = "exec"
            i += 1
            continue
        mode = pending_mode
        pending_mode = "exec"
        i += 1

        # Skip directive options (``:emphasize-lines: ...``, ``:linenos:``, ...).
        while i < len(lines) and lines[i].lstrip().startswith(":"):
            i += 1

        # Skip the blank line separating the directive header from its body.
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        if i >= len(lines):
            break

        indent_match = re.match(r"^(\s+)", lines[i])
        if not indent_match:
            continue
        indent = indent_match.group(1)

        body: list[str] = []
        while i < len(lines):
            cur = lines[i]
            if cur.strip() == "":
                body.append("")
                i += 1
            elif cur.startswith(indent):
                body.append(cur[len(indent):])
                i += 1
            else:
                break

        while body and body[0] == "":
            body.pop(0)
        while body and body[-1] == "":
            body.pop()

        blocks.append((mode, "\n".join(body)))
    return blocks


def main() -> int:
    if not EXAMPLES_DIR.is_dir():
        print(
            f"check_api_examples: no examples dir at {EXAMPLES_DIR}",
            file=sys.stderr,
        )
        return 0

    # Import the SDK up-front so a missing wheel fails with a clear
    # message rather than a per-snippet ImportError traceback. The
    # explicit ``startup()`` is what callers normally get for free via
    # ``gs.register_external_module``; here we run the snippets in a bare
    # namespace with no plugin layer, and string-typed asset fields (e.g.
    # ``EnvironmentMapAsset.texture``, ``LightFieldAsset.uri``) allocate
    # from an internal arena that segfaults if it has not been initialised.
    try:
        import gs_nyx.nyx_py_sdk as _nps
    except ImportError as exc:
        print(
            f"check_api_examples: cannot import gs_nyx.nyx_py_sdk ({exc}); "
            "install the gs-nyx-plugin wheel before running this check.",
            file=sys.stderr,
        )
        return 1
    _nps.startup()

    failures: list[tuple[Path, int, BaseException]] = []
    n_exec = 0
    n_compile = 0
    sidecars = sorted(EXAMPLES_DIR.glob("*.rst"))
    for sidecar in sidecars:
        blocks = extract_python_blocks(sidecar.read_text(encoding="utf-8"))
        for idx, (mode, block) in enumerate(blocks):
            try:
                code = compile(block, str(sidecar), "exec")
            except SyntaxError as exc:
                failures.append((sidecar, idx, exc))
                continue
            if mode == "compile-only":
                n_compile += 1
                continue
            n_exec += 1
            namespace: dict = {"__name__": "__nyx_api_example__"}
            try:
                exec(code, namespace)
            except BaseException as exc:  # noqa: BLE001
                failures.append((sidecar, idx, exc))

    print(
        f"check_api_examples: exec {n_exec} block(s), "
        f"compile-only {n_compile} block(s) from {len(sidecars)} sidecar(s)"
    )

    if failures:
        print("", file=sys.stderr)
        for sidecar, idx, exc in failures:
            rel = sidecar.relative_to(REPO_ROOT)
            print(f"FAILED {rel} (block {idx}):", file=sys.stderr)
            traceback.print_exception(
                type(exc), exc, exc.__traceback__, file=sys.stderr
            )
            print("", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
