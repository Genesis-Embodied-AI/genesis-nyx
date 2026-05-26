# Examples

Runnable scripts that demonstrate the Nyx renderer plugin. Each script is self-contained, it builds a minimal scene, renders one or a few frames, and exits.

These scripts are the canonical source for the example pages under the [user guide](https://genesis-embodied-ai.github.io/nyx-for-genesis/latest/user_guide/examples/), those pages embed the scripts via Sphinx's `literalinclude`, so what you read on the docs site is what you can run here.

## Running

```bash
pip install gs-nyx-plugin
python examples/01_hello_nyx.py
```

## Scripts

| Script | Topic |
|---|---|
| [`01_hello_nyx.py`](01_hello_nyx.py) | Smallest possible scene, render a single frame |
| [`02_attached_camera.py`](02_attached_camera.py) | Mounting a Nyx camera on a robot link and recording an MP4 |
| [`03_materials.py`](03_materials.py) | A row of spheres showing common `gs.surfaces` variants under IBL + a key light |
| [`04_light_types.py`](04_light_types.py) | Side-by-side render of point, directional, and spot lights |
| [`05_gaussian_splat.py`](05_gaussian_splat.py) | Rendering a captured Gaussian splat alongside simulated geometry via `NyxCameraOptions.light_fields` |
| [`06_object_picking.py`](06_object_picking.py) | Casting rays through pixels with `NyxCameraSensor.pick_pixel` to identify hit entities and world positions |
| [`07_multi_camera_multi_env.py`](07_multi_camera_multi_env.py) | Two cameras across four parallel envs, returning a batched `(N_ENVS, H, W, 3)` tensor per `read()` |
