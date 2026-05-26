# Attaching a camera

A worked tour of the **Genesis ↔ Nyx integration surface**. The script mounts a Nyx camera on a Franka panda's wrist, records the wrist view as an MP4 while the robot performs a short pick, and never once touches plugin-internal code, every interaction goes through stock Genesis APIs.

{{ example_02_attached_camera_video }}

## The integration in one sentence

Nyx ships its renderer as a standard Genesis *sensor*. {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` derives from `genesis.options.sensors.camera.BaseCameraOptions`, {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` derives from `genesis.engine.sensors.camera.BaseCameraSensor`. Everything else, attachment, lifecycle, recording, follows from that.

## Where the plugin meets Genesis

Five hand-offs happen in this example. They are the entire integration contract; nothing in user code is plugin-private.

### 1. Sensor registration — `scene.add_sensor`

```python
cam = scene.add_sensor(NyxCameraOptions(
    res            = (1280, 720),
    fov            = 60.0,
    near           = 0.02,
    far            = 50.0,
    entity_idx     = franka.idx,
    link_idx_local = franka.get_link("hand").idx_local,
    offset_T       = WRIST_OFFSET_T,
    spp            = 32,
    render_mode    = npr.ERenderMode.FastPathTracer,
    env_maps       = (env_map,),
))
```

[`scene.add_sensor`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.add_sensor) is Genesis' built-in sensor factory. It uses the type of the options object to pick a sensor class, {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` resolves to {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` via the typed generic in its base class. The sensor is then held by Genesis' `SensorManager` and gets the same lifecycle (`build`, `step`, `read`) as a contact sensor, an IMU, or any other built-in.

### 2. Link attachment — Genesis-owned, not Nyx

`entity_idx`, `link_idx_local`, and `offset_T` are inherited from the `KinematicSensorOptionsMixin` Genesis ships. When you set them, Genesis' `SensorManager` calls `move_to_attach()` on the sensor every time the scene steps. `move_to_attach()` reads the link's world transform from the rigid solver, composes it with `offset_T`, and feeds the result back into the Nyx renderer as the camera pose. The plugin only implements the small `_apply_camera_transform` callback that Genesis invokes with the final 4×4 matrix.

Net effect: the wrist camera tracks the gripper for free. There is no `cam.update_pose()` loop in the example, and there couldn't be, the per-step camera transform is owned by the Genesis side.

### 3. SDK lifecycle — `gs.register_external_module`

```python
# excerpt from gs_nyx_plugin/nyx_camera_options.py
gs.register_external_module(nps.startup, nps.shutdown)
```

The plugin registers its SDK start / stop pair with Genesis at *import* time. `gs.init()` then walks its registry and calls every registered startup; `gs.destroy()` (or interpreter teardown) does the symmetric shutdown.

This is also why mocking `genesis` for docs builds works, the plugin doesn't have a hard dependency on a running Nyx SDK to be *importable*, only to be *used*.

### 4. Reading triggers rendering — `cam.read()`

```python
scene.start_recording(
    data_func   = lambda: cam.read().rgb,
    rec_options = gs.recorders.VideoFile(filename=OUTPUT_PATH, fps=FPS),
)
```

[`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) is the Genesis sensor read API. For {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` the read is *lazy*: it asks Genesis' base machinery "am I stale for the current sim step?", and only if the answer is yes calls `_render_current_state()`. That method does the actual Genesis ↔ Nyx glue:

1. `scene.visualizer.update_visual_states()` (Genesis) syncs visual transforms from the solvers.
2. `move_to_attach()` (Genesis, on each attached sensor) refreshes the camera pose from the link.
3. The Nyx renderer's `update_scene` / `render` are then called with the up-to-date state.
4. The frame is wrapped in a {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraData` named-tuple. Because the scene was built without `n_envs`, [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data)`.rgb` is a `(H, W, 3)` `uint8` CUDA tensor; with [`scene.build(n_envs=N)`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.build) the same field comes out as `(N, H, W, 3)` and you'd index `[0]`, that's the single change between this script and `01_hello_nyx.py`.

User code never calls a render function explicitly. One [`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) followed by one [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) is the whole loop.

### 5. Recording — stock Genesis pipeline

[`scene.start_recording`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.start_recording) and `gs.recorders.VideoFile` are both Genesis, not Nyx. The Genesis `RecorderManager` invokes `data_func` after each step, hands the returned `(H, W, 3)` `uint8` array to the `VideoFile` writer, and the writer pipes frames through PyAV to an H.264 MP4. The Nyx camera is just a data source, swap it for a Genesis rasterizer camera and the same recorder code works unchanged.

## Why the timing lines up

`dt = 1 / FPS` ties simulation time to video time: one [`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step) produces exactly one frame of the recording, so the MP4 plays back at the same speed the robot moved. If you raise `FPS`, drop `dt` correspondingly; the recorder doesn't care about real wall-clock time, only step counts.

## Source

```{literalinclude} ../../../../examples/02_attached_camera.py
:language: python
:linenos:
```

Run it:

```bash
uv run python examples/02_attached_camera.py
```

The MP4 is written to `examples/out/02_attached_camera.mp4`. The Sphinx build copies that file into `_static/generated/examples/02_attached_camera.mp4` and embeds it at the top of this page, so the video on the docs site stays in lock-step with whatever the latest run produced.
