# Known issues

Nyx is wrapped in C++/CUDA and prints diagnostics to `stderr` from inside the native library. A handful of these are emitted in situations the plugin handles correctly, so the messages are noise rather than failures. This page lists the messages we know about and confirms that you can ignore them.

```{note}
The messages on this page are benign. If you see one of them, the run will still produce correct frames; you can ignore them. If you see an error that is *not* listed here and the run also misbehaves, that is a real bug and worth reporting.
```

## Runtime warning

During a render pass you may see:

```text
[WARNING][Transform Component] Multiple references at pointing to the same instance.
```

The rendered frames are unaffected.

## What is *not* in this list

If you encounter any of the following, the plugin is likely in a genuinely bad state and you should not treat it as benign:

- A Python exception originating from `gs_nyx` or `gs_nyx_plugin` (anything that surfaces as a traceback rather than a `stderr` line from the native library).
- A CUDA error mentioning `out of memory`, `illegal memory access`, or `device-side assert`.
- An assertion that mentions a specific asset, sensor, or scene object (`SceneAsset`, `CameraAsset`, `LightAsset`, etc.). Those name a thing in your scene that the renderer rejected.

When in doubt, the test is whether {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.read` still returns a sensible image: a black or NaN-filled frame means something is wrong; a normal-looking frame plus one of the messages above means you can keep going.

## Status

All of the messages listed above are known to the maintainers and will be addressed in a future release. They are tracked as cosmetic issues, not as functional bugs, which is why they have not been silenced yet.

## See also

- {doc}`installation`: driver and wheel requirements.
- {doc}`advanced/sensor_lifecycle`: why a single renderer is shared across sensors and environments.
