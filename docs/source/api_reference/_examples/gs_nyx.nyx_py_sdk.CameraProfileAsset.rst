.. rubric:: Example

A camera profile bundles the lens, sensor and colour-management settings a
Nyx camera renders with. Build one in Python, export it to JSON, and hand
the file to a camera through
:attr:`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.camera_profile`
(the camera's ``fov`` is then ignored, the profile owns the optics):

.. code-block:: python

    import math
    import gs_nyx.nyx_py_sdk as nps

    profile = nps.CameraProfileAsset()
    profile.set_fov_y(math.radians(40.0))                     # vertical field of view
    profile.colorManagement.toneMapper = nps.EToneMapper.ACES_1_3
    profile.lens.vignette.strength     = 0.5
    profile.sensor.exposure.iso        = 0.0                  # 0 disables sensor noise

    assert abs(profile.fov_y() - math.radians(40.0)) < 1e-4

.. nyx-test: compile-only

.. code-block:: python

    nps.export_camera_profile_file("my_profile.json", profile)

    # The file is then consumed by a NyxCameraOptions instance:
    #
    #     NyxCameraOptions(..., camera_profile="my_profile.json")

.. note::

   The wheel ships a ready-made profile at
   ``gs_nyx/assets/camera_profiles/sony_a7_r5_24mm.json`` (Sony A7R V body,
   24 mm lens, ACES tone mapping). Without a ``camera_profile`` the plugin
   writes a default profile per camera from ``fov`` with Reinhard tone
   mapping, so existing scenes render as before.
