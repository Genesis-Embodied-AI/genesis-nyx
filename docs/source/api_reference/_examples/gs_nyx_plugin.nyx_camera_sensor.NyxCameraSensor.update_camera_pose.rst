.. rubric:: Example

``update_camera_pose`` swaps the camera's pose for the next render and
**detaches** the sensor from any rig it was previously attached to.
This is the right tool for free-roaming or scripted camera moves; if you
need the camera to follow an entity per environment, configure the
attachment fields on
:class:`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` instead.

.. nyx-test: compile-only

.. code-block:: python

    # ``cam`` is a built NyxCameraSensor; ``scene`` is the owning Genesis Scene.
    cam.update_camera_pose(
        pos    = (0.0, 0.0, 5.0),     # top-down vantage, 5 m above origin.
        lookat = (0.0, 0.0, 0.0),
        up     = (1.0, 0.0, 0.0),     # +X is "up" in the image.
    )
    scene.step()                       # re-render at the new pose.
    frame = cam.read().rgb[0].cpu().numpy()

.. note::

   All three arguments are optional; passing only ``pos`` leaves ``lookat``
   and ``up`` unchanged. Coordinates are in Genesis Z-up world space and
   apply to every parallel environment uniformly — there is no per-env
   variant of this call. For per-env poses, attach the camera to a per-env
   entity through ``NyxCameraOptions.entity_idx`` / ``link_idx_local``.
