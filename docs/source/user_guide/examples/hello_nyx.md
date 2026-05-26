# Hello, Nyx

The smallest end-to-end Nyx scene: a gold PBR ball on a plane, lit entirely by an HDR environment map, rendered to a single PNG.

{{ example_01_hello_nyx_screenshot }}

## What it shows

- Initializing Genesis with `gs.init()`. The Nyx SDK is booted automatically: importing `NyxCameraOptions` registers its start / stop pair with Genesis, so no explicit `nps.startup()` / `nps.shutdown()` call is needed.
- Adding scene geometry with stock Genesis morphs (`Plane`, `Mesh`) and overriding the GLB's embedded material with `gs.surfaces.Gold()`.
- Configuring an HDR {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset` (long-lat layout, intensity multiplier) as the sole light source.
- Adding a Nyx camera sensor via {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` — resolution, pose, FOV, samples-per-pixel, and {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.FastPathTracer`.
- Building the scene, stepping the simulation once to trigger a render, then reading the frame back from the sensor with [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data)`.rgb`.

## Source

```{literalinclude} ../../../../examples/01_hello_nyx.py
:language: python
:linenos:
```

Run it:

```bash
uv run python examples/01_hello_nyx.py
```

The output PNG is written to `examples/out/01_hello_nyx.png`.
