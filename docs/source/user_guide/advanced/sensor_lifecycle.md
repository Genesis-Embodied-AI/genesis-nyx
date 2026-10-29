# Sensor lifecycle

The {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` integrates the Nyx renderer with Genesis using a render-on-read model. [`Scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) advances physics but does not render. Rendering is performed on the first [`read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) call that follows a step, for every Nyx camera and every environment at once, and the resulting images are kept in GPU tensors that alias the renderer's output until the simulation advances or a camera pose changes.

This page describes the sensor's order of operations across its three phases: construction, build, and the per-step render-on-read cycle.

## Lifecycle overview

| Phase | Triggered by | GPU work |
|---|---|---|
| Construction | [`scene.add_sensor()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.add_sensor) | None |
| Build | [`scene.build()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.build) | Renderer startup, GPU pairing, buffer allocation and import |
| Render-on-read | [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) after [`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) | One batched upload, one batched render of every (env, camera) pair |
| Cached read | `cam.read()` while not stale | None |
| Destruction | Scene destruction | Buffer release, renderer shutdown |

## Construction

`scene.add_sensor(NyxCameraOptions(...))` instantiates a {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` from the given {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` and registers it with the sensor manager. The sensor options are stored on the instance. No renderer is created and no GPU resources are allocated.

A single scene can contain multiple Nyx sensors. They share a single renderer instance and a single shared image cache.

## Build

`scene.build()` calls `build()` on every sensor in registration order. For each Nyx sensor, `build()` performs the following steps:

1. Verify that torch has a GPU backend, CUDA or ROCm. A CPU-only torch raises immediately.
2. Attach to the shared metadata block used by every Nyx sensor in the scene.
3. Append a camera definition to the shared camera list (resolution, pose, clip planes, sample count, denoising, anti-aliasing, camera profile).

When the last Nyx sensor finishes building, that sensor performs the one-time scene initialisation:

1. Collect lights, environment maps, and light fields from every Nyx sensor.
2. Export a JSON scene description to `__nyx_cache__/<random>/`, together with one camera-profile JSON per camera that did not supply its own (see {doc}`camera_profiles`).
3. Create a single renderer instance. The internal viewport is sized to the maximum resolution across all sensors. The GPU is picked by memory size, or by vendor when {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.gpu_vendor` is set on the first sensor.
4. Pair the torch device with the GPU Nyx picked and make it the current torch device (see {doc}`gpu_backends`).
5. Ask Nyx to allocate its interop buffers for `n_envs` environments (rigid transforms, camera poses, deformable vertices / UVs / indices, and the packed colour output), then import every one of them as a torch tensor. The tensors alias Nyx's memory.
6. Upload static deformable data (UVs and fixed face indices) and replicate it to every env.
7. Hand every sensor a `(B, H, W, 3)` `uint8` view into the packed colour output as its image cache entry.

After `build()` returns, the renderer is initialised and the sensor is ready to render on the next `read()`.

```{note}
All Nyx sensors must be added before `scene.build()`. Adding sensors after the build is not supported.
```

```{note}
All Nyx sensors must use the same `render_mode`. The plugin raises an exception if the values diverge.
```

## Render-on-read

[`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) advances the simulation and does not render. The next [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) triggers the render.

`read()` is inherited from `BaseCameraSensor` and runs the following steps:

| Step | Action |
|---|---|
| 1. Staleness check | If the renderer last ran at a different global step than the simulator is at, every Nyx sensor's `_stale` flag is set to `True`. |
| 2. Cached path | If `_stale` is `False`, the cached image is returned without further work. |
| 3. Pose update | If the camera is attached to a rigid link, `move_to_attach()` recomputes its world transform for every env. |
| 4. Render | `_render_current_state()` is called. This renders every Nyx camera for every environment in a single pass. |
| 5. Mark fresh | The `_stale` flag is cleared on every Nyx sensor. |
| 6. Return | The requested environments are sliced from the cached `(B, H, W, 3)` view and wrapped in a {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraData` namedtuple with an `rgb` field. |

Because `_render_current_state()` renders every Nyx camera in one call, only the first `read()` of the step performs the render pass. Subsequent `read()` calls on other Nyx sensors in the same step return their pre-rendered image from the cache.

## Render pass

`_render_current_state()` is a short, fully batched sequence. There is no per-environment loop in Python.

| Step | Action |
|---|---|
| 1 | `scene.visualizer.update_visual_states()` flushes Genesis visual state. |
| 2 | For every attached sensor, `move_to_attach()` computes its `(B, 3)` per-env position, look-at and up vectors. |
| 3 | `renderer.update()` pumps the GUI event loop and advances the renderer's animation clock. |
| 4 | For every Nyx sensor, its camera pose is written into the camera buffers in one batched copy: attached cameras write their per-env poses, static cameras broadcast a single pose over the env dimension. |
| 5 | `renderer.update_scene()` copies the rigid `vgeoms` poses and the deformable vertex positions (FEM, PBD, MPM-visual) of **all envs** into the imported buffers in one `copy_` per section. Particle-reconstructed surfaces (MPM-recon, SPH-recon) are meshed on the CPU per entity and per env and streamed into their slots; unused triangle budget is padded with degenerate triangles. The plugin then waits for torch's GPU work and tells Nyx the buffers changed. |
| 6 | `renderer.render_all()` calls the native `render_batch()`, which runs the interop dispatches for each env, renders every camera, and writes every image into the packed colour buffer. Nyx waits for the GPU before returning. Per-env environment maps are selected inside this batch. |

When the call returns, every sensor's image view holds the current step's frames for every env. All sensors are marked fresh and the last-render step is recorded.

## Image cache

The image cache is stored on {py:class}`~gs_nyx_plugin.nyx_camera_shared_metadata.NyxCameraSharedMetadata` `.image_cache` as a `dict[int, torch.Tensor]` keyed by sensor index. Each entry is a strided view into the renderer's packed colour output, created once at build time.

| Property | Value |
|---|---|
| Shape | `(B, H, W, 3)` |
| Dtype | `torch.uint8` |
| Device | The torch device paired with the renderer's GPU (CUDA or ROCm) |
| Sized per | Sensor (different sensors may have different resolutions) |
| Lifetime | Tied to the scene; released on scene destruction |

`cam.read().rgb` returns that view, without a copy. The view is overwritten in place by every render pass, so call `.clone()` or `.cpu()` to keep a frame across steps.

The renderer's internal viewport is sized to the maximum resolution across all Nyx sensors in the scene. Individual camera viewports are clipped to their configured resolution at render time.

## Cache invalidation

The cache is invalidated when:

- The simulation advances. `scene.step()` moves the global step counter, which marks every Nyx sensor stale on the next `read()`.
- An attached camera's link moves. Handled inside `_render_current_state()` via `move_to_attach()`; the new transforms are pushed before rendering.
- {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.update_camera_pose` is called. This detaches the camera from any rig and forces a re-render on the next `read()`.

The cache is **not** invalidated when:

- `cam.read()` is called multiple times within the same step.
- Non-pose options such as `spp`, `denoise` or `camera_profile` are mutated after `scene.build()`. These options are read at build time only.

## Multi-camera and multi-environment scenes

The plugin enforces a single shared renderer per scene. This has three consequences:

- All Nyx sensors must use the same `render_mode`.
- All Nyx sensors must be registered before `scene.build()` is called.
- Reading any one Nyx sensor renders all of them, for every environment. For setups with identical camera layouts per env, this is the intended behaviour. For setups with an expensive secondary camera that is read infrequently, the secondary camera is still rendered on every step where any Nyx sensor is read.

Environments are batched inside Nyx: one upload and one synchronization cover every env, and the per-env cost is GPU render time only. GPU time still scales with the number of (env, camera) pairs.

## Destruction

When the scene is destroyed, the shared metadata's `destroy()` hook releases every imported buffer, closes the compute context, shuts the native renderer down, and removes the `__nyx_cache__/<id>/` folder holding the scene description, the camera profiles and any exported `.obj` files.

## Live window

When `open_window=True`, the GUI event loop is serviced inside `_render_current_state()` via the `renderer.update()` call. This is the only point at which window events are pumped. The window size is set by `window_size` (default `(1920, 1080)`).

```{warning}
If `cam.read()` is not called every step, the live window appears frozen between reads. Call `read()` once per step for a smooth preview.
```

## See also

- {doc}`../quickstart` — Minimal end-to-end script.
- {doc}`../concepts` — Renderer states and asset model.
- {doc}`gpu_backends` — How the GPU is picked and how buffers are shared with torch.
