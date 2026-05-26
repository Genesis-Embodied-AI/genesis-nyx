# Gaussian splats

The Nyx plugin renders captured light fields alongside simulated geometry. One field type is supported:

- **Gaussian splats** — a point-cloud-like representation where each point is a 3D Gaussian with view-dependent colour. Loaded from a `.ply` or `.spz` file.

Both are declared on a Nyx camera sensor via the {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.light_fields` field of {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` and modelled as {py:class}`~gs_nyx.nyx_py_sdk.LightFieldAsset` instances. They render as part of the scene every frame, alongside simulated rigid and deformable geometry.

## Declaring a light field

A light field is built by constructing a {py:class}`~gs_nyx.nyx_py_sdk.LightFieldAsset`, setting its type ({py:class}`~gs_nyx.nyx_py_sdk.ELightFieldType`) and URI, and passing it through {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.light_fields`:

```python
import gs_nyx.nyx_py_sdk as nps
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions

splat            = nps.LightFieldAsset()
splat.type       = nps.ELightFieldType.GaussianField
splat.uri        = "assets/bonsai.ply"

cam = scene.add_sensor(NyxCameraOptions(
    res=(256, 256),
    pos=(0, 0, 5),
    light_fields=[splat],
    tone_mapper=nps.EToneMapper.Off,
))
```

`light_fields` from every Nyx sensor in the scene are collected at `scene.build()` and merged into the shared scene description.

## Supported field types

| {py:class}`~gs_nyx.nyx_py_sdk.ELightFieldType` | File formats | Description |
|---|---|---|
| `GaussianField` | `.ply`, `.spz` | 3D Gaussian splats with view-dependent colour stored per Gaussian. |

### Gaussian splat formats

| Extension | Description |
|---|---|
| `.ply` | Standard 3D Gaussian Splatting output (Inria / INRIA-style). Plain-text PLY header with per-Gaussian position, scale, rotation, opacity, and spherical-harmonic coefficients. |
| `.spz` | Compact compressed Gaussian-splat format. Quantises and compresses the same per-Gaussian fields for faster loading and a much smaller on-disk footprint. |

The format is auto-detected from the URI extension. No flag is required to switch between them.

## Common properties

| Property | Type | Description |
|---|---|---|
| `type` | {py:class}`~gs_nyx.nyx_py_sdk.ELightFieldType` | `GaussianField`. |
| `uri` | `str` | Path to the asset file. |

## Tone mapping for Gaussian splats

Gaussian splats are typically authored against a specific exposure and tone curve. To match the original capture, disable the renderer's tone mapper:

```python
NyxCameraOptions(
    ...,
    tone_mapper=nps.EToneMapper.Off,
    light_fields=[splat],
)
```

## Lifecycle and constraints

```{warning}
Light fields are loaded once at `scene.build()` from the URIs declared at that point. Replacing the asset or changing its placement at runtime is not supported. To change the field, rebuild the scene.
```

```{note}
Light fields render alongside simulated geometry. A scene can mix simulated rigid bodies, deformable solvers, and a Gaussian-splat capture in the same frame.
```

## See also

- {doc}`lights` — Direct light sources.
- {doc}`environment_maps` — HDRI-based environment lighting.
