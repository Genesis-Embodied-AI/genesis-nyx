# Sensor lifecycle

The {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` integrates the Nyx renderer with Genesis using a render-on-read model. [`Scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) advances physics but does not render. Rendering is performed on the first [`read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) call that follows a step, and the resulting image is cached in a CUDA tensor and reused by every subsequent `read()` until the simulation time advances or the camera pose changes.

This page describes the sensor's order of operations across its three phases: construction, build, and the per-step render-on-read cycle.

## Lifecycle overview

| Phase | Triggered by | GPU work |
|---|---|---|
| Construction | [`scene.add_sensor()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.add_sensor) | None |
| Build | [`scene.build()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.build) | Renderer startup, buffer allocation |
| Render-on-read | [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) after [`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) | Per-camera, per-env render pass |
| Cached read | `cam.read()` while not stale | None |
| Destruction | Scene destruction | Renderer shutdown, buffer release |

## Construction

`scene.add_sensor(NyxCameraOptions(...))` instantiates a {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` from the given {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` and registers it with the sensor manager. The sensor options are stored on the instance. No renderer is created and no GPU resources are allocated.

A single scene can contain multiple Nyx sensors. They share a single renderer instance and a single shared image cache.

## Build

`scene.build()` calls `build()` on every sensor in registration order. For each Nyx sensor, `build()` performs the following steps:

1. Attach to the shared metadata block used by every Nyx sensor in the scene.
2. Append a camera definition to the shared camera list (resolution, FOV, pose, clip planes, sample count, tone mapper, anti-aliasing).
3. Allocate a `(B, H, W, 3)` `torch.uint8` CUDA tensor in the shared image cache, keyed by the sensor index.

When the last Nyx sensor finishes building, that sensor performs the one-time scene initialisation:

1. Collect lights, environment maps, and light fields from every Nyx sensor.
2. Export a JSON scene description to `__nyx_cache__/<random>/`.
3. Create a single renderer instance. The internal viewport is sized to the maximum resolution across all sensors.
4. Allocate CUDA interop buffers: rigid transforms, deformable vertex, UV, and index buffers, and camera pose tensors.
5. Pre-upload static deformable data (UVs and fixed face indices).

After `build()` returns, the renderer is initialised and the sensor is ready to render on the next `read()`.

```{note}
All Nyx sensors must be added before `scene.build()`. Adding sensors after the build is not supported.
```

```{note}
All Nyx sensors must use the same `render_mode`. The plugin raises an exception if the values diverge.
```

## Render-on-read

[`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) advances `scene.t` and does not render. The next [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) triggers the render.

`read()` is inherited from `BaseCameraSensor` and runs the following steps:

| Step | Action |
|---|---|
| 1. Staleness check | If `shared_metadata.last_render_timestep != scene.t`, every Nyx sensor's `_stale` flag is set to `True` and `last_render_timestep` is updated to `scene.t`. |
| 2. Cached path | If `_stale` is `False`, the cached image is returned without further work. |
| 3. Pose update | If the camera is attached to a rigid link, `move_to_attach()` recomputes its world transform. |
| 4. Render | `_render_current_state()` is called. This renders every Nyx camera for every environment in a single pass. |
| 5. Mark fresh | The `_stale` flag is cleared. |
| 6. Return | The requested environments are sliced from the cached `(B, H, W, 3)` tensor and wrapped in a {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraData` namedtuple with an `rgb` field. |

Because `_render_current_state()` renders every Nyx camera in one call, only the first `read()` of the step performs the full render pass. Subsequent `read()` calls on other Nyx sensors in the same step return their pre-rendered image from the cache.

## Render pass

`_render_current_state()` runs a one-time setup block followed by a per-environment loop.

**Per-step setup**

| Step | Action |
|---|---|
| 1 | `scene.visualizer.update_visual_states()` flushes Genesis visual state. |
| 2 | For every attached sensor, `move_to_attach()` computes its per-env world transform. |
| 3 | `renderer.update()` pumps the GUI event loop and updates renderer delta time. |

**Per environment** (`env_idx` in `0..B-1`)

| Step | Action |
|---|---|
| 1 | For every Nyx sensor, write its position, look-at, and up vector into the renderer's CUDA pose tensors. Attached cameras use their per-env transform; static cameras use the same pose for every env. |
| 2 | `update_scene(env_idx)` copies the env's rigid `vgeoms` pose, deformable solver vertex positions (FEM, PBD, MPM-visual), and reconstructed MPM-recon meshes, then selects the env map. |
| 3 | `update_scene_buffers()` syncs the new buffer pointers to the renderer. |
| 4 | For every Nyx sensor, `render_frame(camera_index)` is called. The returned `(H, W, 3)` `uint8` tensor is copied into `image_cache[sensor_idx][env_idx]`. |

When the env loop completes, every sensor's cache holds the current step's frames for every env. All sensors are marked fresh and `last_render_timestep` is set to `scene.t`.

## Image cache

The image cache is stored on {py:class}`~gs_nyx_plugin.nyx_camera_shared_metadata.NyxCameraSharedMetadata` `.image_cache` as a `dict[int, torch.Tensor]` keyed by sensor index.

| Property | Value |
|---|---|
| Shape | `(B, H, W, 3)` |
| Dtype | `torch.uint8` |
| Device | CUDA |
| Sized per | Sensor (different sensors may have different resolutions) |
| Lifetime | Tied to the scene; freed on scene destruction |

`cam.read().rgb` returns a view into the cache. Convert to a CPU NumPy array with `.cpu().numpy()` if required.

The renderer's internal viewport is sized to the maximum resolution across all Nyx sensors in the scene. Individual camera viewports are clipped to their configured resolution at render time.

## Cache invalidation

The cache is invalidated when:

- `scene.t` changes. `scene.step()` advances simulation time, which marks every Nyx sensor stale on the next `read()`.
- An attached camera's link moves. Handled inside `_render_current_state()` via `move_to_attach()`; the new transform is pushed before rendering.
- {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.update_camera_pose` is called. This detaches the camera from any rig and forces a re-render on the next `read()`.

The cache is **not** invalidated when:

- `cam.read()` is called multiple times within the same step.
- Non-pose options such as `spp` or `denoise` are mutated after `scene.build()`. These options are read at build time only.

## Multi-camera scenes

The plugin enforces a single shared renderer per scene. This has three consequences:

- All Nyx sensors must use the same `render_mode`.
- All Nyx sensors must be registered before `scene.build()` is called.
- Reading any one Nyx sensor renders all of them. For setups with identical camera layouts per env, this is the intended behaviour. For setups with an expensive secondary camera that is read infrequently, the secondary camera is still rendered on every step where any Nyx sensor is read.

## Live window

When `open_window=True`, the GUI event loop is serviced inside `_render_current_state()` via the `renderer.update()` call. This is the only point at which window events are pumped.

```{warning}
If `cam.read()` is not called every step, the live window appears frozen between reads. Call `read()` once per step for a smooth preview.
```

## See also

- {doc}`../quickstart` — Minimal end-to-end script.
- {doc}`../concepts` — Renderer states and asset model.
