# Concepts

```{note}
This page is a stub. Flesh it out as the API stabilises. The intent is to give a one-page mental model that bridges the {doc}`quickstart` and the {doc}`../api_reference/index`.
```

## The renderer lifecycle

A {py:class}`~gs_nyx.nyx_py_renderer.NyxRenderer` instance progresses through three states:

1. **Constructed**, Python object exists, no GPU resources allocated.
2. **Started**, the Nyx SDK has been booted with a {py:class}`~gs_nyx.nyx_py_renderer.BridgeStartupParams`; GPU context, swapchain, and asset pools are live. The plugin registers the SDK's start hook with Genesis at import time, so `gs.init()` triggers this transition for you.
3. **Shut down**, all GPU resources have been released and the instance is no longer usable. `gs.destroy()` (or interpreter teardown) triggers this transition through the same registered stop hook.

## Scenes and assets

A scene is the renderer's view of "what exists". It is composed of typed assets:

| Asset class | Role |
|---|---|
| {py:class}`~gs_nyx.nyx_py_sdk.SceneAsset` | Container that owns the rest |
| {py:class}`~gs_nyx.nyx_py_sdk.InstanceAsset` | One placed mesh, with a transform and a material binding |
| {py:class}`~gs_nyx.nyx_py_sdk.CameraAsset` | A virtual camera with intrinsics and a pose |
| {py:class}`~gs_nyx.nyx_py_sdk.LightAsset` | A point / directional / area light |
| {py:class}`~gs_nyx.nyx_py_sdk.MaterialAsset` | Shader parameters and texture references |
| {py:class}`~gs_nyx.nyx_py_sdk.LightFieldAsset` | A captured radiance field (Gaussian splat or sparse grid) attached to a camera |
| {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset` | Image-based lighting |

Each asset has a stable UUID. The renderer is told about changes via {py:class}`~gs_nyx.nyx_py_renderer.BridgeUpdateDesc` (which assets exist) and {py:class}`~gs_nyx.nyx_py_renderer.BridgeUpdateData` (what their per-frame values are).

## Render modes

{py:class}`~gs_nyx.nyx_py_renderer.ERenderMode` selects the rendering algorithm:

- {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.Forward`, rasterisation. Fastest. Suited for visualisation and RL rollouts.
- {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.FastPathTracer`, biased path tracer. Photorealistic with manageable cost.
- {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.RefPathTracer`, reference unbiased path tracer. Slow but ground-truth.
- {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.Debug`, visualise normals, depths, materials, etc. (see {py:class}`~gs_nyx.nyx_py_renderer.EDebugView`).

## Integrating with Genesis

The plugin is designed to ingest scene state from a {py:class}`~genesis.engine.scene.Scene`, translate it into Nyx assets, and produce rendered frames that can be returned to Genesis as observations.

See {doc}`examples/attached_camera` for the end-to-end pattern.
