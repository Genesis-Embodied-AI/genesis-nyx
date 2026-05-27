---
sd_hide_title: true
---

# Nyx for Genesis

::::{grid} 1
:gutter: 2

:::{grid-item}
:class: sd-text-center

# Nyx for Genesis

**A high-performance renderer plugin for the [Genesis World](https://genesis-world.readthedocs.io/) simulator.**

```{image} /_static/images/landing.png
:alt: Path-traced render of dual robot arms over a fruit on a tabletop
:width: 100%
:class: sd-mb-3
```

Nyx drops in where a Genesis `Camera` would go and produces photoreal, path-traced frames from the same scene state. It renders robots, articulated assets, terrain, cloth, HDRI lighting, and Gaussian-splat light fields, all GPU-resident and ready to feed straight back into a training loop.
:::
::::

::::{grid} 1 1 2 2
:gutter: 3
:margin: 4 4 0 0

:::{grid-item-card} {octicon}`book;1.5em;sd-mr-1` User guide
:link: user_guide/index
:link-type: doc

Install the plugin, set up your first scene, drive the renderer from Python, and integrate with a Genesis simulation. Includes runnable examples for attached cameras, materials, lighting, Gaussian splats, picking, and multi-env rendering.
:::

:::{grid-item-card} {octicon}`code;1.5em;sd-mr-1` API reference
:link: api_reference/index
:link-type: doc

Auto-generated reference for every public class, function, and enum in the `gs_nyx` package, with cross-links into the Genesis API and worked examples for the symbols you'll touch most.
:::

::::

## Highlights

::::{grid} 1 2 2 4
:gutter: 3
:margin: 2 2 0 0

:::{grid-item-card} {octicon}`light-bulb;1.2em;sd-mr-1` Path-traced PBR
:link: user_guide/supported_features
:link-type: doc
:class-card: sd-text-center

Forward, fast, and reference path-tracing modes share one scene description. Disney-style materials, named metals, HDR environments.
:::

:::{grid-item-card} {octicon}`device-camera;1.2em;sd-mr-1` Robot-attached cameras
:link: user_guide/examples/attached_camera
:link-type: doc
:class-card: sd-text-center

Mount sensors on any entity/link with an offset transform. Pose updates flow through automatically each `scene.step()`.
:::

:::{grid-item-card} {octicon}`stack;1.2em;sd-mr-1` Multi-env friendly
:link: user_guide/examples/multi_camera_multi_env
:link-type: doc
:class-card: sd-text-center

Render `n_envs > 1` rollouts with per-environment HDRI swaps for cheap domain randomization. RGB stays on the GPU as `(B, H, W, 3) uint8`.
:::

:::{grid-item-card} {octicon}`globe;1.2em;sd-mr-1` Gaussian-splat scenes
:link: user_guide/examples/gaussian_splat
:link-type: doc
:class-card: sd-text-center

Drop captured-real environments straight into a simulated scene as a light field for photoreal backgrounds in synthetic data.
:::

::::

## Get started in a minute

Install the wheel from PyPI (see {doc}`user_guide/installation` for the full requirements):

```bash
pip install gs-nyx-plugin
```

Then swap your Genesis camera for a Nyx sensor:

```python
import genesis as gs
import gs_nyx.nyx_py_renderer as npr
import gs_nyx.nyx_py_sdk as nps
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions

gs.init()

scene = gs.Scene(show_viewer=False)
cam = scene.add_sensor(NyxCameraOptions(
    res         = (1280, 720),
    pos         = (-1.0, 1.0, 1.2),
    lookat      = (0.0, 0.0, 0.1),
    spp         = 32,
    render_mode = npr.ERenderMode.FastPathTracer,
))

scene.build(n_envs=1)
scene.step()
rgb = cam.read().rgb[0].cpu().numpy()  # (H, W, 3) uint8
```

Walk through the full version in {doc}`user_guide/quickstart`, or jump to {doc}`user_guide/examples/hello_nyx` for a complete runnable scene.

## Find your way around

- {doc}`user_guide/installation`: wheel requirements, CUDA driver, version pinning.
- {doc}`user_guide/quickstart`: render your first frame from an existing Genesis scene.
- {doc}`user_guide/concepts`: the renderer lifecycle, scenes, and assets.
- {doc}`user_guide/supported_features`: what the plugin renders, what it doesn't, and where the rough edges are.
- {doc}`user_guide/advanced/sensor_lifecycle`: operational details on the render-on-read model, multi-camera constraints, and the lighting model.
- {doc}`api_reference/index`: the full `gs_nyx` and `gs_nyx_plugin` API.

```{toctree}
:hidden:
:maxdepth: 2

user_guide/index
api_reference/index
```
