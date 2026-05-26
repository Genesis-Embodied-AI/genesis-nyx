API reference
=============

The pages below are auto-generated from the installed ``gs_nyx`` package on
every build. Each module, class, function, and enum has its own page,
populated from the docstrings shipped in the wheel.

.. note::

   The plugin's bindings are compiled C++ (nanobind). Signatures are read from
   the ``.pyi`` stub files inside the wheel; descriptive text comes from the
   docstrings each binding registers with nanobind. If a member appears with an
   empty body, its binding is missing a docstring upstream.

.. note::

   Worked examples for individual symbols live in
   ``api_reference/_examples/`` as ``.rst`` sidecars named by fully-qualified
   Python path (e.g. ``gs_nyx.nyx_py_sdk.quaternion_conjugate.rst``). They
   are appended to autodoc's output by the ``nyx_api_examples`` extension;
   ``docs/scripts/check_api_examples.py`` runs every snippet before the
   Sphinx build so a broken example fails the docs build. The runnable
   user-guide scripts under ``examples/`` are the place for narrative
   walkthroughs.

``gs_nyx`` is the compiled C++ binding layer (renderer, scene SDK, video
encoder). ``gs_nyx_plugin`` is the Python integration layer that exposes the
renderer to Genesis as a sensor — this is where ``NyxCameraOptions``,
``NyxCameraSensor`` and the scene-export helpers live, and what the example
scripts import directly.

.. autosummary::
   :toctree: generated
   :template: custom-module-template.rst
   :recursive:

   gs_nyx
   gs_nyx_plugin
