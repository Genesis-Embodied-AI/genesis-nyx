"""Inject curated rST example snippets into autodoc-rendered docstrings.

The plugin's nanobind bindings live in a separate source tree and we don't
want to bloat their inline docstrings with prose, so per-symbol examples
live as ``.rst`` sidecar files under
``docs/source/api_reference/_examples/`` and are appended to autodoc's
output at build time.

Convention
----------

* One file per documented symbol, named by **fully-qualified** Python name
  with ``.rst`` extension. Examples:

      _examples/gs_nyx.math.quat_conjugate.rst
      _examples/gs_nyx.NyxCameraOptions.rst
      _examples/gs_nyx.NyxCameraOptions.lookat.rst

* Contents are appended verbatim to the autodoc docstring after a single
  blank line. Standard rST applies , ``literalinclude``, ``code-block``,
  cross-refs, admonitions, etc. all work.

* Sidecars whose name does not match any documented symbol during the
  build trigger a Sphinx warning at the end of the build (catches typos
  and upstream renames that silently dropped the example).

The extension is intentionally tiny: it owns no rendering or formatting
decisions. Authors compose the example as they would any other rST.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.util import logging

LOGGER = logging.getLogger(__name__)

_EXAMPLES_SUBDIR = Path("api_reference") / "_examples"


def _examples_dir(app: Sphinx) -> Path:
    return Path(app.srcdir) / _EXAMPLES_SUBDIR


def _on_builder_inited(app: Sphinx) -> None:
    """Snapshot the set of sidecar files so we can detect orphans later."""
    examples_dir = _examples_dir(app)
    if not examples_dir.is_dir():
        app.env.nyx_api_examples_unused = set()
        return
    app.env.nyx_api_examples_unused = {
        path.stem for path in examples_dir.glob("*.rst")
    }


def _on_process_docstring(
    app: Sphinx,
    what: str,
    name: str,
    _obj: Any,
    _options: Any,
    lines: list[str],
) -> None:
    """Append the matching sidecar (if any) to ``name``'s docstring.

    Class-level sidecars are deliberately skipped here: appending them
    to the class docstring would place the prose between the class
    docstring and the Methods / Attributes rubrics. The class page
    template instead renders ``.. nyx-class-example:: <fullname>``
    (registered by :mod:`nyx_nanobind`) below the ``autoclass`` block,
    so the prose lands at the bottom of the page. We still discard the
    sidecar from the orphan-tracking set so the end-of-build check
    doesn't flag it as unmatched.
    """
    examples_dir = _examples_dir(app)
    sidecar = examples_dir / f"{name}.rst"
    if not sidecar.is_file():
        return

    unused: set[str] = getattr(app.env, "nyx_api_examples_unused", set())
    unused.discard(name)

    if what == "class":
        # Owned by ``.. nyx-class-example::``; see the docstring above.
        return

    if lines and lines[-1] != "":
        lines.append("")
    lines.extend(sidecar.read_text(encoding="utf-8").splitlines())


def _on_build_finished(app: Sphinx, _exception: Exception | None) -> None:
    unused: set[str] = getattr(app.env, "nyx_api_examples_unused", set()) or set()
    for stem in sorted(unused):
        LOGGER.warning(
            "[nyx-api-examples] sidecar %s.rst matched no documented symbol "
            "(typo or upstream rename?)",
            stem,
            type="nyx_api_examples",
        )


def setup(app: Sphinx) -> dict[str, Any]:
    app.connect("builder-inited", _on_builder_inited)
    app.connect("autodoc-process-docstring", _on_process_docstring)
    app.connect("build-finished", _on_build_finished)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
