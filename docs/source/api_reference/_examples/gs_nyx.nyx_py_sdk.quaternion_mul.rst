.. rubric:: Example

The Hamilton product composes rotations right-to-left, so
``quaternion_mul(b, a)`` rotates first by ``a`` and then by ``b`` (the same
ordering as 4×4 matrix multiplication on column vectors):

.. code-block:: python

    import math
    import gs_nyx.nyx_py_sdk as nps

    # 45° rotation about +Z, written as a unit quaternion in (x, y, z, w).
    half_w = math.cos(math.radians(22.5))
    half_z = math.sin(math.radians(22.5))
    q45 = nps.quaternion(0.0, 0.0, half_z, half_w)

    # Composing two 45° rotations yields a 90° rotation about the same axis.
    q90 = nps.quaternion_mul(q45, q45)
    # q90.w ≈ cos(45°) ≈ 0.70710678
    # q90.z ≈ sin(45°) ≈ 0.70710678

.. note::

   ``quaternion_mul`` does not renormalise its result. After many chained
   compositions, divide each component by ``sqrt(w² + x² + y² + z²)`` to
   keep numerical drift in check; renormalisation matters because
   :func:`quaternion_conjugate` only inverts *unit* quaternions.
