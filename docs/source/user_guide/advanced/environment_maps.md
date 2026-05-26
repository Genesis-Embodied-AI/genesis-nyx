# Environment maps

Environment maps provide image-based lighting (IBL) using an HDR image as both the visible background and the source of indirect illumination. They drive reflections, ambient colour, and global indirect light without requiring explicit light sources.

Environment maps are declared on a Nyx camera sensor via the {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.env_maps` field of {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions`. The plugin collects them from every Nyx sensor at `scene.build()` and writes the union into the shared scene description.

## Declaring an environment map

An environment map is built by constructing an {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset`, setting its texture and parameters, and passing it through {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.env_maps`:

```python
import math
import gs_nyx.nyx_py_sdk as nps

env_map            = nps.EnvironmentMapAsset()
env_map.texture    = "path/to/envmap.hdr"
env_map.layout     = nps.EEnvMapLayout.LongLat
env_map.rotation   = math.radians(30)
env_map.multiplier = 1.5

cam = scene.add_sensor(NyxCameraOptions(
    res=(1280, 720),
    pos=(2.0, -1.5, 2.0),
    lookat=(0.0, 0.0, 0.9),
    env_maps=(env_map,),
))
```

`env_maps` is a tuple. Multi-environment scenes use the tuple index to assign a different map to each Genesis env (see [Per-environment selection](#per-environment-selection)).

## Properties

| Property | Type | Description |
|---|---|---|
| `texture` | `str` | Path to an `.hdr` or `.exr` file. Leave unset for a solid-colour HDRI driven entirely by `tint`. |
| `layout` | {py:class}`~gs_nyx.nyx_py_sdk.EEnvMapLayout` | Image layout. `LongLat` is the standard equirectangular HDRI projection. |
| `rotation` | `float` | Yaw rotation around the up axis, in radians. |
| `multiplier` | `float` | Brightness multiplier applied to the HDRI values. |
| `tint` | {py:class}`~gs_nyx.nyx_py_sdk.float3` `(r, g, b)` | Colour tint multiplied into the HDRI. When `texture` is unset, this *is* the HDRI: a constant RGB radiance applied across the whole sphere. |

## Supported file formats

| Extension | Status |
|---|---|
| `.hdr` | Supported (Radiance RGBE) |
| `.exr` | Supported (OpenEXR) |

(solid-colour-hdri)=
## Solid-colour HDRI (default sky and how to override it)

A Nyx scene with no environment map declared is **not** rendered against a black background. The renderer falls back to a flat mid-grey HDRI sky (RGB ≈ `(0.5, 0.5, 0.5)`) so unlit surfaces still receive ambient illumination and untouched scenes look reasonable out of the box. That fallback is convenient, but it is itself a light source: it contributes diffuse ambient and reflections to every PBR surface in the scene.

To replace the default sky with a different constant colour, attach an {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset` with no `texture` and set `tint` to the colour you want. The renderer treats a texture-less asset as a uniform-radiance sky:

```python
import gs_nyx.nyx_py_sdk as nps

# Pitch-black sky: kills the default grey ambient entirely, leaving the
# scene lit purely by the explicit `lights` on the camera.
black_sky      = nps.EnvironmentMapAsset()
black_sky.tint = nps.float3(0.0, 0.0, 0.0)

cam = scene.add_sensor(NyxCameraOptions(
    ...,
    env_maps = (black_sky,),
))
```

Use this whenever you need a clean, controllable lighting setup, for example when isolating the contribution of a single light, comparing materials under identical illumination, or generating synthetic data where ambient light would confound the labels. `multiplier` still applies, so a warm overcast wash can be expressed as `tint = nps.float3(0.6, 0.55, 0.5)` with `multiplier` tuned to taste.

(per-environment-selection)=
## Per-environment selection

In a batched scene (`scene.build(n_envs=N)`), the env-map tuple is indexed by Genesis environment. Environment `i` renders with `env_maps[i]`.

```python
env_map_a = nps.EnvironmentMapAsset()
env_map_a.texture = "studio.hdr"
env_map_a.tint = nps.float3(0.6, 0.2, 0.1)

env_map_b = nps.EnvironmentMapAsset()
env_map_b.texture = "outdoor.exr"
env_map_b.tint = nps.float3(0.3, 0.8, 0.2)
env_map_b.multiplier = 0.8

cam = scene.add_sensor(NyxCameraOptions(
    ...,
    env_maps=(env_map_a, env_map_b),
))

scene.build(n_envs=2)
```

The plugin calls `set_env_map(env_index)` on the renderer inside the per-environment loop of the render pass (see {doc}`sensor_lifecycle`). This is the one piece of per-frame lighting state the plugin pushes, and it makes per-env HDRI domain randomisation cheap.

## Lifecycle and constraints

```{warning}
Environment maps are baked into the scene at `scene.build()`. The `texture`, `layout`, `rotation`, `multiplier`, and `tint` fields cannot be modified at runtime. To change the HDRI, rebuild the scene.
```

```{note}
A scene with no environment map and no explicit lights renders against Nyx's default mid-grey HDRI sky as its only light source. The plugin emits a warning at build time, since this is rarely what you want: every PBR surface picks up the same flat grey ambient and the frame looks washed out. Add at least one light (see {doc}`lights`), an HDRI environment map, or a [solid-colour HDRI](#solid-colour-hdri) with a chosen `tint` to take control of the illumination.
```

```{note}
Procedural sun and sky generation is not supported. Use a captured HDRI or pair an {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset` with a directional light.
```

## See also

- {doc}`lights` — Point / directional / spot light sources.
- {doc}`splats` — Gaussian splats.
- {doc}`sensor_lifecycle` — When environment maps are uploaded and switched per env.
