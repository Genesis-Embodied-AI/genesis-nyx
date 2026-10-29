# Known issues

Nyx is a native C++ / Vulkan library and prints diagnostics to `stderr` from inside the native code. A handful of these are emitted in situations the plugin handles correctly, so the messages are noise rather than failures. This page lists the messages we know about and confirms that you can ignore them.

```{note}
The messages on this page are benign. If you see one of them, the run will still produce correct frames; you can ignore them. If you see an error that is *not* listed here and the run also misbehaves, that is a real bug and worth reporting.
```

## Runtime warning

During a render pass you may see:

```text
[WARNING][Transform Component] Multiple references at pointing to the same instance.
```

The rendered frames are unaffected.

## Informational messages

These are printed through the Genesis logger or as plain warnings by the plugin itself. They describe a decision the plugin made, not a problem.

| Message | Meaning |
|---|---|
| `[NyxRenderer] Nyx renders on torch device N, selecting it.` | Nyx picked a GPU that was not torch's current device. The plugin switched the current torch device so new tensors land next to the rendered images. See {doc}`advanced/gpu_backends`. |
| `[WARNING] NyxCameraOptions: 'camera_profile' was provided, so 'fov' will be ignored.` | The field of view lives in the camera profile. Remove `fov` from the options, or drop the profile. See {doc}`advanced/camera_profiles`. |
| A warning that the scene has no lights and no environment maps. | The frame will be lit by Nyx's default mid-grey sky only. See {doc}`advanced/lights`. |

## Controlling log verbosity

The native library writes `Warning` and `Error` messages by default. Use {py:func}`~gs_nyx.nyx_py_sdk.set_log_flags` with {py:class}`~gs_nyx.nyx_py_sdk.ELogLevel` to change that, for instance to silence the benign warning above or to enable informational output while debugging:

```python
import gs_nyx.nyx_py_sdk as nps

nps.set_log_flags(nps.ELogLevel.Error)                          # errors only
nps.set_log_flags(nps.ELogLevel.Info | nps.ELogLevel.Warning | nps.ELogLevel.Error)
print(nps.log_flags())
```

## What is *not* in this list

If you encounter any of the following, the plugin is likely in a genuinely bad state and you should not treat it as benign:

- A Python exception originating from `gs_nyx` or `gs_nyx_plugin` (anything that surfaces as a traceback rather than a `stderr` line from the native library).
- A `RuntimeError` raised by `NyxRenderer.startup`. The log line printed just before it names the cause, usually a missing Vulkan device or driver feature.
- A {py:class}`~gs_nyx.nyx_external_memory.NyxExternalMemoryError`. The compute-side import of Nyx's buffers failed; the most common causes are a torch build that does not match the GPU vendor Nyx picked, or a GPU torch cannot see. See the troubleshooting table in {doc}`installation`.
- A CUDA or HIP error mentioning `out of memory`, `illegal memory access`, or `device-side assert`.
- An assertion that mentions a specific asset, sensor, or scene object (`SceneAsset`, `CameraAsset`, `LightAsset`, etc.). Those name a thing in your scene that the renderer rejected.

When in doubt, the test is whether {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.read` still returns a sensible image: a black or NaN-filled frame means something is wrong; a normal-looking frame plus one of the messages above means you can keep going.

## Status

All of the messages listed above are known to the maintainers and will be addressed in a future release. They are tracked as cosmetic issues, not as functional bugs, which is why they have not been silenced yet.

## See also

- {doc}`installation`: driver, torch build and wheel requirements.
- {doc}`advanced/gpu_backends`: how Nyx's GPU is paired with torch.
- {doc}`advanced/sensor_lifecycle`: why a single renderer is shared across sensors and environments.
