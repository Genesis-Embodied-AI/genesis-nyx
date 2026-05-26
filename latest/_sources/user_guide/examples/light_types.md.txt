# Light types

A side-by-side tour of the three light types the plugin exposes through the `lights` field of {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions` (kinds enumerated by {py:class}`~gs_nyx.nyx_py_sdk.ELightType`): **point**, **directional**, and **spot**. The same trio of PBR balls is rendered under all three at once, each light coloured and placed to make its contribution unmistakable.

{{ example_04_light_types_screenshot }}

## What it shows

Three balls sit on a plane, spaced wide enough that each light's falloff doesn't bleed into its neighbour. By default Nyx fills the sky with a flat grey HDRI, which would muddy the demonstration; this example switches it off (see [Disabling the default grey sky](#disabling-the-default-grey-sky) below) so every photon reaching a surface comes from one of the three lights declared on the camera.

- A **point** light hovers just above the left ball. Saturated red, short range, isotropic falloff, the classic "bare bulb". The hotspot is brightest right under the light and dies off into the plane around it.
- A **directional** light, dim and green, tilts in from above. Reaches every ball equally and casts long parallel shadows. Think "sun" — at this intensity it's faint enough that the point and spot easily dominate on their own balls, but it tints the middle ball (which has no other light on it) clearly green.
- A **spot** light is mounted high and to the right, aimed down-and-in at the right ball. A cool blue cone with a narrow inner angle and a soft outer falloff produces a crisp puddle of light on the plane.

Reading the rendered frame:

| Ball | Dominant light | What to look for |
|---|---|---|
| Left | Point (red) | Bright top hemisphere going red, falloff visible on the plane around it. |
| Middle | Directional (green) | The only ball with no punctual light on it — green wash from above and a long shadow trailing back. |
| Right | Spot (blue) | Cool tint, sharp cone edge on the plane, soft falloff at the outer angle. |

## How the lights are declared

Each light is a plain dict with a `type` key plus the parameters specific to that type. The list is handed to the `lights` field of {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions`:

```python
POINT_LIGHT = {
    "type":      "point",
    "pos":       (-0.93, 0.0, 0.5),
    "color":     (1.0, 0.15, 0.05),
    "intensity": 4.0,
    "range":     0.8,
}

DIRECTIONAL_LIGHT = {
    "type":      "directional",
    "dir":       (0.0, 0.3, -0.95),
    "color":     (0.25, 1.0, 0.35),
    "intensity": 2.0,
}

SPOT_LIGHT = {
    "type":        "spot",
    "pos":         (0.93, -0.6, 1.0),
    "dir":         (0.0, 0.5, -0.85),
    "color":       (0.15, 0.4, 1.0),
    "intensity":   15.0,
    "inner_angle": 10.0,
    "outer_angle": 20.0,
    "range":       3.0,
}

cam = scene.add_sensor(NyxCameraOptions(
    ...,
    lights = [POINT_LIGHT, DIRECTIONAL_LIGHT, SPOT_LIGHT],
))
```

A few things worth noting from the dict shapes:

- `pos` and `dir` are in Genesis Z-up world coordinates. The plugin handles the conversion to Nyx Y-up at build time.
- `intensity` is a relative brightness multiplier. The [lights reference](../advanced/lights.md) describes the photometric units each type *nominally* uses (lumens for `point`/`spot`, lux for `directional`), but in practice the renderer's exposure is calibrated such that values in the single digits to low tens give a well-exposed frame. Treat the units table as documenting the *quantity*, not the absolute scale, and tune by eye.
- The spot pulls the highest intensity here because its energy is concentrated into a narrow cone; a point at the same number would over-power the scene.
- `inner_angle` and `outer_angle` on the spot are half-angles in degrees. Inside the inner cone the light is at full intensity; between inner and outer it falls off smoothly to zero.
- `range` on the point and spot bounds the falloff distance. The directional light has no `range`, it's modelled as infinitely far away.

For the complete parameter list and units table, see {doc}`../advanced/lights`.

(disabling-the-default-grey-sky)=
## Disabling the default grey sky

A Nyx scene with no environment map is *not* black: the renderer falls back to a flat mid-grey HDRI sky so unlit shaders still produce something visible. That fallback would wash out the colour separation this example is trying to demonstrate, so it has to be turned off explicitly.

The trick is to attach a colour-only environment map. An {py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset` with no `texture` is treated as a solid-colour HDRI whose value is `tint`; setting `tint` to black gives an HDRI sky that radiates zero light:

```python
import gs_nyx.nyx_py_sdk as nps

black_sky      = nps.EnvironmentMapAsset()
black_sky.tint = nps.float3(0.0, 0.0, 0.0)   # solid-colour HDRI, no texture

cam = scene.add_sensor(NyxCameraOptions(
    ...,
    lights   = [POINT_LIGHT, DIRECTIONAL_LIGHT, SPOT_LIGHT],
    env_maps = (black_sky,),
))
```

The same pattern works for any constant background. A warm overcast wash, for example, is `tint = nps.float3(0.6, 0.55, 0.5)` with `multiplier` tuned to taste. See {doc}`../advanced/environment_maps` for the full `EnvironmentMapAsset` reference.

## Source

```{literalinclude} ../../../../examples/04_light_types.py
:language: python
:linenos:
```

Run it:

```bash
uv run python examples/04_light_types.py
```

The PNG is written to `examples/out/04_light_types.png`. The Sphinx build copies it to `_static/generated/examples/04_light_types.png` and embeds it at the top of this page, so the docs site always shows whatever the latest run produced.

## See also

- {doc}`../advanced/lights` — Full reference for the light dict schema, photometric units, and lifecycle constraints.
- {doc}`../advanced/environment_maps` — Image-based lighting, which can be combined with the lights above.
- {doc}`materials` — A side-by-side render of the common `gs.surfaces` variants under the same lighting.
