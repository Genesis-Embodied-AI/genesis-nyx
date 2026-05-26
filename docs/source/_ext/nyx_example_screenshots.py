"""Run each example script at doc-build time and capture its output artifacts.

Why an extension rather than a separate CI step:

The user-guide example pages (``user_guide/examples/*.md``) embed each script
via ``literalinclude`` and reference matching artifacts under
``_static/generated/examples/<script-stem>.{png,mp4}``. We want both to be
regenerated automatically every time the docs are built so they never go out
of sync with the script source. Driving it from a Sphinx extension means
``sphinx-build`` (and therefore ``docs/scripts/build_version.py`` in CI) is
the single entry point.

What gets captured
------------------

For each ``<examples_dir>/<script>.py`` matched by ``nyx_examples_pattern``:

* **PNG (still image)**: :mod:`docs.scripts.run_example` runs the script in a
  subprocess and intercepts :meth:`PIL.Image.Image.save` to capture the first
  frame written. See that module for details.

* **MP4 (video)**: scripts that record a video must write it to
  ``<examples_dir>/out/<script-stem>.mp4``. After the subprocess exits this
  extension copies the file to ``<screenshots_dir>/<stem>.mp4``. The check is
  filesystem-based so it works whether the example ran fresh in this build,
  ran previously, or was pre-committed.

Configuration values (set in ``conf.py``):

``nyx_examples_dir``
    Directory containing the example scripts. Defaults to
    ``<repo>/examples`` (two parents up from the Sphinx source dir).

``nyx_screenshots_dir``
    Where captured PNGs / MP4s land. Defaults to
    ``<srcdir>/_static/generated/examples``. The Sphinx static-file machinery
    picks them up automatically because ``_static`` is on
    ``html_static_path``.

``nyx_examples_pattern``
    Glob applied inside ``nyx_examples_dir``. Defaults to ``[0-9]*_*.py``,
    matching the ``NN_name.py`` convention used by the example set.

``nyx_examples_timeout``
    Per-script subprocess timeout in seconds. Defaults to 600.

Environment overrides:

``NYX_SKIP_EXAMPLE_SCREENSHOTS=1``
    Skip the whole step. Useful for fast local doc iteration when you know
    the artifacts on disk are already current, or on a CPU-only machine
    where the renderer can't run.

MyST substitutions:

For every example matched by ``nyx_examples_pattern``, the extension defines
two MyST substitutions:

* ``example_<stem>_screenshot``, either Markdown for an inline image (PNG
  present) or an empty string.
* ``example_<stem>_video``, either a ``{video}`` directive block (MP4 present)
  or an empty string.

Pages embed ``{{ example_<stem>_screenshot }}`` and / or
``{{ example_<stem>_video }}`` so a missing artifact degrades to nothing
rather than failing the build.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.util import logging

LOGGER = logging.getLogger(__name__)

_RUNNER = Path(__file__).resolve().parents[2] / "scripts" / "run_example.py"


def _resolve_paths(app: Sphinx) -> tuple[Path, Path, str, int]:
    srcdir = Path(app.srcdir).resolve()
    default_examples_dir = srcdir.parents[1] / "examples"
    default_screenshots_dir = srcdir / "_static" / "generated" / "examples"

    examples_dir = Path(app.config.nyx_examples_dir or default_examples_dir).resolve()
    screenshots_dir = Path(
        app.config.nyx_screenshots_dir or default_screenshots_dir
    ).resolve()
    pattern = app.config.nyx_examples_pattern or "[0-9]*_*.py"
    timeout = int(app.config.nyx_examples_timeout or 600)
    return examples_dir, screenshots_dir, pattern, timeout


def _capture_one(script: Path, out_png: Path, timeout: int) -> int:
    """Run a single example script via the runner; return its exit code."""
    cmd = [sys.executable, str(_RUNNER), str(script), "--out", str(out_png)]
    LOGGER.info("[nyx-screenshots] %s, %s", script.name, out_png.name)
    try:
        completed = subprocess.run(
            cmd,
            timeout=timeout,
            check=False,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        LOGGER.warning(
            "[nyx-screenshots] %s timed out after %ds; no artifacts captured",
            script.name,
            timeout,
            type="nyx_example_screenshots",
        )
        return 124

    if completed.stdout:
        for line in completed.stdout.rstrip().splitlines():
            LOGGER.info("[nyx-screenshots] %s: %s", script.name, line)
    if completed.stderr:
        for line in completed.stderr.rstrip().splitlines():
            LOGGER.info("[nyx-screenshots] %s (stderr): %s", script.name, line)
    return completed.returncode


def _collect_video(script: Path, examples_dir: Path, screenshots_dir: Path) -> bool:
    """Copy ``<examples_dir>/out/<stem>.mp4`` to ``<screenshots_dir>/<stem>.mp4``.

    Returns True if the destination ended up with a video on disk.
    """
    src = examples_dir / "out" / f"{script.stem}.mp4"
    dst = screenshots_dir / f"{script.stem}.mp4"
    if src.is_file():
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        LOGGER.info("[nyx-screenshots] %s: copied video %s", script.name, dst.name)
        return True
    return dst.is_file()


def _publish_substitutions(
    config: Any, scripts: list[Path], screenshots_dir: Path
) -> None:
    """Register ``example_<stem>_{screenshot,video}`` substitutions from disk state.

    Driven from filesystem state (rather than runner return codes) so
    pre-committed artifacts are honoured even when
    ``NYX_SKIP_EXAMPLE_SCREENSHOTS=1``.
    """
    subs = dict(getattr(config, "myst_substitutions", None) or {})
    for script in scripts:
        stem = script.stem

        png_path = screenshots_dir / f"{stem}.png"
        # Leading slash, Sphinx resolves this from the source root, which
        # makes the same Markdown work regardless of how deeply the page
        # lives in the tree.
        if png_path.is_file():
            url = f"/_static/generated/examples/{stem}.png"
            subs[f"example_{stem}_screenshot"] = (
                f"![Rendered output of `{script.name}`]({url})"
            )
        else:
            subs[f"example_{stem}_screenshot"] = ""

        mp4_path = screenshots_dir / f"{stem}.mp4"
        if mp4_path.is_file():
            url = f"/_static/generated/examples/{stem}.mp4"
            # Multi-line MyST substitution that expands to a ``{video}``
            # directive (sphinxcontrib-video). ``autoplay`` + ``muted`` are
            # required together for modern browsers to actually start
            # playback on page load.
            subs[f"example_{stem}_video"] = "\n".join(
                [
                    f":::{{video}} {url}",
                    ":width: 100%",
                    ":autoplay:",
                    ":muted:",
                    ":loop:",
                    ":playsinline:",
                    ":::",
                ]
            )
        else:
            subs[f"example_{stem}_video"] = ""

    config.myst_substitutions = subs


def _run_all(_app: Sphinx, config: Any) -> None:
    examples_dir, screenshots_dir, pattern, timeout = _resolve_paths(_app)
    if not examples_dir.is_dir():
        LOGGER.warning(
            "[nyx-screenshots] examples directory %s does not exist; skipping",
            examples_dir,
            type="nyx_example_screenshots",
        )
        return

    scripts = sorted(examples_dir.glob(pattern))
    if not scripts:
        LOGGER.warning(
            "[nyx-screenshots] no example scripts matched %s in %s",
            pattern,
            examples_dir,
            type="nyx_example_screenshots",
        )
        return

    skip = os.environ.get("NYX_SKIP_EXAMPLE_SCREENSHOTS") == "1"
    if skip:
        LOGGER.info(
            "[nyx-screenshots] NYX_SKIP_EXAMPLE_SCREENSHOTS=1 set; "
            "leaving any existing artifacts in place."
        )
    else:
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        for script in scripts:
            out_png = screenshots_dir / f"{script.stem}.png"
            rc = _capture_one(script, out_png, timeout)
            captured_video = _collect_video(script, examples_dir, screenshots_dir)

            if rc == 0:
                continue
            if rc == 2 and captured_video:
                # Script wrote a video but never called Image.save, that's
                # fine, the user-guide page embeds the video.
                continue
            if rc == 2:
                LOGGER.warning(
                    "[nyx-screenshots] %s ran but produced no PNG or MP4; "
                    "user-guide page will render without media",
                    script.name,
                    type="nyx_example_screenshots",
                )
            elif out_png.is_file() or captured_video:
                # The render path succeeded — PNG/MP4 is already on disk —
                # but the script exited non-zero on the way out. Currently
                # observed: the Nyx Python SDK's memory-leak detector
                # asserts at shutdown when CoACD convex decomposition has
                # touched its memory globals, taking the process down with
                # SIGSEGV after the artifact was captured. Treat as a
                # shutdown crash, not a render failure, so the docs build
                # under ``-W`` doesn't fail on something the deployed page
                # will render correctly. Drop this branch once the upstream
                # assert is downgraded to a log.
                LOGGER.info(
                    "[nyx-screenshots] %s exited with code %d after capturing "
                    "its artifact; treating as shutdown-only failure",
                    script.name,
                    rc,
                )
            else:
                LOGGER.warning(
                    "[nyx-screenshots] %s exited with code %d; "
                    "see the [nyx-screenshots] log lines above",
                    script.name,
                    rc,
                    type="nyx_example_screenshots",
                )

    _publish_substitutions(config, scripts, screenshots_dir)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value("nyx_examples_dir", None, "env")
    app.add_config_value("nyx_screenshots_dir", None, "env")
    app.add_config_value("nyx_examples_pattern", "[0-9]*_*.py", "env")
    app.add_config_value("nyx_examples_timeout", 600, "env")

    # ``config-inited`` fires once configuration is fully loaded but before
    # Sphinx starts reading source files, which is the right moment to
    # populate ``_static/generated/``, the static-file collector will pick
    # the artifacts up later in the build.
    app.connect("config-inited", _run_all)

    return {
        "version": "0.2.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
