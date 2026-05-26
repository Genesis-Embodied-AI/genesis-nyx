# Gaussian splat

A captured Gaussian splat composited into a live Genesis scene, lit by a single directional sun. The cactus is a `.ply` radiance field; the plane it sits on is a stock `gs.morphs.Plane`. Both are rendered in the same Nyx frame.

{{ example_05_gaussian_splat_screenshot }}

## What it shows

- Loading a 3D Gaussian Splatting `.ply` file as a {py:class}`~gs_nyx.nyx_py_sdk.LightFieldAsset` and attaching it to the camera through {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.light_fields`.
- Mixing the splat with **simulated geometry** (a Genesis `Plane`) lit by a single **directional light**. The plane is shaded by the sun; the cactus's appearance is whatever the splat baked in at capture time.

## How the splat is declared

A splat is a {py:class}`~gs_nyx.nyx_py_sdk.LightFieldAsset` with {py:class}`~gs_nyx.nyx_py_sdk.ELightFieldType` set to `GaussianField`. Set its `uri` to a `.ply` (Inria-style 3DGS) or `.spz` (compressed) file, then hand it to the camera:

```python
import gs_nyx.nyx_py_sdk as nps

cactus      = nps.LightFieldAsset()
cactus.type = nps.ELightFieldType.GaussianField
cactus.uri  = "examples/assets/cactus.ply"

cam = scene.add_sensor(NyxCameraOptions(
    ...,
    light_fields = [cactus],
))
```

A few things worth noting:

- **Splats are not Genesis entities.** They never enter the rigid / FEM / MPM solvers, never collide, and have no morph. They live entirely on the renderer side; the only Genesis-facing surface is the `light_fields` field of the camera options.
- **Light fields are scene-wide.** The plugin collects `light_fields` from every Nyx sensor at `scene.build()` and merges them into one shared scene description. Declaring the same splat on two cameras isn't required — and would duplicate it.
- **Format is auto-detected.** `.ply` for plain 3DGS output, `.spz` for the compressed variant. The extension decides which loader runs; there's no flag to set.
- **The splat has a transform.** `position`, `rotation` (quaternion), and per-axis `scale` are all on {py:class}`~gs_nyx.nyx_py_sdk.LightFieldAsset`. The defaults — origin, identity, unit scale — keep this example simple, but you can move or resize the cactus by setting them before `scene.build()`. See {doc}`../advanced/splats` for the full field list.

## Source

```{literalinclude} ../../../../examples/05_gaussian_splat.py
:language: python
:linenos:
```

Run it:

```bash
uv run python examples/05_gaussian_splat.py
```

The PNG is written to `examples/out/05_gaussian_splat.png`. The Sphinx build copies it to `_static/generated/examples/05_gaussian_splat.png` and embeds it at the top of this page, so the docs site always shows whatever the latest run produced.

## See also

- {doc}`../advanced/splats` — Full reference for {py:class}`~gs_nyx.nyx_py_sdk.LightFieldAsset`: supported formats, transform fields, tone-mapping guidance.
- {doc}`light_types` — Reference for the point / directional / spot light schema used here.
- {doc}`hello_nyx` — The simplest Nyx scene, useful as a contrast for what changes once a splat is involved.
