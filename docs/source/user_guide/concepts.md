# Concepts

```{note}
This page is a stub. Flesh it out as the API stabilises. The intent is to give a one-page mental model that bridges the {doc}`quickstart` and the {doc}`../api_reference/index`.
```

## The renderer lifecycle

A {py:class}`~gs_nyx.nyx_py_renderer.NyxRenderer` instance progresses through three states:

1. **Constructed**, Python object exists, no GPU resources allocated.
2. **Started**, the Nyx SDK has been booted with a {py:class}`~gs_nyx.nyx_py_renderer.BridgeStartupParams`; a GPU has been picked (by memory size, or by vendor / adapter index through its `pickStrategy`), and the Vulkan context, swapchain, and asset pools are live. The plugin registers the SDK's start hook with Genesis at import time, so `gs.init()` triggers this transition for you.
3. **Shut down**, all GPU resources have been released and the instance is no longer usable. `gs.destroy()` (or interpreter teardown) triggers this transition through the same registered stop hook.

## Scenes and assets

A scene is the renderer's view of "what exists". It is composed of typed assets:

| Asset class | Role |
|---|---|
| {py:class}`~gs_nyx.nyx_py_sdk.SceneAsset` | Container that owns the rest |
| {py:class}`~gs_nyx.nyx_py_sdk.InstanceAsset` | One placed mesh, with a transform and a material binding |
| {py:class}`~gs_nyx.nyx_py_sdk.CameraAsset` | A virtual camera with a pose, a resolution and a reference to a camera profile |
| {py:class}`~gs_nyx.nyx_py_sdk.CameraProfileAsset` | The physical camera model: lens, sensor and colour management (see {doc}`advanced/camera_profiles`) |
| {py:class}`~gs_nyx.nyx_py_sdk.LightAsset` | A point / directional / spot / area light |
| {py:class}`~gs_nyx.nyx_py_sdk.MaterialAsset` | Shader parameters and texture references |
| {py:class}`~gs_nyx.nyx_py_sdk.LightFieldAsset` | A captured radiance field (Gaussian splat or sparse grid) |
| {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset` | Image-based lighting |

Each asset has a stable UUID. The plugin serialises the scene to JSON once, at `scene.build()`, and the renderer loads it from disk.

## Driving the scene from Python

Per-frame state does not go through the asset model. The renderer is told which buffers to allocate through a {py:class}`~gs_nyx.nyx_py_renderer.BridgeUpdateDesc` (how many rigid geometries, cameras, deformable vertices and triangles, and how many environments), and it then **exports** those buffers ({py:class}`~gs_nyx.nyx_py_renderer.EBridgeBuffer`) as OS handles. The plugin imports them into PyTorch with {py:class}`~gs_nyx.nyx_external_memory.NyxExternalMemoryImporter`, so writing a new transform or a new vertex position is a plain tensor copy into memory the renderer owns. This is what makes the plugin independent of the compute API: the same code runs on a CUDA torch build and on a ROCm torch build (see {doc}`advanced/gpu_backends`).

The rendered images come back the same way: the packed colour output is one more exported buffer, and `cam.read().rgb` is a view into it.

## Render modes

{py:class}`~gs_nyx.nyx_py_renderer.ERenderMode` selects the rendering algorithm:

- {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.Forward`, rasterisation. Fastest. Suited for visualisation and RL rollouts.
- {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.FastPathTracer`, biased path tracer. Photorealistic with manageable cost.
- {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.RefPathTracer`, reference unbiased path tracer. Slow but ground-truth.
- {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.Debug`, visualise normals, depths, materials, etc. (see {py:class}`~gs_nyx.nyx_py_renderer.EDebugView`).

## Integrating with Genesis

The plugin is designed to ingest scene state from a {py:class}`~genesis.engine.scene.Scene`, translate it into Nyx assets, and produce rendered frames that can be returned to Genesis as observations.

See {doc}`examples/attached_camera` for the end-to-end pattern.
