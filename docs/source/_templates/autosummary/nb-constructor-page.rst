{# Dedicated page for a nanobind class' __init__: lists every C++ overload
   instead of the ``ClassName(*args, **kwargs)`` collapsed signature autodoc
   would otherwise produce. The ``.. nb-constructor::`` directive lives in
   ``nyx_nanobind.py``; it reads ``__nb_signature__`` off the nb_method and
   emits one ``.. py:method::`` block per overload, with the per-overload
   docstring as each block's body.

   The page title is ``Constructor`` (not ``__init__``) so the sidebar
   entry reads naturally next to the class' real methods. The page is
   intentionally kept in its parent class' toctree (no ``:orphan:``) so
   the pydata theme's section navigation still resolves on this page. #}
Constructor
===========

.. currentmodule:: {{ module }}

.. nb-constructor:: {{ fullname.rsplit('.__init__', 1)[0] }}
