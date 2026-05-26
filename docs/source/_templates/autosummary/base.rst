{# Default autosummary template for symbols that don't have a more specific
   template (functions, methods, attributes, exceptions). Mirrors Sphinx's
   built-in base.rst but uses only the leaf name in the H1, so the navbar
   entries, page titles, and breadcrumbs show just `cudaDevice` instead of
   `gs_nyx.nyx_py_renderer.BridgeStartupParams.cudaDevice`. #}
{{ fullname.split('.') | last | escape | underline }}

.. currentmodule:: {{ module }}

.. auto{{ objtype }}:: {{ objname }}
