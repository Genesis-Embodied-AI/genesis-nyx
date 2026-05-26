.. rubric:: Reading rendered pixels

``read()`` is the only entry point for pulling rendered pixels out of a
NyxCameraSensor — and the method that defines what this class is *for*.
It's inherited from Genesis' ``BaseCameraSensor`` so it doesn't get its
own page in this reference, but the Nyx-specific behaviour is small
enough to cover here. The returned
:class:`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraData` exposes a single
``rgb`` tensor of shape ``(B, H, W, 3)`` resident on CUDA, where ``B`` is
the number of parallel Genesis environments (always at least 1):

.. nyx-test: compile-only

.. code-block:: python

    import genesis as gs
    import gs_nyx.nyx_py_renderer as npr
    from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions

    gs.init()
    scene = gs.Scene(show_viewer=False)
    scene.add_entity(morph=gs.morphs.Plane())

    cam = scene.add_sensor(NyxCameraOptions(
        res         = (640, 480),
        pos         = (2.0, -2.0, 1.0),
        lookat      = (0.0, 0.0, 0.0),
        render_mode = npr.ERenderMode.FastPathTracer,
        lights      = [{"type": "directional", "dir": (-0.3, 0.4, -0.85),
                        "color": (1.0, 1.0, 1.0), "intensity": 3.0}],
    ))
    scene.build(n_envs=1)
    scene.step()                              # triggers the actual render.

    rgb   = cam.read().rgb                    # (1, 480, 640, 3) uint8 on CUDA.
    frame = rgb[0].cpu().numpy()              # H × W × 3 numpy array, ready to save.

.. note::

   The returned tensor aliases the renderer's image cache. Each
   ``scene.step()`` marks the sensor stale and re-renders on the next
   ``read()`` call; if you need to keep a frame across steps call
   ``.clone()`` (or ``.cpu()``) before stepping again. Values are in
   ``[0, 255]`` and the channel order is RGB.
