.. rubric:: Example

``pick_pixel`` casts a ray from the camera through the requested pixel
(top-left origin) and returns either ``None`` if the ray exits the scene
(e.g. through the sky / environment map) or a
:class:`~gs_nyx_plugin.nyx_camera_sensor.NyxPickPixelResult` naming the hit
entity, its link, and the world-space hit position in Genesis Z-up:

.. nyx-test: compile-only

.. code-block:: python

    # ``cam`` is a built NyxCameraSensor returned by ``scene.add_sensor(...)``;
    # see the user guide for the surrounding scene-build boilerplate.
    res = cam.pick_pixel(camera_index=0, x=320, y=240)
    if res is None:
        print("ray hit nothing (background)")
    else:
        wx, wy, wz = res.position
        print(f"hit {res.entity} link={res.link_name!r} at ({wx:.2f}, {wy:.2f}, {wz:.2f})")

.. note::

   ``link_name`` is morph-dependent: the link name for URDF entities, a
   ``"<link>_<vgeom_idx>"`` string for MJCF entities, and an empty string
   for every other morph type. ``camera_index`` is this sensor's slot in
   its shared metadata, ``0`` for the only camera in the scene; multi-camera
   setups index in registration order.
