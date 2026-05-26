"""Run a Nyx example script and capture its first rendered frame.

Used by the ``nyx_example_screenshots`` Sphinx extension so the user-guide
example pages can embed real screenshots without modifying the example
scripts themselves.

The mechanism:

1. Eagerly import :mod:`PIL.Image` so its module object exists in
   :data:`sys.modules` before the example runs.
2. Monkey-patch :meth:`PIL.Image.Image.save` so the first call also writes a
   copy to the screenshot path passed in ``--out``. Subsequent saves are
   passed through untouched (an example may legitimately save more than one
   image; we only want a single hero shot).
3. Execute the example via :func:`runpy.run_path` with ``run_name="__main__"``
   so its ``if __name__ == "__main__":`` block fires exactly as it would when
   the user runs ``python examples/01_hello_nyx.py`` directly.

The example file is not read, modified, or imported as a library; it runs in
its own module namespace with ``sys.argv`` rewritten to look like a direct
invocation, so any logic that keys off ``__file__`` or argv keeps working.

Exit codes:

* ``0``, the example ran to completion AND wrote a screenshot.
* ``2``, the example ran to completion but never called ``Image.save``
  (the user-guide page for this example can't show a screenshot; the Sphinx
  extension turns this into a warning).
* Anything else, the example itself crashed; stderr is forwarded.
"""

from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path


def _install_save_hook(out_path: Path) -> list[bool]:
    """Patch ``PIL.Image.Image.save`` so the first call also writes ``out_path``.

    Returns a single-element list whose only entry flips to ``True`` once a
    screenshot has been captured. A list (rather than a ``nonlocal`` bool) is
    used so the caller can inspect the flag after :func:`runpy.run_path`
    returns.
    """
    from PIL import Image  # noqa: WPS433, deferred until we know we'll use it.

    captured = [False]
    original_save = Image.Image.save

    def patched_save(self, fp, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = original_save(self, fp, *args, **kwargs)
        if not captured[0]:
            captured[0] = True
            out_path.parent.mkdir(parents=True, exist_ok=True)
            # Re-save through the original implementation to avoid re-entering
            # the hook and to sidestep any state the patched ``fp`` may have
            # consumed (file-like objects can be one-shot).
            original_save(self, str(out_path))
        return result

    Image.Image.save = patched_save  # type: ignore[method-assign]
    return captured


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="Example script to execute.")
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Where to write the captured screenshot PNG.",
    )
    args = parser.parse_args()

    script = args.script.resolve()
    if not script.is_file():
        print(f"run_example: no such script: {script}", file=sys.stderr)
        return 1

    out_path = args.out.resolve()
    captured = _install_save_hook(out_path)

    # Make the example see its own path as argv[0], the way a direct
    # ``python examples/foo.py`` invocation would.
    sys.argv = [str(script)]

    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:
        # Treat SystemExit(0) / SystemExit(None) as a clean run; anything else
        # propagates to the parent as a non-zero exit.
        code = exc.code
        if code not in (None, 0):
            return int(code) if isinstance(code, int) else 1

    if not captured[0]:
        print(
            f"run_example: {script.name} finished without calling Image.save; "
            f"no screenshot written to {out_path}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
