# Quickstart

This guide assumes you already have a working Genesis simulation and want to swap its camera for a Nyx-rendered one. If you need a complete runnable script, see [`examples/01_hello_nyx.py`](https://github.com/Genesis-Embodied-AI/nyx-for-genesis/blob/main/examples/01_hello_nyx.py).

Install the plugin first, see {doc}`installation`.

## 1. Imports

```python
import gs_nyx.nyx_py_renderer as npr
import gs_nyx.nyx_py_sdk as nps
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions
```

## 2. Initialize Genesis

Importing `NyxCameraOptions` registers the Nyx SDK's start / stop pair with Genesis, so `gs.init()` boots the renderer for you and `gs.destroy()` (or interpreter teardown) tears it down.

```python
gs.init()

scene = gs.Scene(show_viewer=False)
```

## 3. Replace your camera with a Nyx sensor

Where you previously called `scene.add_camera(...)`, call `scene.add_sensor(NyxCameraOptions(...))` instead. All the intrinsics live on the options object — see {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` for the full field list and {py:class}`~gs_nyx.nyx_py_renderer.ERenderMode` for the available render modes.

```python
cam = scene.add_sensor(NyxCameraOptions(
    res         = (1280, 720),
    pos         = (-1.0, 1.0, 1.2),
    lookat      = (0.0, 0.0, 0.1),
    fov         = 40.0,
    spp         = 32,
    render_mode = npr.ERenderMode.FastPathTracer,
))
```

To mount the camera on a robot link instead of a static pose, drop `pos`/`lookat` and pass `entity_idx` / `link_idx_local` / `offset_T`, see {doc}`examples/attached_camera`.

## 4. Add a light

Path-traced renders need a light source. A single directional ("sun") {py:class}`~gs_nyx.nyx_py_sdk.LightAsset` is the simplest (see {py:class}`~gs_nyx.nyx_py_sdk.ELightType` for the full set of light types):

```python
sun                       = nps.LightAsset()
sun.type                  = nps.ELightType.Directional
sun.directional_direction = (-0.4, -0.4, -0.8)
sun.color                 = (1.0, 1.0, 1.0)
sun.intensity             = 5.0

cam = scene.add_sensor(NyxCameraOptions(
    # ...intrinsics as above...
    lights = (sun,),
))
```

## 5. Render and read frames

A frame is produced every [`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step). Pull the latest RGB buffer with [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data)`.rgb`, shape `(n_envs, H, W, 3)` `uint8`:

```python
scene.build(n_envs=1)
scene.step()

rgb = cam.read().rgb[0].cpu().numpy()  # (H, W, 3) uint8
```

For video, hand `cam.read().rgb[0]` to [`scene.start_recording(...)`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.start_recording), see [`examples/02_attached_camera.py`](https://github.com/Genesis-Embodied-AI/nyx-for-genesis/blob/main/examples/02_attached_camera.py).

## Where to go next

- {doc}`index`, the user-guide landing page lists the runnable example scripts (camera attachment, lighting, materials, Genesis integration).
- {doc}`concepts`, the mental model behind scenes, assets, and renderer lifecycle.
- {doc}`../api_reference/index`, exhaustive API reference.
