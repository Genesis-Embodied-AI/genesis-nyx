# Changelog

Release notes for the wheels documented on this site. Version numbers refer to `gs-nyx` (renderer) and `gs-nyx-plugin` (Genesis integration).

## gs-nyx 0.1.9 / gs-nyx-plugin 0.1.10

### New

- **AMD GPUs through ROCm.** The renderer no longer bundles a CUDA runtime. Its buffers are exported as OS handles and imported into whichever compute API PyTorch was built for, CUDA or HIP, by the new {py:mod}`gs_nyx.nyx_external_memory` module. A ROCm build of PyTorch drives AMD GPUs with no change in user code, on Windows 11 and Linux. See {doc}`advanced/gpu_backends`.
- **GPU selection.** {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.gpu_vendor` picks the vendor Nyx renders on; by default the GPU with the most memory is used ({py:class}`~gs_nyx.nyx_py_sdk.EPickStrategy`, {py:class}`~gs_nyx.nyx_py_sdk.EGPUVendor`).
- **Batched multi-environment rendering.** Every `(env, camera)` pair is rendered by a single native call. The plugin uploads the state of all environments in one copy and no longer loops over environments in Python. See {doc}`advanced/sensor_lifecycle`.
- **Camera profiles.** {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.camera_profile` references a {py:class}`~gs_nyx.nyx_py_sdk.CameraProfileAsset` JSON file describing lens, sensor and colour management. A Sony A7R V / 24 mm profile ships with the wheel. See {doc}`advanced/camera_profiles`.
- **Tone mappers.** `Neutral` and `ACES_1_3` join `Off`, `Reinhard` and `LUT` in {py:class}`~gs_nyx.nyx_py_sdk.EToneMapper`.
- **Parallax-corrected environment maps.** {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset` gains `parallax` ({py:class}`~gs_nyx.nyx_py_sdk.EEnvMapParallax`) and the `parallax_box_*` fields. See {doc}`advanced/environment_maps`.
- **Transmissive materials in the SDK.** {py:class}`~gs_nyx.nyx_py_sdk.MaterialAsset` exposes `transmission`, `thickness`, `absorption` and `ior`. The plugin does not map Genesis `Glass` / `Water` surfaces to them yet.
- **Log control.** {py:func}`~gs_nyx.nyx_py_sdk.set_log_flags` / {py:func}`~gs_nyx.nyx_py_sdk.log_flags` select which {py:class}`~gs_nyx.nyx_py_sdk.ELogLevel` levels the native library prints.
- **Scene reload.** {py:meth}`~gs_nyx.nyx_py_renderer.NyxRenderer.reload` re-imports only the assets that changed on disk.
- **Python 3.13** is now a supported interpreter.

### Breaking changes

- `NyxCameraOptions.tone_mapper` was removed. Set the tone mapper in a camera profile instead ({doc}`advanced/camera_profiles`).
- `EnvironmentMapAsset.rotation` is now expressed in **degrees** (it was radians).
- The plugin requires **Genesis World 1.4.x** (`genesis-world>=1.4.0,<1.5.0`).
- `NyxCameraOptions.window_size` defaults to `(1920, 1080)` (was `(1024, 1024)`).
- Lower-level renderer API: `BridgeUpdateData`, `update_scene_buffers()` and `BridgeStartupParams.cudaDevice` are gone. Buffers are exported with {py:meth}`~gs_nyx.nyx_py_renderer.NyxRenderer.export_buffer` ({py:class}`~gs_nyx.nyx_py_renderer.EBridgeBuffer`), the GPU is chosen with `pickStrategy` / `deviceData`, and {py:meth}`~gs_nyx.nyx_py_renderer.NyxRenderer.render_batch` replaces the per-camera `render_frame` return value. {py:class}`~gs_nyx_plugin.nyx_renderer.NyxPyRenderer` keeps a compatible `render(camera_index, env_index)` and adds `render_all()` and `camera_image()`.
- Video encoder: `encode_frame_srgb_to_cpu` takes only the host output pointer; the input frame is written into the buffer returned by `export_input_buffer()`.

## gs-nyx 0.1.1 / gs-nyx-plugin 0.1.1

Initial public documentation release. NVIDIA / CUDA only.
