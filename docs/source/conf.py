"""Sphinx configuration for the Nyx-for-Genesis documentation.

The API reference is generated entirely from the installed ``gs_nyx`` wheel
(docstrings + ``.pyi`` stubs produced by nanobind stubgen at build time). No
source checkout of the plugin is required or used.
"""

from __future__ import annotations

import enum
import os
import sys
from importlib import metadata
from pathlib import Path

# Local extensions live in ``_ext/`` next to this file.
sys.path.insert(0, str(Path(__file__).resolve().parent / "_ext"))


# -- Project information -----------------------------------------------------

project = "Nyx for Genesis"
author = "Genesis AI"
copyright = "2026, Genesis AI"

# DOCS_VERSION is injected by the CI workflow. Locally it's whatever is currently
# installed; falls back to "dev" if gs-nyx isn't present yet (e.g. early layout work).
try:
    _installed_version = metadata.version("gs-nyx")
except metadata.PackageNotFoundError:
    _installed_version = "dev"

release = os.environ.get("DOCS_VERSION", _installed_version)
version = release


# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_togglebutton",
    "myst_parser",
    "sphinx_subfigure",
    "sphinxcontrib.video",
    "nyx_example_screenshots",
    "nyx_api_examples",
    "nyx_nanobind",
]

templates_path = ["_templates"]
# ``api_reference/_examples`` holds rST sidecars consumed by the
# ``nyx_api_examples`` extension via ``autodoc-process-docstring``. They are
# read off disk and injected into the matching symbol's docstring; we exclude
# them from source discovery so Sphinx doesn't also render them as standalone
# "<no title>" orphan pages.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "api_reference/_examples",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- MyST --------------------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "amsmath",
    "deflist",
    "fieldlist",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 4


# -- Autodoc / autosummary ---------------------------------------------------

autosummary_generate = True
autosummary_imported_members = False

# NOTE: ``members`` is deliberately omitted so ``autoclass`` / ``automodule``
# don't inline member docs. Each class page lists members via ``autosummary``
# with ``:toctree:`` so every method and attribute gets its own dedicated page
# (Unity-style API layout).
autodoc_default_options = {
    "undoc-members": False,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"
autodoc_typehints_format = "short"
autoclass_content = "class"

# Modules to mock if the docs CI cannot import them on a CPU-only runner.
# Start empty: gs_nyx wheels should import cleanly even without a GPU, since
# autodoc never executes any rendering code. Add entries here only if a real
# build surfaces an ImportError.
#
# ``genesis`` is mocked because ``gs_nyx_plugin`` imports it at module load
# (``BaseCameraOptions``, ``BaseCameraSensor``, ``qd_to_torch``, etc.) and we
# don't want the docs build to depend on a working Genesis install — autodoc
# only needs the class objects, not their runtime behaviour.
#
# ``torch`` and ``trimesh`` are mocked for the same reason: ``gs_nyx_plugin``
# imports them at module top level, but pulling them into the docs venv just to
# satisfy ``import torch`` would bloat the CI install (torch alone is ~700 MB).
autodoc_mock_imports: list[str] = ["genesis", "torch", "trimesh"]

# Napoleon (Google + NumPy docstring styles)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_use_rtype = False
napoleon_use_param = True
# Render docstring "Attributes" sections as a ``:ivar:`` field list inside the
# class body instead of emitting a separate ``.. attribute::`` directive per
# field. The class template (custom-class-template.rst) already generates a
# dedicated page per attribute via autosummary, and napoleon's default
# ``.. attribute::`` output would re-register the same Python domain object,
# producing "duplicate object description" warnings for every dataclass that
# documents its fields in the class docstring (e.g. NyxCameraSharedMetadata).
napoleon_use_ivar = True


# -- Intersphinx -------------------------------------------------------------

intersphinx_mapping = {
    "python":  ("https://docs.python.org/3/", None),
    "numpy":   ("https://numpy.org/doc/stable/", None),
    "torch":   ("https://pytorch.org/docs/stable/", None),
    "genesis": ("https://genesis-world.readthedocs.io/en/latest/", None),
}


# -- HTML output -------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_title = project
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
templates_path = ["_templates"]

# The version switcher JSON is served from the root of the deployed site
# (gh-pages branch), not from per-version directories. The CI workflow keeps
# /_static/version_switcher.json on the site root in sync with the list of
# version subdirectories present in gh-pages.
_switcher_url = os.environ.get(
    "DOCS_SWITCHER_URL",
    "https://genesis-embodied-ai.github.io/nyx-for-genesis/_static/version_switcher.json",
)

html_theme_options = {
    # Monokai code blocks in both light and dark modes — keeps the embedded
    # `.. code-block::` / fenced-code styling consistent regardless of which
    # site theme the reader has selected.
    "pygments_light_style": "monokai",
    "pygments_dark_style": "monokai",
    "show_nav_level": 2,
    "navigation_depth": 4,
    "show_toc_level": 2,
    "use_edit_page_button": False,
    "search_as_you_type": True,
    "navbar_center": ["version-switcher", "navbar-nav"],
    "switcher": {
        "json_url": _switcher_url,
        "version_match": release,
    },
    # Don't fail the build if the switcher JSON is unreachable (e.g. during
    # the very first deploy, before gh-pages exists).
    "check_switcher": False,
    "show_version_warning_banner": True,
    "icon_links": [
        {
            "name": "Genesis",
            "url": "https://genesis-world.readthedocs.io/",
            "icon": "fa-solid fa-book",
        },
    ],
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version", "theme-version"],
}


# -- Misc --------------------------------------------------------------------

# Keep build deterministic: forbid implicit references that fail silently.
nitpicky = False  # flip on once API docstrings stabilise


# -- autodoc filtering -------------------------------------------------------

# Names inherited from ``int`` that leak onto every ``IntEnum`` / ``IntFlag``
# subclass — including the bindings (e.g. ``gs_nyx.nyx_py_sdk.EMaterialProperty``,
# declared with ``nb::is_arithmetic() + nb::is_flag()``). Without this filter,
# autosummary stubs a page for each one, producing a wave of "document isn't
# included in any toctree" warnings.
_INT_INHERITED_NAMES = frozenset(
    {
        "as_integer_ratio",
        "bit_count",
        "bit_length",
        "conjugate",
        "denominator",
        "from_bytes",
        "imag",
        "is_integer",
        "numerator",
        "real",
        "to_bytes",
    }
)


def _skip_int_inherited(_app, _what, name, obj, _skip, _options):
    # ``autodoc-skip-member`` is dispatched via ``emit_firstresult``: any
    # non-``None`` return short-circuits subsequent listeners *and* tells
    # autosummary how to treat the member. Returning ``False`` here would
    # force every non-matching member into the public list — including
    # private classes like ``_ReconSlot`` that autosummary would
    # otherwise filter out by the leading-underscore rule. We only ever
    # speak up to *skip* int-inherited names; everything else defers to
    # the default behaviour by returning ``None``.
    if name in _INT_INHERITED_NAMES and getattr(obj, "__objclass__", None) is int:
        return True
    return None


# Suppress the ``Enum(value, names=<not given>, *values, ...)`` constructor
# signature that autodoc pulls from ``enum.Enum.__init_subclass__`` for every
# nanobind-bound enum. It's never user-callable (the binding only exposes
# the named members) and just bloats every enum page.
def _strip_enum_signature(_app, what, _name, obj, _options, _signature, return_annotation):
    if what == "class" and isinstance(obj, type) and issubclass(obj, enum.Enum):
        return ("", return_annotation)
    return None


def setup(app):
    app.connect("autodoc-skip-member", _skip_int_inherited)
    app.connect("autodoc-process-signature", _strip_enum_signature)
