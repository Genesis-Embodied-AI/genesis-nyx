"""Teach autodoc/autosummary that nanobind ``nb_func`` / ``nb_method`` objects
are functions / methods, and render nanobind constructors Unity-style.

Background
----------

Nanobind binds free functions as instances of a custom ``nb_func`` type and
class methods as ``nb_method``. Both fail :func:`inspect.isfunction` and
:func:`inspect.isbuiltin`, so:

* ``FunctionDocumenter.can_document_member`` rejects ``nb_func``. The
  ``functions`` bucket in ``custom-module-template.rst`` stays empty and no
  per-function autosummary stubs are generated.
* For class members, ``MethodDocumenter`` (priority 1) and
  ``AttributeDocumenter`` (priority 10) both accept ``nb_method`` (since it
  passes ``inspect.isroutine`` *and* the generic attribute checks). The
  higher priority wins, so every ``nb_method`` ends up classified as an
  attribute and the ``methods`` bucket in ``custom-class-template.rst``
  stays empty too. Methods and data fields then render mixed together
  under a single "Attributes" rubric.

Side effects when this extension is off:

* Module pages render an empty "Functions" rubric (or omit it).
* Class pages list methods alongside fields under "Attributes" with no
  visual distinction.
* ``api_reference/_examples/<module>.<func>.rst`` sidecars never get
  attached to a real docstring, so ``nyx_api_examples`` reports them as
  orphans at the end of the build.

Constructor rendering
---------------------

Nanobind exposes each C++ constructor as an overload of ``__init__``. From
Python's side the result is a single ``nb_method`` whose ``__doc__`` is just
``sig1\\nsig2\\n...`` and whose introspected signature collapses to the
generic ``(*args, **kwargs)``. autodoc therefore renders the class header
as ``ClassName(*args, **kwargs)`` and never surfaces the per-overload
descriptions the C++ binding registered via ``nb::init<...>("docstring")``.

To produce a Unity-style "Constructors" section instead:

* The class signature is stripped for nanobind classes (the per-overload
  signatures live in the Constructors block, not the header).
* :class:`NanobindConstructorDirective` (``.. nb-constructor:: <class>``)
  reads ``__nb_signature__`` and emits one ``.. py:method::`` per overload
  on the dedicated ``<class>.__init__`` page. The first overload is
  indexed (so cross-refs resolve); the rest are siblings.
* :class:`NanobindConstructorSummaryDirective`
  (``.. nb-constructor-summary:: <class>``) renders an autosummary-style
  table of overloads on the class page itself, with the per-overload
  signature on the left and the per-overload docstring as the description.

What this extension registers
-----------------------------

* :class:`NanobindFunctionDocumenter` — priority +1 over the stock
  :class:`FunctionDocumenter`, recognises ``nb_func``.
* :class:`NanobindMethodDocumenter` — priority 12 (above
  :class:`AttributeDocumenter`'s 10 and :class:`PropertyDocumenter`'s 11
  to break any tie), recognises ``nb_method`` so class methods land in the
  ``methods`` autosummary bucket. Python ``property`` objects continue to
  be classified by :class:`PropertyDocumenter` and stay in attributes.
* :class:`NanobindEnumAttributeDocumenter` — priority 11, takes over from
  the stock :class:`AttributeDocumenter` for enum members and restores the
  per-member docstring that
  :class:`~sphinx.ext.autodoc.NonDataDescriptorMixin` would otherwise
  discard. Required because nanobind's
  ``.value(name, value, "docstring")`` populates ``member.__doc__`` but
  Sphinx never reads it for non-descriptor attributes.
* ``.. nb-constructor::`` and ``.. nb-constructor-summary::`` directives.
* ``autodoc-process-signature`` listener that strips the
  ``(*args, **kwargs)`` from nanobind class headers.
* A patched :meth:`AutosummaryRenderer.render` that injects
  ``is_nanobind_class`` into the per-class template context so
  ``custom-class-template.rst`` can gate the Constructors rubric.
"""

from __future__ import annotations

import enum
import importlib
import inspect
import re
from pathlib import Path
from typing import Any

import sphinx.ext.autodoc
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.ext.autodoc import AttributeDocumenter, FunctionDocumenter, MethodDocumenter
from sphinx.ext.autosummary import generate as _autosummary_generate
from sphinx.ext.autosummary.generate import AutosummaryRenderer
from sphinx.util import logging
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.inspect import safe_getattr
from sphinx.util.nodes import nested_parse_with_titles

LOGGER = logging.getLogger(__name__)


def _is_nanobind_function(obj: object) -> bool:
    return type(obj).__name__ == "nb_func"


def _is_nanobind_method(obj: object) -> bool:
    return type(obj).__name__ == "nb_method"


def _is_nanobind_class(cls: type) -> bool:
    """A nanobind-bound class owns its own ``__init__`` and that ``__init__``
    is an ``nb_method``. Plain Python subclasses that inherit ``__init__`` from
    a nanobind base would also pass this test, which is the right answer —
    they share the same constructor semantics.
    """
    if not isinstance(cls, type):
        return False
    init = cls.__dict__.get("__init__")
    if init is None:
        # Walk the MRO so subclasses of nanobind classes still register.
        for base in cls.__mro__[1:]:
            init = base.__dict__.get("__init__")
            if init is not None:
                break
    return init is not None and _is_nanobind_method(init)


def _is_namedtuple_class(cls: type) -> bool:
    """True for ``typing.NamedTuple`` / ``collections.namedtuple`` subclasses.

    The duck test (subclass of ``tuple`` + ``_fields`` tuple) covers both
    flavours and avoids importing ``typing.NamedTuple`` at runtime (which
    is a factory, not a base class you can ``issubclass`` against).
    """
    if not isinstance(cls, type):
        return False
    if not issubclass(cls, tuple):
        return False
    fields = getattr(cls, "_fields", None)
    return isinstance(fields, tuple) and all(isinstance(f, str) for f in fields)


def _is_plain_python_class_with_init(cls: type) -> bool:
    """True when ``cls`` owns a regular Python ``__init__`` worth documenting.

    Used to extend the Constructors rubric to hand-written Python classes
    like :class:`gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` so they
    pick up the same Unity-style layout as nanobind structs. We require
    ``__init__`` to be defined on this class (not inherited from ``object``
    or a parent we don't own) and to be a plain function — nanobind
    ``nb_method`` and NamedTuple instances are handled by their own
    branches.
    """
    if not isinstance(cls, type):
        return False
    if _is_nanobind_class(cls) or _is_namedtuple_class(cls):
        return False
    init = cls.__dict__.get("__init__")
    if init is None or not callable(init):
        return False
    return not _is_nanobind_method(init)


def _has_constructors_rubric(cls: type) -> bool:
    """Whether the class should render the Unity-style Constructors rubric.

    Three cases: nanobind-bound classes (per-overload C++ constructors),
    plain Python classes that own a real ``__init__``, and ``NamedTuple``
    subclasses (single synthesised constructor with well-known fields).
    The class-page template branches off this flag *and* the per-flavour
    flags (``is_nanobind_class``, ``is_plain_python_class``,
    ``is_namedtuple_class``) to pick the right autosummary template for
    the dedicated ``__init__`` page.

    NamedTuple is included here so that
    :func:`_strip_constructor_class_signature` can still wipe the inline
    Parameters block; the template skips the visible rubric for that
    case because the per-field Attributes block already covers it.
    """
    return (
        _is_nanobind_class(cls)
        or _is_plain_python_class_with_init(cls)
        or _is_namedtuple_class(cls)
    )


def _get_namedtuple_constructor_overloads(
    cls: type,
) -> list[tuple[str, str | None]] | None:
    """One-overload ``[(signature, None)]`` for a NamedTuple's constructor.

    NamedTuple synthesises ``Class(*fields)`` from the annotated class body;
    there is exactly one signature. We build it from ``_fields`` +
    ``__annotations__`` so the rendered overload matches the source
    declaration rather than whatever ``inspect.signature`` reconstructs
    from ``__init__`` (which the ``typing`` machinery hides).

    The per-overload docstring is left ``None`` — the per-field meaning is
    surfaced in the Attributes rubric and on each field's dedicated page,
    not under the constructor.
    """
    if not _is_namedtuple_class(cls):
        return None
    annotations = getattr(cls, "__annotations__", {}) or {}
    params: list[str] = []
    for field in cls._fields:
        ann = annotations.get(field)
        if ann is None:
            params.append(field)
            continue
        type_name = _format_annotation(ann)
        params.append(f"{field}: {type_name}")
    signature = f"__init__({', '.join(['self', *params])})"
    return [(signature, None)]


def _format_annotation(ann: Any) -> str:
    """Render a type annotation the way a human reads it in source.

    Three families need explicit handling:

    * ``ForwardRef("Entity")`` — typing wraps unresolved string annotations
      and ``str()`` returns ``"ForwardRef('Entity')"``. We unwrap to the
      forward arg.
    * Generic aliases like ``tuple[float, float, float]`` — these are
      instances of ``type`` in 3.10+, so the naive ``__qualname__`` path
      collapses them to ``tuple``. ``str()`` keeps the parameter list.
    * Plain classes (``int``, ``str``, ``torch.Tensor``) — ``str()``
      returns ``<class '...'>``; ``__qualname__`` is the readable form.
    """
    forward_arg = getattr(ann, "__forward_arg__", None)
    if forward_arg:
        return forward_arg
    if isinstance(ann, type):
        if getattr(ann, "__args__", None):
            return str(ann)
        return getattr(ann, "__qualname__", None) or ann.__name__
    if isinstance(ann, str):
        return ann
    return str(ann)


def _get_constructor_overloads(
    cls: type,
) -> list[tuple[str, str | None]] | None:
    """Unified overload lookup for classes that get the Constructors rubric.

    Dispatches to the nanobind ``__nb_signature__`` reader for bound
    classes, the NamedTuple field-list synthesiser, or
    :func:`inspect.signature` for plain Python classes. Returning
    ``None`` tells the directives to bail out with a docutils error
    instead of rendering an empty section.
    """
    nb = _get_nb_init_overloads(cls)
    if nb is not None:
        return nb
    nt = _get_namedtuple_constructor_overloads(cls)
    if nt is not None:
        return nt
    return _get_plain_python_init_overloads(cls)


def _get_plain_python_init_overloads(
    cls: type,
) -> list[tuple[str, str | None]] | None:
    """Synthesise a single-row overload list for a plain Python ``__init__``.

    The signature comes from :func:`inspect.signature` with annotations
    stripped — autodoc renders the dedicated page with
    ``autodoc_typehints = "description"`` so the parameter list there
    already carries the types, and including them in the Constructors
    rubric summary just makes the row noisy. The summary docstring is
    the ``__init__``'s own dedented docstring; the class docstring
    isn't used because we want the rubric description to talk about
    construction, not the class as a whole.
    """
    if not _is_plain_python_class_with_init(cls):
        return None
    init = cls.__dict__.get("__init__")
    if init is None:
        return None
    try:
        sig = inspect.signature(init)
    except (TypeError, ValueError):
        return None
    name_only = sig.replace(
        parameters=[
            param.replace(
                annotation=inspect.Parameter.empty,
                default=inspect.Parameter.empty,
            )
            for param in sig.parameters.values()
        ],
        return_annotation=inspect.Signature.empty,
    )
    signature = f"__init__{name_only}"
    doc = inspect.getdoc(init) or None
    return [(signature, doc)]


def _get_nb_init_overloads(cls: type) -> list[tuple[str, str | None]] | None:
    """Return ``[(signature, docstring), ...]`` for each ``__init__`` overload,
    or ``None`` if the class isn't nanobind-bound.

    Signatures come back as ``nb_method.__nb_signature__`` rows of the form
    ``("def __init__(self, arg0: int, /) -> None", docstring_or_None, _)``.
    We strip the leading ``def `` so callers can stitch the result into a
    ``.. py:method::`` directive.
    """
    if not _is_nanobind_class(cls):
        return None
    init = None
    for klass in cls.__mro__:
        init = klass.__dict__.get("__init__")
        if init is not None:
            break
    if init is None:
        return None
    raw = getattr(init, "__nb_signature__", None)
    if not raw:
        return None
    overloads: list[tuple[str, str | None]] = []
    for row in raw:
        if not isinstance(row, tuple) or not row:
            continue
        sig = row[0]
        doc = row[1] if len(row) > 1 else None
        if isinstance(sig, str) and sig.startswith("def "):
            sig = sig[4:]
        overloads.append((sig, doc))
    return overloads or None


def _import_class(fullname: str) -> type | None:
    """Resolve ``"package.module.ClassName"`` to a class object.

    Used by the constructor directives to look up the bound class at build
    time. Returns ``None`` on import failure so the directive can surface a
    proper docutils error instead of crashing the build.
    """
    modname, _, clsname = fullname.rpartition(".")
    if not modname:
        return None
    try:
        mod = importlib.import_module(modname)
    except ImportError:
        return None
    cls = getattr(mod, clsname, None)
    return cls if isinstance(cls, type) else None


_SIG_HEAD_RE = re.compile(r"^[A-Za-z_][\w.]*\s*\(")


def _split_signature_head(sig: str) -> tuple[str, str]:
    """Split ``"__init__(self, x: int) -> None"`` into ``("__init__", "(self, x: int) -> None")``.

    The name is what autodoc would print as the directive name; the tail is
    what we hand to ``.. py:method::`` as the signature argument.
    """
    match = _SIG_HEAD_RE.match(sig)
    if not match:
        return "", sig
    name = match.group(0).rstrip("(").strip()
    return name, sig[match.end() - 1 :]


class NanobindFunctionDocumenter(FunctionDocumenter):
    """FunctionDocumenter that also recognises nanobind ``nb_func`` objects."""

    objtype = "function"
    # Must beat FunctionDocumenter's priority so autodoc picks us when both
    # would match. Equal priority would be resolved by registration order,
    # which is fragile.
    priority = FunctionDocumenter.priority + 1

    @classmethod
    def can_document_member(
        cls, member: Any, membername: str, isattr: bool, parent: Any
    ) -> bool:
        if super().can_document_member(member, membername, isattr, parent):
            return True
        return _is_nanobind_function(member)


class NanobindMethodDocumenter(MethodDocumenter):
    """MethodDocumenter that recognises nanobind ``nb_method`` objects.

    Without this, autosummary's ``get_documenter`` picks
    :class:`AttributeDocumenter` (priority 10) over the stock
    :class:`MethodDocumenter` (priority 1) for every ``nb_method``, and the
    class page ends up listing methods under "Attributes" alongside real
    data fields. Priority 12 beats both Attribute (10) and Property (11)
    to remove ambiguity.
    """

    objtype = "method"
    priority = 12

    @classmethod
    def can_document_member(
        cls, member: Any, membername: str, isattr: bool, parent: Any
    ) -> bool:
        if super().can_document_member(member, membername, isattr, parent):
            return True
        return _is_nanobind_method(member)


class NanobindEnumAttributeDocumenter(AttributeDocumenter):
    """AttributeDocumenter that restores docstrings on Enum members.

    Sphinx's stock :class:`AttributeDocumenter` discards the docstring of any
    attribute it classifies as a "non data descriptor" (see
    :class:`~sphinx.ext.autodoc.NonDataDescriptorMixin`). Plain Python enum
    members are instances of the enum class, not descriptors, so they fall
    into that bucket. The mixin's reasoning — "the docstring of a non-data
    descriptor is very probably the wrong thing to display" — exists to
    avoid rendering, say, ``int.__doc__`` for every ``IntEnum`` value.

    Nanobind binds ``.value(name, value, "docstring")`` correctly: each
    member gets its own ``__doc__`` set in the member's ``__dict__``. But
    Sphinx never looks: it bails inside ``get_doc`` before the docstring is
    read, and ``autodoc-process-docstring`` is never fired, so a conf-level
    hook can't recover the content either.

    This override reads the per-member docstring straight from the enum
    member (re-looked-up via ``parent + name``, since
    ``AttributeDocumenter.import_object`` may have already replaced
    ``self.object`` with the underlying ``.value``).

    ``can_document_member`` deliberately delegates to the parent — we
    replace :class:`AttributeDocumenter` via ``override=True`` and must
    therefore claim *every* attribute it would have claimed (including
    plain data descriptors like ``_tuplegetter`` on NamedTuples), not
    just enum members. The Enum-specific behaviour is gated inside
    :meth:`get_doc`.
    """

    objtype = "attribute"
    # AttributeDocumenter is priority 10, PropertyDocumenter 11. +1 over
    # AttributeDocumenter is enough — PropertyDocumenter rejects enum
    # members in its own ``can_document_member``.
    priority = AttributeDocumenter.priority + 1

    def get_doc(self) -> list[list[str]] | None:
        member = safe_getattr(self.parent, self.objpath[-1], None)
        if isinstance(member, enum.Enum):
            doc = member.__doc__
            # Filter out the class-level fallback that Python returns when
            # the member has no own ``__doc__``. Without this guard, every
            # member would render the enum class's own docstring.
            if doc and doc != type(member).__doc__:
                tab_width = self.directive.state.document.settings.tab_width
                return [prepare_docstring(doc, tab_width)]
        return super().get_doc()


_EXAMPLES_SUBDIR = Path("api_reference") / "_examples"


def _read_constructor_example(app: Sphinx, class_fullname: str) -> list[str]:
    """Return the per-overload-shared example sidecar for a class' ``__init__``.

    Mirrors ``nyx_api_examples``: a file at
    ``api_reference/_examples/<class_fullname>.__init__.rst`` is appended to
    the dedicated constructor page. The ``nb-constructor`` directive owns
    this lookup because the page bypasses autodoc, so the
    ``autodoc-process-docstring`` listener that ``nyx_api_examples`` relies
    on never fires here. We discard the sidecar from
    ``nyx_api_examples_unused`` so the orphan-check at the end of the build
    doesn't flag it as unmatched.
    """
    name = f"{class_fullname}.__init__"
    sidecar = Path(app.srcdir) / _EXAMPLES_SUBDIR / f"{name}.rst"
    if not sidecar.is_file():
        return []
    unused: set[str] = getattr(app.env, "nyx_api_examples_unused", None) or set()
    unused.discard(name)
    return sidecar.read_text(encoding="utf-8").splitlines()


def _render_overload_lines(
    modname: str,
    clsname: str,
    overloads: list[tuple[str, str | None]],
    *,
    example_lines: list[str] | None = None,
) -> list[str]:
    """Build the rST shown on the dedicated ``<class>.__init__`` page.

    Emits ``.. py:method:: ClassName.<sig>`` for each overload, with the
    binding-supplied docstring as the body. The first overload claims the
    canonical anchor (``#<module>.<class>.__init__``); subsequent overloads
    use ``:no-index:`` so they don't trigger duplicate-target warnings while
    still rendering side-by-side.
    """
    lines: list[str] = [f".. currentmodule:: {modname}", ""]
    for index, (sig, doc) in enumerate(overloads):
        _, sig_tail = _split_signature_head(sig)
        lines.append(f".. py:method:: {clsname}.__init__{sig_tail}")
        if index > 0:
            lines.append("   :no-index:")
        lines.append("")
        if doc:
            for doc_line in doc.splitlines():
                lines.append(f"   {doc_line}" if doc_line else "")
        elif len(overloads) > 1:
            lines.append(f"   Overload {index + 1} of ``{clsname}.__init__``.")
        else:
            lines.append(f"   Construct a new :class:`{clsname}` instance.")
        lines.append("")
    if example_lines:
        lines.append("")
        lines.extend(example_lines)
        lines.append("")
    return lines


def _overload_page_docname(class_fullname: str, index: int) -> str:
    """Return the autosummary-generated docname for a single nanobind
    constructor overload, relative to the ``api_reference/generated``
    output directory.

    The suffix is ``__init__-<index>`` so the file sorts adjacent to the
    canonical ``__init__`` stub a single-overload class would still get,
    and Sphinx's docname machinery (which treats ``.`` as a path
    separator inside docnames) leaves it alone — there's no dot here, so
    it stays a single docname.
    """
    return f"{class_fullname}.__init__-{index}"


def _render_single_overload_page(
    modname: str,
    clsname: str,
    sig: str,
    doc: str | None,
    *,
    primary: bool,
    example_lines: list[str] | None = None,
) -> str:
    """Build the rST for a single-overload constructor page.

    Each overload lives at its own docname so the Constructors rubric
    rows on the class page can link to distinct URLs. The page header
    shows the user-facing signature (``ClassName(x: int, y: int)``,
    ``self`` stripped) to keep the breadcrumb / sidebar entry readable;
    the body emits the full ``.. py:method::`` directive so types and
    return annotation still render in the canonical autodoc style.

    Only the *primary* (first) overload page claims the canonical
    ``<class>.__init__`` index entry. Subsequent overload pages add
    ``:no-index:`` so cross-refs from ``:meth:`Class.__init__``` still
    land somewhere predictable and Sphinx doesn't warn about duplicate
    targets.
    """
    _, sig_tail = _split_signature_head(sig)
    display = _strip_self(sig_tail)
    title = f"{clsname}{display}"
    title_bar = "=" * max(len(title), 4)
    lines: list[str] = [
        title,
        title_bar,
        "",
        f".. currentmodule:: {modname}",
        "",
        f".. py:method:: {clsname}.__init__{sig_tail}",
    ]
    if not primary:
        lines.append("   :no-index:")
    lines.append("")
    if doc:
        for doc_line in doc.splitlines():
            lines.append(f"   {doc_line}" if doc_line else "")
    else:
        lines.append(f"   Construct a new :class:`{clsname}` instance.")
    lines.append("")
    if example_lines:
        lines.append("")
        lines.extend(example_lines)
        lines.append("")
    return "\n".join(lines) + "\n"


def _on_builder_inited_split_overloads(app: Sphinx) -> None:
    """Write a separate stub page for each overload of a nanobind class' constructor.

    Sphinx autosummary's ``process_generate_options`` runs on
    ``builder-inited`` at default priority (500) and writes one
    ``<class>.rst`` per class plus, for single-overload classes, a
    ``<class>.__init__.rst`` (the multi-overload case is gated out of
    ``custom-class-template.rst`` because there's no single canonical
    overload to render on one page). This listener registers at priority
    700 so it runs *after* those stubs land but still before
    :func:`BuildEnvironment.find_files` populates ``env.found_docs``, so
    the per-overload pages we drop in here get discovered like any other
    source file.

    The seed list comes from scanning every ``<stem>.rst`` autosummary
    produced and asking whether ``stem`` resolves to a multi-overload
    nanobind class. Files whose stem isn't a class import (methods,
    attributes, modules, ...) return ``None`` from
    :func:`_import_class` and skip the work. Single-overload classes
    are left to autosummary's canonical path.
    """
    gendir = Path(app.srcdir) / "api_reference" / "generated"
    if not gendir.is_dir():
        return
    for stub_path in sorted(gendir.glob("*.rst")):
        fullname = stub_path.stem
        # Skip member pages — they share a directory with class pages
        # but their stems don't resolve to a class.
        cls = _import_class(fullname)
        if cls is None or not _is_nanobind_class(cls):
            continue
        overloads = _get_nb_init_overloads(cls)
        if not overloads or len(overloads) <= 1:
            continue
        example_lines = _read_constructor_example(app, fullname)
        modname, _, clsname = fullname.rpartition(".")
        for index, (sig, doc) in enumerate(overloads):
            page_path = gendir / f"{_overload_page_docname(fullname, index)}.rst"
            content = _render_single_overload_page(
                modname,
                clsname,
                sig,
                doc,
                primary=(index == 0),
                example_lines=example_lines if index == 0 else None,
            )
            page_path.write_text(content, encoding="utf-8")


class NanobindConstructorDirective(Directive):
    """``.. nb-constructor:: <class fullname>``

    Renders every C++ overload that nanobind exposed for the class'
    ``__init__`` as a separate ``.. py:method::`` block, replacing what
    ``.. automethod:: Class.__init__`` would have produced (a single block
    whose body is the raw ``nb_method.__doc__`` overload dump). Used by the
    custom ``_templates/autosummary/method.rst`` template for ``__init__``
    members.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        fullname = self.arguments[0].strip()
        cls = _import_class(fullname)
        if cls is None:
            return [self.state.document.reporter.error(
                f"nb-constructor: could not import class {fullname!r}",
                line=self.lineno,
            )]
        overloads = _get_constructor_overloads(cls)
        if not overloads:
            return [self.state.document.reporter.error(
                f"nb-constructor: {fullname!r} has no documentable constructor",
                line=self.lineno,
            )]
        modname, _, clsname = fullname.rpartition(".")
        app = self.state.document.settings.env.app
        example_lines = _read_constructor_example(app, fullname)
        body_lines = _render_overload_lines(
            modname, clsname, overloads, example_lines=example_lines
        )
        view = StringList(body_lines, source=f"<nb-constructor:{fullname}>")
        container = nodes.section()
        container.document = self.state.document
        nested_parse_with_titles(self.state, view, container)
        return container.children


class NanobindConstructorSummaryDirective(Directive):
    """``.. nb-constructor-summary:: <class fullname>``

    Renders the Constructors rubric body on the class page itself: an
    autosummary-style two-column table with one row per C++ overload. The
    left column shows the per-overload signature; the right column shows the
    first sentence of that overload's docstring. Every row links to the
    dedicated ``<class>.__init__`` page (anchor-shared, since all overloads
    live on the same page).
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        fullname = self.arguments[0].strip()
        cls = _import_class(fullname)
        if cls is None:
            return [self.state.document.reporter.error(
                f"nb-constructor-summary: could not import class {fullname!r}",
                line=self.lineno,
            )]
        overloads = _get_constructor_overloads(cls)
        if not overloads:
            return [self.state.document.reporter.error(
                f"nb-constructor-summary: {fullname!r} has no documentable "
                f"constructor",
                line=self.lineno,
            )]
        _, _, clsname = fullname.rpartition(".")
        # Nanobind classes with multiple overloads get one dedicated page
        # per overload (split in ``_on_builder_inited_split_overloads``).
        # Single-overload nanobind classes, NamedTuples and plain Python
        # classes share a single ``<class>.__init__`` page, so the row
        # link target is the canonical method anchor in that case.
        per_overload = (
            _is_nanobind_class(cls)
            and len(overloads) > 1
        )

        # Use the same wrapper classes the pydata theme styles for
        # autosummary tables so the Constructors block lines up visually
        # with Methods / Attributes.
        table = nodes.table(classes=["autosummary", "longtable"])
        tgroup = nodes.tgroup(cols=2)
        table += tgroup
        tgroup += nodes.colspec(colwidth=10)
        tgroup += nodes.colspec(colwidth=90)
        tbody = nodes.tbody()
        tgroup += tbody

        for index, (sig, doc) in enumerate(overloads):
            _, sig_tail = _split_signature_head(sig)
            # Drop the leading ``self`` so the user-facing signature reads
            # ``uint2()`` / ``uint2(x: int, y: int)`` instead of leaking
            # the bound first argument.
            display_sig = _strip_self(sig_tail)
            row = nodes.row()
            entry_sig = nodes.entry()
            paragraph_sig = nodes.paragraph()
            if per_overload:
                # ``:doc:`` xrefs go through
                # :func:`sphinx.util.docname_join`, which interprets the
                # target as relative to the *parent directory* of the
                # current doc. The per-overload page sits next to the
                # class page in ``api_reference/generated``, so the leaf
                # docname (no directory prefix) is the right reftarget.
                xref = _make_doc_ref(
                    self.state,
                    _overload_page_docname(fullname, index),
                    f"{clsname}{display_sig}",
                )
            else:
                xref = _make_internal_ref(
                    self.state, f"{fullname}.__init__", f"{clsname}{display_sig}"
                )
            paragraph_sig += xref
            entry_sig += paragraph_sig
            row += entry_sig

            entry_doc = nodes.entry()
            entry_doc += nodes.paragraph(text=_first_sentence(doc) or "")
            row += entry_doc

            tbody += row

        result: list[nodes.Node] = [table]
        if per_overload:
            # Without this, the per-overload pages
            # ``<class>.__init__-N.rst`` written by
            # ``_on_builder_inited_split_overloads`` are reachable from
            # the table's links but live outside every toctree, so
            # Sphinx warns "document isn't included in any toctree".
            # A hidden ``addnodes.toctree`` registers them in the class
            # page's outgoing edges without rendering a visible list —
            # same trick autosummary uses for its own
            # ``autosummary_toc`` wrapper. Toctree entries are absolute
            # docnames (no extension), computed from the current
            # docname's directory + the overload page stem.
            import posixpath
            from sphinx import addnodes

            env = self.state.document.settings.env
            this_dir = posixpath.dirname(env.docname)
            absolute_docnames = [
                posixpath.normpath(
                    posixpath.join(this_dir, _overload_page_docname(fullname, i))
                )
                for i in range(len(overloads))
            ]
            tocnode = addnodes.toctree()
            tocnode["parent"] = env.docname
            tocnode["entries"] = [(None, dn) for dn in absolute_docnames]
            tocnode["includefiles"] = absolute_docnames
            tocnode["maxdepth"] = -1
            tocnode["caption"] = None
            tocnode["glob"] = None
            tocnode["hidden"] = True
            tocnode["includehidden"] = False
            tocnode["numbered"] = 0
            tocnode["titlesonly"] = False
            tocnode["rawentries"] = []
            result.append(tocnode)
        return result


def _strip_self(sig_tail: str) -> str:
    """Turn ``"(self, x: int) -> None"`` into ``"(x: int)"``.

    The return-type annotation is also dropped — constructors always return
    an instance of the class, and showing ``-> None`` (which is what nanobind
    emits) is just visual noise on the summary table.
    """
    if not sig_tail.startswith("("):
        return sig_tail
    arrow = sig_tail.rfind(") -> ")
    body = sig_tail[1 : arrow] if arrow != -1 else sig_tail[1:].rstrip()
    if body.endswith(")"):
        body = body[:-1]
    parts = [p.strip() for p in body.split(",")]
    parts = [p for p in parts if p and p != "self" and not p.startswith("self") and p != "/"]
    return "(" + ", ".join(parts) + ")"


_FIRST_SENTENCE_RE = re.compile(r"^(.+?[.!?])(?:\s|$)")


def _first_sentence(doc: str | None) -> str:
    if not doc:
        return ""
    text = doc.strip().splitlines()[0] if doc.strip() else ""
    match = _FIRST_SENTENCE_RE.match(text)
    return match.group(1) if match else text


def _make_doc_ref(state, docname: str, label: str) -> nodes.Node:
    """Build a pending Sphinx cross-reference to a docname.

    Used for per-overload constructor pages, where each row in the
    Constructors rubric links to a separate ``<class>.__init__-N`` page
    rather than to an anchor on a shared ``__init__`` page. Going through
    the ``std:doc`` role keeps the link correct across builders and lets
    Sphinx fail the build if the target page wasn't generated, instead
    of silently producing a dead link.
    """
    from docutils.nodes import Text
    from sphinx.addnodes import pending_xref

    xref = pending_xref(
        "",
        refdomain="std",
        reftype="doc",
        reftarget=docname,
        refexplicit=True,
        refwarn=True,
    )
    literal = nodes.literal(classes=["xref", "std", "std-doc"])
    literal += Text(label)
    xref += literal
    return xref


def _make_internal_ref(state, target: str, label: str) -> nodes.Node:
    """Build a pending Sphinx cross-reference to ``target`` shown as ``label``.

    Uses the ``py:meth`` role so the link resolves to the
    ``<class>.__init__`` page where the overloads live. Going through the
    domain (rather than emitting a raw ``nodes.reference`` with a hardcoded
    URL) keeps the link correct across builders (html / dirhtml / linkcheck).
    """
    from docutils.nodes import Text
    from sphinx.addnodes import pending_xref

    xref = pending_xref(
        "",
        refdomain="py",
        reftype="meth",
        reftarget=target,
        refexplicit=True,
        refwarn=True,
    )
    xref["py:module"] = state.document.settings.env.ref_context.get("py:module")
    literal = nodes.literal(classes=["xref", "py", "py-meth"])
    literal += Text(label)
    xref += literal
    return xref


_INHERITED_NOISE_MODULES = frozenset({"builtins", "enum"})


def _filtered_get_class_members(obj: Any) -> dict[str, Any]:
    """Replacement for ``sphinx.ext.autosummary.generate._get_class_members``.

    Drops members surfaced by uninteresting base classes:

    * Enum subclasses inherit ``conjugate`` / ``bit_length`` / ``to_bytes``
      / ``real`` / ``imag`` / ``count`` from ``int`` (or ``object``); these
      bury real enum values in the Methods and Attributes tables.
    * ``NamedTuple`` subclasses inherit ``count`` and ``index`` from
      ``tuple``; these aren't useful on the class page either.

    We consult two locations for the defining class because Sphinx's
    ``get_class_members`` doesn't set ``member.class_`` for inherited
    method descriptors (the common case for built-in inherited
    ``tuple.count`` / ``int.bit_length``). Falling back to the descriptor's
    own ``__objclass__`` covers that gap. Members whose origin is unknown
    or is a regular Python/nanobind class pass through unchanged.
    """
    members = sphinx.ext.autodoc.get_class_members(obj, None, safe_getattr)
    result: dict[str, Any] = {}
    for name, member in members.items():
        if _defined_in_noise_module(member):
            continue
        result[name] = member.object
    return result


def _defined_in_noise_module(member: Any) -> bool:
    """True iff the member should be filtered out because it comes from a
    built-in or stdlib base we don't want to expose in the class page."""
    candidates: list[Any] = []
    sphinx_cls = getattr(member, "class_", None)
    if sphinx_cls is not None:
        candidates.append(sphinx_cls)
    obj = getattr(member, "object", None)
    objclass = getattr(obj, "__objclass__", None)
    if objclass is not None:
        candidates.append(objclass)
    for cls in candidates:
        mod = getattr(cls, "__module__", None)
        if mod in _INHERITED_NOISE_MODULES:
            return True
    return False


# ----- NamedTuple field-docstring extraction ------------------------------

# Cache populated by ``_extract_namedtuple_field_docs``: keyed by
# ``"<module>.<class>"`` so the attribute hook can look it up by name
# without re-importing the class.
_NAMEDTUPLE_FIELD_DOCS: dict[str, dict[str, list[str]]] = {}

_NUMPY_FIELD_HEADER_RE = re.compile(r"^(?P<name>\w+)\s*(?::\s*(?P<type>.+))?\s*$")


def _find_napoleon_section(
    lines: list[str], section: str
) -> tuple[int, int] | None:
    """Locate the half-open ``[start, end)`` range of a Napoleon section.

    Recognises the NumPy form ("Attributes\\n----------") only — that's
    what our codebase uses (see ``nyx_camera_sensor.NyxCameraData``).
    Returns ``None`` if the section isn't found. Ranges include the
    header and underline lines so the caller can splice them out wholesale.
    """
    header_line = section
    for i, line in enumerate(lines):
        if line.strip() != header_line:
            continue
        if i + 1 >= len(lines):
            continue
        underline = lines[i + 1].strip()
        if not underline or not all(c == "-" for c in underline):
            continue
        # Section body runs until the next blank-line + new section header,
        # the end of the lines, or a dedent. We use the simpler rule of
        # "until next Napoleon header (same column 0)" which is what
        # ``sphinx_napoleon`` itself does for these docstrings.
        end = len(lines)
        for j in range(i + 2, len(lines)):
            line_j = lines[j]
            # Detect another section header by looking ahead for an
            # underline.
            if (
                line_j
                and not line_j.startswith(" ")
                and not line_j.startswith("\t")
                and j + 1 < len(lines)
                and lines[j + 1].strip()
                and all(c == "-" for c in lines[j + 1].strip())
            ):
                end = j
                break
        return i, end
    return None


def _parse_napoleon_attributes(body: list[str]) -> dict[str, list[str]]:
    """Parse a NumPy ``Attributes``-section body into per-field doc lines.

    The expected shape is::

        rgb : torch.Tensor
            Rendered RGB image, shape ``(B, H, W, 3)`` ...

    Indented continuations belong to the preceding field; blank lines are
    preserved inside each field's body so multi-paragraph descriptions
    render correctly. Type annotations are intentionally dropped — they
    already live on the class via ``__annotations__`` and on each field's
    dedicated page via the autodoc directive Sphinx generates.
    """
    result: dict[str, list[str]] = {}
    current_field: str | None = None
    current_lines: list[str] = []
    for raw in body:
        # A field header is unindented (no leading space) and matches "name"
        # or "name : type".
        if raw and not raw.startswith((" ", "\t")):
            match = _NUMPY_FIELD_HEADER_RE.match(raw.strip())
            if match:
                if current_field is not None:
                    result[current_field] = _dedent_trim(current_lines)
                current_field = match.group("name")
                current_lines = []
                continue
        if current_field is not None:
            current_lines.append(raw)
    if current_field is not None:
        result[current_field] = _dedent_trim(current_lines)
    return result


def _dedent_trim(lines: list[str]) -> list[str]:
    """Strip the common leading indent and surrounding blank lines.

    The Napoleon body lines come in with whatever indentation the
    docstring used (typically 4 spaces). We dedent so the result reads
    like a standalone paragraph and survives being injected as the body
    of a fresh ``.. py:attribute::`` directive.
    """
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    if not lines:
        return []
    indents = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    common = min(indents) if indents else 0
    return [line[common:] if line.strip() else "" for line in lines]


def _on_process_class_docstring(
    _app, what: str, name: str, obj: Any, _options: Any, lines: list[str]
) -> None:
    """Hoist a NamedTuple's Napoleon ``Attributes`` block into per-field docs.

    The default rendering for NamedTuples shows the Attributes section
    inline under the class header, which collides with the Attributes
    rubric our class template produces (each field links to its own
    page). We:

    * parse the Attributes section once per class,
    * cache the per-field docstring lines so
      :func:`_on_process_attribute_docstring` can inject them when each
      field is documented on its own page,
    * delete the section from the class docstring so it doesn't render
      twice.

    Sphinx fires ``autodoc-process-docstring`` *before* Napoleon parses
    the section, so we operate on the raw NumPy-style text. Calling
    Napoleon ourselves would double-process the survivors.
    """
    if what != "class" or not _is_namedtuple_class(obj):
        return
    span = _find_napoleon_section(lines, "Attributes")
    if span is None:
        return
    start, end = span
    body = lines[start + 2 : end]
    _NAMEDTUPLE_FIELD_DOCS[name] = _parse_napoleon_attributes(body)
    # Drop the now-redundant section (header + underline + body, and the
    # trailing blank line if one is present).
    while end < len(lines) and not lines[end].strip():
        end += 1
    del lines[start:end]


def _on_process_attribute_docstring(
    _app, what: str, name: str, _obj: Any, _options: Any, lines: list[str]
) -> None:
    """Replace a NamedTuple field's stock docstring with the parsed body.

    Without this, every ``_tuplegetter`` shows the same placeholder text
    Python's NamedTuple machinery sets (``Alias for field number N``)
    on both the Attributes rubric and the field's dedicated page.
    """
    if what != "attribute":
        return
    parent_name, _, field_name = name.rpartition(".")
    docs = _NAMEDTUPLE_FIELD_DOCS.get(parent_name)
    if not docs or field_name not in docs:
        return
    lines[:] = docs[field_name]


class NyxClassExampleDirective(Directive):
    """``.. nyx-class-example:: <class fullname>``

    Insert the class-level example sidecar at this directive's location.

    Sidecars at ``api_reference/_examples/<class_fullname>.rst`` are
    long-form prose (typically a "How to use" section with a code
    sample) that we want to render *below* the class' Methods and
    Attributes rubrics. ``nyx_api_examples`` appends sidecars to autodoc
    docstrings, which would place this prose between the class
    docstring and the rubrics — backwards. The class template instead
    invokes this directive outside (after) the ``autoclass`` block, so
    the prose lands at the bottom of the page.

    Marks the sidecar as "seen" in the
    ``nyx_api_examples_unused`` set so the end-of-build orphan check
    doesn't flag it as unmatched.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        fullname = self.arguments[0].strip()
        app = self.state.document.settings.env.app
        sidecar = Path(app.srcdir) / _EXAMPLES_SUBDIR / f"{fullname}.rst"
        if not sidecar.is_file():
            return []
        unused: set[str] = getattr(app.env, "nyx_api_examples_unused", None) or set()
        unused.discard(fullname)
        lines = sidecar.read_text(encoding="utf-8").splitlines()
        view = StringList(lines, source=f"<nyx-class-example:{fullname}>")
        container = nodes.section()
        container.document = self.state.document
        nested_parse_with_titles(self.state, view, container)
        return container.children


def _wipe_constructor_annotations(
    app, what, name, obj, _options, _signature, _return_annotation
):
    """Second-pass wipe of ``app.env.temp_data['annotations'][<class>]`` for
    classes that get a Constructors rubric.

    Sphinx's :func:`sphinx.ext.autodoc.typehints.record_typehints` connects
    to ``autodoc-process-signature`` at the default priority (500) and
    populates ``annotations`` from ``inspect.signature``. The doctree
    transform :func:`merge_typehints` later reads that entry and inserts
    a Parameters field list under the class. We wipe the entry *after*
    ``record_typehints`` runs (priority 600 here, > 500) so the field
    list never gets built. The wipe in
    :func:`_strip_constructor_class_signature` (priority 400) is too
    early — ``record_typehints`` refills it.
    """
    if what != "class" or not isinstance(obj, type) or not _has_constructors_rubric(obj):
        return None
    annotations = getattr(app.env, "temp_data", {}).get("annotations") if app.env else None
    if isinstance(annotations, dict) and name in annotations:
        annotations[name] = {}
    return None


def _strip_constructor_class_signature(
    app, what, name, obj, _options, _signature, return_annotation
):
    """Suppress the inline class-header signature *and* the auto-generated
    Parameters section for classes that get a Constructors rubric.

    Three cases share this treatment:

    * Nanobind classes — autodoc shows ``ClassName(*args, **kwargs)``
      because :func:`inspect.signature` can't unpack an ``nb_method``
      overload set.
    * ``NamedTuple`` subclasses — autodoc shows ``ClassName(field1, field2)``;
      Sphinx's built-in ``merge_typehints`` (used when
      ``autodoc_typehints = "description"``) then inserts a Parameters
      field list at doctree-transform time, sourced from
      ``app.env.temp_data['annotations'][<fullname>]``.
    * Plain Python classes with a Constructors rubric — same as the
      NamedTuple case, plus ``sphinx_autodoc_typehints`` adds its own
      ``:param:`` / ``:type:`` fields to the class docstring (see
      :func:`_strip_constructor_param_fields`).

    Returning an empty signature handles the visible header. To stop the
    Parameters list we wipe the recorded annotations *after*
    ``record_typehints`` populates them (it runs on the same event, also
    at default priority). The recorded entry is what
    ``merge_typehints`` later reads to decide whether to emit the field
    list at all. The companion docstring hook then strips the
    ``sphinx_autodoc_typehints`` injections.
    """
    if what != "class" or not isinstance(obj, type) or not _has_constructors_rubric(obj):
        return None
    annotations = getattr(app.env, "temp_data", {}).get("annotations") if app.env else None
    if isinstance(annotations, dict) and name in annotations:
        annotations[name] = {}
    return ("", return_annotation)


_PARAM_FIELD_RE = re.compile(
    r"^\s*:(?:param|parameter|arg|argument|type|kwparam|kwtype|return|returns|rtype)"
    r"(?:\s+[^:]*)?:"
)


def _strip_constructor_param_fields(
    _app, what: str, _name: str, obj: Any, _options: Any, lines: list[str]
) -> None:
    """Strip ``:param:`` / ``:type:`` / ``:return:`` fields from a class
    docstring once a Constructors rubric is going to render them on the
    dedicated ``__init__`` page.

    ``sphinx_autodoc_typehints`` connects an ``autodoc-process-docstring``
    listener at the default priority (500) that synthesises these fields
    from ``cls.__init__``'s annotations. The fields then render as a
    "Parameters" block under the class docstring, duplicating the info
    the dedicated constructor page already shows with cross-refs. We
    connect at a higher priority value so this listener runs *after*
    the injection, and remove any field-list line plus its indented
    continuations.
    """
    if what != "class" or not isinstance(obj, type) or not _has_constructors_rubric(obj):
        return
    i = 0
    while i < len(lines):
        if not _PARAM_FIELD_RE.match(lines[i]):
            i += 1
            continue
        # Drop the field header.
        del lines[i]
        # Drop indented continuation lines (the param description body).
        while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
            # Stop if we hit a blank line that's followed by a non-field,
            # non-indented line — that's the start of a new paragraph
            # belonging to the class docstring, not the field's body.
            if not lines[i].strip():
                if i + 1 < len(lines) and lines[i + 1].strip() and not _PARAM_FIELD_RE.match(lines[i + 1]) and not lines[i + 1].startswith((" ", "\t")):
                    break
            del lines[i]
    # Collapse trailing blank lines we may have created.
    while lines and not lines[-1].strip():
        lines.pop()


def _patch_autosummary_get_modules() -> None:
    """Skip submodules whose ``__all__`` is explicitly empty.

    Sphinx autosummary's recursive package walk
    (``_get_modules`` in ``sphinx.ext.autosummary.generate``) discovers
    submodules via :func:`pkgutil.iter_modules` and only filters by
    leading-underscore name. That leaves internal helpers like
    ``gs_nyx_plugin.nyx_scene_utils`` — which declare
    ``__all__: list[str] = []`` to signal "not part of the public API"
    — being walked and documented anyway.

    We wrap the helper to additionally drop any importable submodule
    whose ``__all__`` is present and empty. Submodules that don't
    declare ``__all__`` at all keep showing up (the convention here is
    that *explicit* emptiness is the opt-out signal, not the absence).
    """
    from sphinx.ext.autosummary import generate as gen

    if getattr(gen, "_nyx_get_modules_patched", False):
        return
    original = gen._get_modules

    def patched(obj, *, skip, name, public_members=None):
        public, items = original(obj, skip=skip, name=name, public_members=public_members)

        def _has_empty_all(modname: str) -> bool:
            try:
                module = importlib.import_module(f"{name}.{modname}")
            except ImportError:
                return False
            all_attr = getattr(module, "__all__", None)
            return isinstance(all_attr, (list, tuple)) and len(all_attr) == 0

        public = [m for m in public if not _has_empty_all(m)]
        items = [m for m in items if not _has_empty_all(m)]
        return public, items

    gen._get_modules = patched
    setattr(gen, "_nyx_get_modules_patched", True)


def _patch_autosummary_no_table() -> None:
    """Teach ``.. autosummary::`` two extra flag options that strip the
    visible artefacts while leaving stub generation intact:

    * ``:no-table:`` drops the one-row summary table.
    * ``:no-toc:`` drops the wrapped ``autosummary_toc`` node, which is
      what Sphinx walks to populate ``app.env.toctree_includes`` and what
      the pydata theme renders as sidebar entries. Without this flag the
      dedicated ``<class>.__init__`` page lands in the sidebar under
      every class — clutter on nanobind structs, redundant on NamedTuples
      where the constructor is just the class itself.

    Stub generation is driven by ``find_autosummary_in_lines`` re-parsing
    the source files, so it doesn't care whether the doctree carries the
    table or the toc node. The ``__init__`` page therefore still exists
    and links from the Constructors rubric continue to resolve; only the
    sidebar and the inline table are suppressed. The page itself sets
    ``:orphan:`` (see ``nb-constructor-page.rst``) so Sphinx doesn't warn
    that it isn't included in any toctree.
    """
    from sphinx.ext import autosummary as _autosummary_pkg
    from sphinx.ext.autosummary import Autosummary, autosummary_table, autosummary_toc

    if getattr(Autosummary, "_nyx_no_table_patched", False):
        return

    original_run = Autosummary.run
    original_option_spec = dict(Autosummary.option_spec)
    original_option_spec["no-table"] = lambda arg: True  # docutils flag option
    original_option_spec["no-toc"] = lambda arg: True

    def patched_run(self):
        result = original_run(self)
        if "no-table" in self.options:
            result = [n for n in result if not isinstance(n, autosummary_table)]
        if "no-toc" in self.options:
            result = [n for n in result if not isinstance(n, autosummary_toc)]
        return result

    Autosummary.option_spec = original_option_spec
    Autosummary.run = patched_run
    setattr(Autosummary, "_nyx_no_table_patched", True)
    # ``find_autosummary_in_lines`` skips any line that starts with ``:``
    # before falling into its item-line branch, so unknown options are
    # ignored harmlessly during stub-gen — no parser change needed.
    _ = _autosummary_pkg  # keep import for readers


def _patch_autosummary_renderer() -> None:
    """Inject ``is_nanobind_class`` into the per-class template context.

    Sphinx's autosummary builds its Jinja namespace inside
    ``generate_autosummary_content`` and never fires an event the template
    could hook for extra context. Wrapping ``AutosummaryRenderer.render``
    is the surgical alternative: we look up the class from ``fullname``
    just before rendering and stash a flag the class template can branch
    on without doing any Python introspection of its own.
    """
    original = AutosummaryRenderer.render

    def render(self, template_name: str, context: dict) -> str:
        if context.get("objtype") == "class":
            fullname = context.get("fullname")
            if fullname:
                cls = _import_class(fullname)
                if cls is not None and _has_constructors_rubric(cls):
                    context = dict(context)
                    context["is_nanobind_class"] = _is_nanobind_class(cls)
                    context["is_namedtuple_class"] = _is_namedtuple_class(cls)
                    context["is_plain_python_class"] = (
                        _is_plain_python_class_with_init(cls)
                    )
                    context["has_constructors_rubric"] = True
                    # Gate the autosummary block in custom-class-template
                    # on this count: multi-overload nanobind classes get
                    # one page per overload (written by
                    # ``_on_builder_inited_split_overloads``) and don't
                    # need autosummary to generate a canonical
                    # ``<class>.__init__`` stub.
                    overloads = _get_constructor_overloads(cls)
                    context["nb_constructor_overload_count"] = (
                        len(overloads) if overloads else 0
                    )
        return original(self, template_name, context)

    AutosummaryRenderer.render = render


def setup(app: Sphinx) -> dict[str, Any]:
    app.setup_extension("sphinx.ext.autodoc")
    app.add_autodocumenter(NanobindFunctionDocumenter, override=True)
    app.add_autodocumenter(NanobindMethodDocumenter, override=True)
    app.add_autodocumenter(NanobindEnumAttributeDocumenter, override=True)
    app.add_directive("nb-constructor", NanobindConstructorDirective)
    app.add_directive("nb-constructor-summary", NanobindConstructorSummaryDirective)
    app.add_directive("nyx-class-example", NyxClassExampleDirective)
    # ``autodoc-process-signature`` is dispatched via ``emit_firstresult``:
    # the first handler that returns a non-``None`` value wins, the rest
    # don't get to run. ``sphinx_autodoc_typehints`` connects at the
    # default priority (500) and unconditionally regenerates the signature
    # from ``inspect.signature``, which would clobber our empty signature
    # for plain Python classes. Connecting at a lower priority value puts
    # us in front of it so our strip takes effect first.
    app.connect(
        "autodoc-process-signature", _strip_constructor_class_signature, priority=400
    )
    # Sphinx's built-in ``record_typehints`` connects to the same event at
    # the default priority (500) and populates
    # ``app.env.temp_data['annotations'][<fullname>]`` from
    # ``inspect.signature``. ``merge_typehints`` then reads that entry as
    # a doctree transform to insert a Parameters field list on the class
    # page. The wipe in ``_strip_constructor_class_signature`` (priority
    # 400) runs *before* ``record_typehints``, so the entry it tries to
    # blank doesn't exist yet. We re-wipe at priority 600 to run after
    # ``record_typehints`` has refilled the dict — that's the wipe that
    # actually keeps ``merge_typehints`` from rendering anything.
    app.connect(
        "autodoc-process-signature", _wipe_constructor_annotations, priority=600
    )
    # ``sphinx_autodoc_typehints`` connects at the default priority (500)
    # to inject ``:param:`` / ``:type:`` fields into the class docstring
    # when ``always_document_param_types`` is set (we don't, but its
    # ``:type:`` injection still happens for any pre-existing ``:param:``
    # lines an author wrote). Running this listener at priority 700
    # places it *after* that injection so we can strip the fields back
    # out before ``merge_typehints`` turns them into a visible Parameters
    # block.
    app.connect(
        "autodoc-process-docstring", _strip_constructor_param_fields, priority=700
    )
    # Napoleon registers its ``autodoc-process-docstring`` listener at the
    # default priority (500) and rewrites the NumPy-style ``Attributes``
    # block before any later listener sees it. We need to extract that
    # block while it still looks like NumPy, so run earlier (lower
    # priority value = earlier).
    app.connect("autodoc-process-docstring", _on_process_class_docstring, priority=400)
    app.connect("autodoc-process-docstring", _on_process_attribute_docstring)
    # ``process_generate_options`` (autosummary's stub-gen) runs on
    # ``builder-inited`` at the default priority (500); we go at 700 so
    # the per-overload split happens *after* the canonical
    # ``<class>.__init__.rst`` stubs land but still before
    # ``BuildEnvironment.find_files`` populates ``env.found_docs``, so
    # the per-overload pages get discovered as ordinary source files.
    app.connect(
        "builder-inited", _on_builder_inited_split_overloads, priority=700
    )
    # Sphinx exposes no event for filtering autosummary's class-member
    # enumeration, so we replace the private helper outright. See
    # _filtered_get_class_members for the rationale.
    _autosummary_generate._get_class_members = _filtered_get_class_members
    _patch_autosummary_renderer()
    _patch_autosummary_no_table()
    _patch_autosummary_get_modules()
    return {
        "version": "0.4.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
