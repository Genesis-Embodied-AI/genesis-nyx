.. rubric:: Example

A typical environment-map asset wraps a long-lat HDR (such as the ones
shipped by Poly Haven) and is passed to a camera through
:attr:`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.env_maps`:

.. code-block:: python

    import gs_nyx.nyx_py_sdk as nps

    env_map            = nps.EnvironmentMapAsset()
    env_map.texture    = "path/to/studio_4k.hdr"
    env_map.layout     = nps.EEnvMapLayout.LongLat
    env_map.multiplier = 1.0
    env_map.tint       = nps.float3(1.0, 1.0, 1.0)
    env_map.rotation   = 0.0  # radians, about the world up axis

    # The asset is then consumed by a NyxCameraOptions instance:
    #
    #     NyxCameraOptions(..., env_maps=(env_map,))
    #
    # so every Nyx camera in the scene inherits this lighting environment.

.. note::

   :attr:`texture` is read by the renderer at scene-build time, not when the
   asset is constructed. Paths are resolved relative to the working
   directory of the running Genesis process; pass absolute paths or anchor
   them to the script location with
   ``os.path.join(os.path.dirname(__file__), ...)`` to keep behaviour stable
   across launch directories.
