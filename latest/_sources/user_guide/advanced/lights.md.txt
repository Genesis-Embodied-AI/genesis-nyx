# Lights

Lights are declared on a Nyx camera sensor via the `lights` field of {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions`. At `scene.build()`, the plugin collects the lights from every Nyx sensor in the scene, converts each one to a {py:class}`~gs_nyx.nyx_py_sdk.LightAsset` (kinds enumerated by {py:class}`~gs_nyx.nyx_py_sdk.ELightType`), and writes the union into the shared Nyx scene description.

This page describes the supported light types, their parameters, the coordinate convention, and the runtime constraints that apply once the scene is built.

## Declaring lights

A light is a Python dictionary with a required `type` key. The dictionary is passed to the `lights` field of {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` as a list:

```python
SPOT = {
    "type":      "spot",
    "pos":       (2.0, -2.0, 3.0),
    "dir":       (0.0, 0.707, -0.707),
    "color":     (0.8, 0.4, 0.4),
    "intensity": 50.0,
    "range":     10.0,
}

POINT = {
    "type":      "point",
    "pos":       (0.0, 1.0, 3.0),
    "color":     (0.4, 0.8, 0.4),
    "intensity": 50.0,
    "range":     10.0,
}

cam = scene.add_sensor(NyxCameraOptions(
    res=(512, 512),
    pos=(0, 0, 10),
    lookat=(0, 0, 0),
    lights=[SPOT, POINT],
))
```

Lights declared on different Nyx sensors in the same scene are merged. Two cameras cannot see different lighting setups; they share one scene.

## Supported light types

| Type | `type` value | Required | Optional |
|---|---|---|---|
| Point | `"point"` | `pos` | `range`, `color`, `intensity`, `shadow` |
| Directional | `"directional"` | `dir` | `color`, `intensity`, `shadow` |
| Spot | `"spot"` | `pos`, `dir` | `inner_angle`, `outer_angle`, `range`, `color`, `intensity`, `shadow` |

```{note}
Ambient light is not supported. Use an environment map for image-based lighting instead (see {doc}`environment_maps`).
```

```{note}
Area lights are not exposed by the plugin. The Nyx engine supports rectangle / sphere / tube / disc emitters internally (see {py:class}`~gs_nyx.nyx_py_sdk.EAreaShape`), but they are not surfaced through {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions`.
```

## Common properties

These keys are accepted by every light type.

| Key | Type | Default | Description |
|---|---|---|---|
| `color` | `(r, g, b)` | `(1, 1, 1)` | Linear RGB in `[0, 1]`. |
| `intensity` | `float` | `1.0` | Light intensity in the unit set by the light type (see [Units](#units)). |

## Type-specific properties

### Point light

A point light emits uniformly in every direction from a position.

| Key | Type | Default | Description |
|---|---|---|---|
| `pos` | `(x, y, z)` | `(0, 0, 5)` | World position in Genesis Z-up coordinates. |
| `range` | `float` | `100.0` | Effective falloff distance. |

### Directional light

A directional light emits along a direction vector. Position is irrelevant — the light is treated as infinitely far away.

| Key | Type | Default | Description |
|---|---|---|---|
| `dir` | `(x, y, z)` | `(0, 0, -1)` | Light direction in Genesis Z-up coordinates. |

### Spot light

A spot light emits from a position in a cone defined by two cutoff angles.

| Key | Type | Default | Description |
|---|---|---|---|
| `pos` | `(x, y, z)` | `(0, 0, 5)` | World position in Genesis Z-up coordinates. |
| `dir` | `(x, y, z)` | `(0, 0, -1)` | Cone axis in Genesis Z-up coordinates. |
| `inner_angle` | `float` (degrees) | `15.0` | Full intensity is delivered inside this half-angle. |
| `outer_angle` | `float` (degrees) | `30.0` | Falloff reaches zero at this half-angle. |
| `range` | `float` | `100.0` | Effective falloff distance. |

(units)=
## Units

Light intensity is expressed in **photometric** units — quantities weighted by the human eye's spectral response, in contrast with radiometric (energy-based) units. The plugin fixes one photometric unit per light type to match physical convention. The full Nyx unit enum ({py:class}`~gs_nyx.nyx_py_sdk.ELightUnit`: Candela / Nit / EV100) is not currently surfaced through {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions`.

### Plugin defaults

| Light type | `intensity` unit | Quantity |
|---|---|---|
| Point | Lumen (`lm`) | Luminous power |
| Spot | Lumen (`lm`) | Luminous power |
| Directional | Lux (`lx`) | Illuminance |

### Photometric reference

| Quantity | Photometric term | Unit |
|---|---|---|
| Power | Luminous power / luminous flux ($\Phi_v$) | Lumen (`lm`) |
| Power per solid angle | Luminous intensity ($I_v$) | Candela (`cd`) — equivalent to `lm/sr` |
| Power per area | Illuminance / luminous exitance ($E_v$, $M_v$) | Lux (`lx`) — equivalent to `lm/m²` |
| Power per area per solid angle | Luminance ($L_v$) | Nit (`nt`) — equivalent to `cd/m²` or `lm/(m²·sr)` |
| Energy | Luminous energy ($Q_v$) | Lumen-second (`lm·s`) |

### Conventions by light kind

| Light kind | Typical unit | Rationale |
|---|---|---|
| Punctual (point, spot) | Luminous power (`lm`) | A real bulb is rated by total light emitted in all directions. |
| Photometric (IES profile) | Luminous intensity (`cd`) | A photometric profile measures intensity per direction. |
| Sun / directional | Illuminance (`lx`) | A directional source has no finite total power; lux describes the light landing on a surface perpendicular to the rays. |
| Sky / image-based | Luminance (`cd/m²`) | Captured environment maps are calibrated per solid angle. |
| Area / emissive surface | Luminance (`cd/m²`) or EV | Matches how displays and emissive textures are specified. |

The last two rows are included for reference — the plugin does not currently surface area lights or photometric (IES) profiles, so luminance and per-direction candela values are not reachable through {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions`.

## Coordinate convention

All positions and directions are specified in Genesis Z-up world coordinates. The plugin converts them to Nyx Y-up at build time. No manual axis swap is required.

## Lifecycle and constraints

```{warning}
Lights are baked into the scene at `scene.build()` and cannot be modified at runtime. Mutating the `lights` field of {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` after build has no effect on rendered output. To change lighting, rebuild the scene.
```

```{note}
Genesis `VisOptions.lights` (`DirectionalLight`, `PointLight`, `AmbientLight`) is ignored by the Nyx plugin. Configure lights through {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` instead.
```

```{note}
If a scene contains no lights *and* no environment maps, the plugin emits a warning at build time and the scene is lit solely by Nyx's default mid-grey HDRI sky (RGB ≈ `(0.5, 0.5, 0.5)`). This is rarely what you want; add at least one light, an HDRI, or a {ref}`solid-colour HDRI <solid-colour-hdri>` with a chosen `tint` (use black to suppress the default sky entirely).
```

## See also

- {doc}`environment_maps` — Image-based lighting and HDRI assets.
- {doc}`splats` — Gaussian splats.
- {doc}`sensor_lifecycle` — When the scene description is baked and what triggers a re-render.
