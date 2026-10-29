.. rubric:: Example

A Nyx camera is declared with the same fields as a Genesis camera plus the
renderer-specific ones. Two of them are new in ``gs-nyx-plugin`` 0.1.10:
``gpu_vendor`` selects which GPU the shared renderer runs on (it must be one
your CUDA or ROCm torch build can drive), and ``camera_profile`` replaces the
former ``tone_mapper`` field with a full lens / sensor / colour profile:

.. nyx-test: compile-only

.. code-block:: python

    import gs_nyx.nyx_py_renderer as npr
    import gs_nyx.nyx_py_sdk as nps
    from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions

    cam = scene.add_sensor(NyxCameraOptions(
        res            = (1280, 720),
        pos            = (-1.0, 1.0, 1.2),
        lookat         = (0.0, 0.0, 0.1),
        spp            = 32,
        denoise        = True,
        render_mode    = npr.ERenderMode.FastPathTracer,
        anti_aliasing  = nps.EAntiAliasing.SMAA,
        gpu_vendor     = nps.EGPUVendor.AMD,          # render on the AMD GPU (ROCm torch)
        camera_profile = "profiles/sony_a7_r5_24mm.json",
    ))

.. note::

   ``gpu_vendor`` is read from the first Nyx sensor added to the scene and
   applies to every Nyx camera, since they share one renderer. ``None`` (the
   default) picks the GPU with the most memory. When ``camera_profile`` is
   set, ``fov`` is ignored and a warning is printed if both are given.
