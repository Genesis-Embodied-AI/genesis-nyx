# Camera profiles

A camera profile describes the physical camera a Nyx sensor emulates: its lens (focal length, aperture, distortion, chromatic aberration, vignetting), its sensor (size, exposure, noise) and its colour management (tone mapper, optional LUT). Profiles are {py:class}`~gs_nyx.nyx_py_sdk.CameraProfileAsset` objects stored as JSON files and referenced by a camera through {py:attr}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions.camera_profile`.

## Default behaviour

When `camera_profile` is left at `None`, the plugin writes a default profile for every Nyx camera into the scene's `__nyx_cache__/<id>/` folder at `scene.build()`. That profile is derived from the camera's `fov` and uses Reinhard tone mapping, which reproduces the behaviour of earlier releases.

## Using a profile file

Point `camera_profile` at a JSON profile. The field of view then comes from the profile's optics, so `fov` is ignored (a warning is printed if both are set):

```python
import os
import gs_nyx
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions

# A profile shipped with the wheel: Sony A7R V body, 24 mm lens, ACES tone mapping.
SONY_A7R5 = os.path.join(
    os.path.dirname(gs_nyx.__file__), "assets", "camera_profiles", "sony_a7_r5_24mm.json"
)

cam = scene.add_sensor(NyxCameraOptions(
    res            = (1920, 1080),
    pos            = (-1.0, 1.0, 1.2),
    lookat         = (0.0, 0.0, 0.1),
    camera_profile = SONY_A7R5,
))
```

Relative paths are resolved against the working directory of the Genesis process; prefer absolute paths.

## Building a profile in Python

{py:class}`~gs_nyx.nyx_py_sdk.CameraProfileAsset` exposes every field; {py:func}`~gs_nyx.nyx_py_sdk.export_camera_profile_file` and {py:func}`~gs_nyx.nyx_py_sdk.import_camera_profile_file` round-trip it to JSON. This is the simplest way to change one knob, such as the tone mapper, while keeping the default optics:

```python
import math
import gs_nyx.nyx_py_sdk as nps

profile = nps.CameraProfileAsset()
profile.set_fov_y(math.radians(40.0))                    # vertical field of view
profile.colorManagement.toneMapper = nps.EToneMapper.Off # linear output
profile.lens.vignette.strength     = 0.0

nps.export_camera_profile_file("my_profile.json", profile)

cam = scene.add_sensor(NyxCameraOptions(..., camera_profile="my_profile.json"))
```

### Fields

| Group | Field | Meaning |
|---|---|---|
| `lens.optical` | `focalLength` | Focal length of the lens, in millimetres. Together with `sensor.sensorHeight` it defines the vertical field of view ({py:meth}`~gs_nyx.nyx_py_sdk.CameraProfileAsset.fov_y` / {py:meth}`~gs_nyx.nyx_py_sdk.CameraProfileAsset.set_fov_y`). |
| `lens.distortion` | `k1`, `k2`, `k3` | Radial distortion polynomial coefficients. |
| `lens.chromaticAberration` | `lateralRScale`, `lateralBScale` | Lateral chromatic aberration of the red and blue channels. |
| `lens.vignette` | `strength`, `k1`, `k2`, `tint` | Achromatic barrel occlusion (radial polynomial) and its colour tint. |
| `lens.aperture` | `apertureFStops` | Aperture in f-stops. |
| `sensor` | `sensorHeight`, `sensorResolutionY` | Physical sensor height in millimetres and its vertical resolution. |
| `sensor.exposure` | `iso`, `minISO`, `maxISO`, `shutterSpeed`, `exposureCompensation` | Shot sensitivity (ISO, `0` disables the noise simulation), body limits, integration time in seconds, and a stop offset on top of the physical exposure. |
| `sensor.noise` | `baseISO`, `strength` | Lowest native sensitivity anchoring the noise model, and an artistic scale on its amplitude. |
| `colorManagement` | `toneMapper`, `lutURI` | Tone mapping operator ({py:class}`~gs_nyx.nyx_py_sdk.EToneMapper`) and the LUT file used by `EToneMapper.LUT`. |

### Tone mappers

| {py:class}`~gs_nyx.nyx_py_sdk.EToneMapper` | Output |
|---|---|
| `Off` | No tone mapping; linear HDR values. Use it for Gaussian splats authored against their own tone curve (see {doc}`splats`). |
| `Reinhard` | Reinhard operator. The plugin's default. |
| `Neutral` | Frostbite neutral operator. |
| `ACES_1_3` | ACES 1.3 operator. |
| `LUT` | Look-up table from `lutURI` for tone mapping and grading. |

## JSON layout

The shipped `sony_a7_r5_24mm.json` shows the file format:

```json
{
    "version": 1,
    "description": "Sony A7 R5 24mm",
    "lens": {
        "focal_length": 24.0,
        "chromatic_aberration": { "lateral_r_scale": 0.004, "lateral_b_scale": -0.004 },
        "distortion": { "k1": -0.187357, "k2": 0.055437, "k3": -0.010774 },
        "vignette": { "strength": 1.0, "k1": -0.174, "k2": 0.189, "tint": [1.3, 1.0, 0.9] }
    },
    "sensor": { "height": 23.8, "resolution_y": 6336 },
    "color_management": { "tone_mapper": "aces_1_3" }
}
```

Keys that are omitted keep their defaults. To discover the exact spelling of a field, build the profile in Python and export it rather than writing the JSON by hand.

## Lifecycle and constraints

```{warning}
Profiles are read at `scene.build()`. Editing the JSON or the `camera_profile` field afterwards has no effect until the scene is rebuilt.
```

```{note}
`camera_profile` replaces the `tone_mapper` option of earlier plugin releases. Tone mapping is now a property of the profile, not of {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions`.
```

## See also

- {doc}`splats`: why Gaussian splats usually want tone mapping off.
- {doc}`../supported_features`: which camera properties the plugin honours.
