.. rubric:: Example

For a unit quaternion, the conjugate is also its inverse, flip the sign of
the vector part and the rotation is undone:

.. code-block:: python

    import gs_nyx.nyx_py_sdk as nps

    # 90° rotation around +Z.
    q = nps.quaternion()
    q.w, q.x, q.y, q.z = 0.70710678, 0.0, 0.0, 0.70710678

    q_inv = nps.quaternion_conjugate(q)
    # q_inv.w, q_inv.x, q_inv.y, q_inv.z == (0.70710678, -0.0, -0.0, -0.70710678)

    # Composing a unit quaternion with its conjugate yields identity.
    identity = nps.quaternion_mul(q, q_inv)
    # identity.w, identity.x, identity.y, identity.z == (1.0, 0.0, 0.0, 0.0)

.. note::

   For non-unit quaternions, ``quaternion_conjugate`` is **not** the inverse,
   use it only when you've already normalised.
