.. rubric:: Example

A Gaussian-splat capture (a ``.ply`` exported from a 3DGS trainer) is
rendered by declaring a ``GaussianField`` asset and passing it to a camera
through
:attr:`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.light_fields`:

.. code-block:: python

    import gs_nyx.nyx_py_sdk as nps

    capture            = nps.LightFieldAsset()
    capture.type       = nps.ELightFieldType.GaussianField
    capture.uri        = "path/to/capture.ply"
    capture.position   = nps.float3(0.0, 0.0, 0.0)
    # 90° rotation about the world up axis to stand the capture upright in
    # Genesis' Z-up frame. See :func:`quaternion_conjugate` for the
    # (x, y, z, w) unit-quaternion convention.
    capture.rotation   = nps.quaternion(0.0, 0.0, -0.70710678, 0.70710678)
    capture.scale      = nps.float3(1.0, 1.0, 1.0)
    capture.multiplier = 1.0

    # The asset is then consumed by a NyxCameraOptions instance:
    #
    #     NyxCameraOptions(..., light_fields=(capture,))

.. note::

   :attr:`type` selects the underlying representation:
   :attr:`~ELightFieldType.GaussianField` for ``.ply`` Gaussian splats and
   :attr:`~ELightFieldType.SparseGrid` for volumetric sparse-grid radiance
   fields. The renderer dispatches to a different code path for each, so the
   ``uri`` must point to a file matching the declared type.
