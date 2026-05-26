{# Dedicated page for a plain Python class' __init__. We delegate to
   ``.. automethod::`` so autodoc renders the full Parameters list
   (sourced from the docstring + ``autodoc_typehints = "description"``)
   instead of the bare overload signature ``.. nb-constructor::`` emits.

   The page title is ``Constructor`` (not ``__init__``) so the sidebar
   entry reads naturally next to the class' real methods. The page is
   intentionally kept in its parent class' toctree (no ``:orphan:``) so
   the pydata theme's section navigation still resolves on this page. #}
Constructor
===========

.. currentmodule:: {{ module }}

.. automethod:: {{ objname }}
