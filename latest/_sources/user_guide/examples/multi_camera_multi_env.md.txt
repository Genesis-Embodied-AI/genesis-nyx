# Multiple cameras and parallel environments

Two orthogonal patterns the Nyx plugin composes for free: **multiple cameras** in one scene and **multiple Genesis environments** built in parallel. This example puts both to work at once — two {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor`s and `n_envs=4` — and tiles the resulting `(2, 4, H, W, 3)` image stack into a single PNG so the symmetry is visible at a glance.

{{ example_07_multi_camera_multi_env_screenshot }}

Both features are independent knobs on the same APIs — multi-camera is a second `scene.add_sensor` call, multi-env is a `n_envs=N` argument to `scene.build`. Either alone is already useful (multi-view supervision, batched RL rollouts, synthetic data generation). The two sections below cover what each one changes; the rest of the page covers the bits that only show up when you combine them.

## What changes when you add a second camera

Concretely, nothing in your code except a second `scene.add_sensor(NyxCameraOptions(...))` call. Each sensor gets its own resolution, FOV, pose, attachment, and {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.pick_pixel` entry-point. Under the hood the plugin keeps **one** native renderer alive for the whole scene and contributes every camera (plus its lights, env maps and light fields) to that shared instance.

That sharing is worth a moment because it turns three potential footguns into non-issues:

- **Lights and light fields are scene-wide.** `lights` and `light_fields` from every Nyx sensor are merged at build time, so every env sees the union of them through both cameras. Declare them on whichever camera reads best in code; duplicating them on every camera duplicates the underlying asset. Env maps are the exception — see [Different lighting per environment](#different-lighting-per-environment) below.
- **Render mode is scene-wide too.** Every Nyx sensor must agree on {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.render_mode` — the shared renderer can only serve one mode at a time. Mixing {py:class}`~gs_nyx.nyx_py_renderer.ERenderMode` values like {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.FastPathTracer` and {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.Debug` raises at build.
- **`pick_pixel` indexes registration order.** The first sensor added is `camera_index=0`, the second `1`, and so on, all reachable from {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.pick_pixel` `(camera_index, x, y)` on any sensor. See {doc}`object_picking` for the ray API itself.

## What changes when you add parallel environments

[`scene.build(n_envs=N)`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.build) widens every sensor's read shape from `(H, W, 3)` to `(N, H, W, 3)`. The cost is honest: the plugin renders one env at a time internally, so wall-clock time grows linearly with `N`. The benefit is that the simulator does too — one [`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) advances every env, and one [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) returns the whole batch.

Per-env state lives on the **entities**, not the camera. After `build()`, any state setter accepts an `(N, ...)`-shaped argument and writes a different value into each env:

```python
ball.set_pos([
    [ 0.0,  1.2, 0.3],
    [ 1.2,  0.0, 0.3],
    [ 0.0, -1.2, 0.3],
    [-1.2,  0.0, 0.3],
])
```

That single call is what makes the four columns of the wide overview differ — the camera pose is constant, but the simulator has placed the ball somewhere else in every env. Anything you can set per env in Genesis (rigid pose, joint positions, particle state, …) shows up the same way in the next render.

## Different camera positions per environment

Per-env state is on entities, so to place a camera differently in every env you bind it to one. Add an invisible rigid entity to act as an attachment target, attach the camera to it via `entity_idx` / `offset_T`, and `set_pos` / `set_quat` it per env — the camera moves with it, exactly the way it would move with a Franka wrist link in {doc}`attached_camera`. `offset_T` is the camera's pose **in the rig's local frame**, so the same offset stays consistent relative to the rig no matter where the rig ends up; per-env *position* slides the camera around the world, per-env *orientation* rotates its viewing angle. In this example the rig is set to point outward from the centre of the plane in each env, so the follow row shows the same ball framed from four different radial angles, each against a different slice of the HDRI sky.

## Different lighting per environment

`env_maps` is the one piece of the camera config that the renderer **indexes by env** rather than merging scene-wide: env `i` is lit by `env_maps[i]`. Passing an `N`-long tuple to a single `NyxCameraOptions` is therefore enough to render every env under its own HDRI, with no extra calls or per-step bookkeeping. This example alternates two assets across four envs:

```python
env_maps = (env_map_sky, env_map_studio, env_map_sky, env_map_studio)
```

Even-indexed envs render under an outdoor sky, odd-indexed envs under a studio softbox. The choice flows through both cameras automatically because the renderer instance is shared, so the top-row wide overview and the bottom-row follow camera both see env 0 lit by `env_map_sky`, env 1 by `env_map_studio`, and so on. A few constraints worth knowing:

- The mapping is strictly positional. There is no per-env override API or "default" entry; the tuple must be at least `n_envs` long.
- The tuple is collected at build time across every Nyx sensor in the scene. Declare it on one sensor (as here) to keep the source of truth in a single place; declaring it on multiple cameras concatenates the lists and the indexing drifts.
- Each entry is a full {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset`, so per-env intensity (`multiplier`), rotation, and tint are all available — useful for domain-randomized lighting on top of a single base HDRI.

## Heterogeneous environments: not supported

The `(N, ...)`-shaped state setters above all assume every env contains the **same** geometry — only the state differs. Genesis itself has a stronger form of variation called *heterogeneous simulation*, where you pass a tuple of morph variants to `scene.add_entity` and the rigid solver hands each env a different variant:

```python
# Valid Genesis call. Will simulate correctly, but Nyx will NOT render it correctly.
scene.add_entity(morph=(
    gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=(0.0, 0.0, 0.1)),
    gs.morphs.Sphere(radius=0.03,           pos=(0.1, 0.0, 0.1)),
))
```

**The Nyx plugin does not currently support heterogeneous morphs.** The scene description the plugin builds at `scene.build()` time captures a single set of meshes shared across all envs, so even if the rigid solver is dispatching a different variant per env on the physics side, every env will render with the same geometry the plugin saw first. The mismatch is silent — no exception is raised, the image just doesn't match the simulation.

If you need different *models* per env, the options today are:

- **Spawn every variant in every env and toggle their state per env.** Add all candidate morphs as separate entities, then in each env push the inactive ones below the plane (or to a far-away corner) via `set_pos`. Geometry stays homogeneous from the plugin's perspective, so rendering is correct.
- **Build separate scenes.** Run one Genesis scene per variant and read each one independently. You lose the batched-step speed-up but keep both physics and rendering correct.

State-based variation works fine: positions, joint angles, velocities, masses through domain randomization, and per-env lighting (see [Different lighting per environment](#different-lighting-per-environment) above). The limitation only applies when you need a different mesh in each env.

## Reading the saved image

The PNG is a 2 × 4 grid. Top row: the wide overview, four times — same camera pose, four different ball positions, with the lighting alternating outdoor sky / studio softbox / outdoor sky / studio softbox across columns. Bottom row: the follow camera, four times — both the camera pose *and* the ball move per env, with the rig rotated outward from the centre so each cell shows the ball from a different radial angle, lit by the same HDRI as the wide cell directly above it. Comparing top and bottom of the same column tells you per-env state and per-env env maps are shared across cameras; comparing left to right of the same row tells you the per-env variation actually took effect.

## Source

```{literalinclude} ../../../../examples/07_multi_camera_multi_env.py
:language: python
:linenos:
```

Run it:

```bash
uv run python examples/07_multi_camera_multi_env.py
```

The PNG is written to `examples/out/07_multi_camera_multi_env.png`. The Sphinx build copies it to `_static/generated/examples/07_multi_camera_multi_env.png` and embeds it at the top of this page, so the docs site always shows whatever the latest run produced.

## See also

- {doc}`attached_camera` — Full walk-through of `entity_idx` / `offset_T` and Genesis' sensor-attachment lifecycle. The follow camera here is the same mechanism, just bound to an invisible rig instead of a robot link.
- {doc}`../advanced/sensor_lifecycle` — When the shared renderer is created (after the *last* {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` finishes building) and the implications for sensors added or read in unusual orders.
- {doc}`hello_nyx` — The single-camera, single-env baseline. Diff this example against it to see exactly which lines flip on multi-camera and multi-env behaviour.
