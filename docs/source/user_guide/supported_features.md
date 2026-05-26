# Supported features

A quick map of what the Nyx plugin renders and what it doesn't. Use this page to decide whether your Genesis scene will work as-is, need a small tweak, or hit a hard limit.

Legend: ✅ supported · ⚠️ partial / has caveats · ❌ not supported

## Solvers

The plugin reads geometry from four Genesis solvers. Anything else is invisible to Nyx.

| Solver | Status | Notes |
|---|---|---|
| Rigid | ✅ | Drives rigid bodies, URDFs, MJCFs, drones, primitives, terrain. |
| FEM | ✅ | Live vertices, fixed topology (no remeshing). |
| PBD | ✅ | Same path as FEM. Only PBD entities backed by a mesh or primitive morph render — particle-only PBD is filtered out. |
| MPM | ⚠️ | Solids render through a skinned mesh; fluids (liquid/sand/snow) via per-frame marching-cubes reconstruction. `vis_mode="particle"` is unsupported and raises at build with an actionable message. |
| SPH | ❌ | Particle fluids — no surface to render. |
| SF (smoke) | ❌ | Eulerian grid not consumed. |
| Tool, Avatar | ❌ | Not consumed. |

```{note}
Genesis's MPM tutorial defaults to `vis_mode="particle"`. Switch it to `"visual"` (solids) or `"recon"` (fluids) when porting that tutorial to Nyx.
```

## Entities and morphs

| Morph | Status | Notes |
|---|---|---|
| `Box`, `Sphere`, `Cylinder`, `Plane` | ✅ | Native Nyx primitives — no mesh triangulation. |
| `Mesh` (`.obj`, `.stl`, `.glb`, `.gltf`) | ✅ | `.glb`/`.gltf` keep their embedded materials. |
| `Mesh` (`.dae` / `.usd*`) | ❌ | Passed through, but Nyx has no Collada or USD importer — load will fail. |
| `URDF` | ✅ | Picking works at link-name granularity. |
| `MJCF` | ✅ | Visual geometry is transcoded to OBJ at export time. |
| `Drone` | ✅ | Renders fine; propeller spin shows up only if the rigid solver writes the propeller transforms. |
| `Terrain` | ✅ | Procedural OBJ export per build. |
| Capsule / ellipsoid (URDF/MJCF visual geom) | ⚠️ | Falls back to a triangulated mesh instead of Nyx's native capsule primitive. Renders correctly, just less efficient. |
| `Nowhere` (emitters) | ❌ | No particle visualization. |

For texture files, `.png`, `.jpg`, `.bmp`, `.tga`, `.hdr`, and `.exr` are all supported. `.webp` and `.tiff` will fail to load on the Nyx side.

## Surfaces and materials

The plugin maps `genesis.surfaces.*` to a single Disney-style PBR slot.

| Surface | Status | Notes |
|---|---|---|
| `Plastic`, `Rough`, `Smooth`, `Default`, `BSDF` | ✅ | Generic PBR. |
| `Metal` (incl. `Gold`, `Copper`, `Iron`, …) | ✅ | 8 named metals via a color lookup; no spectral complex IOR. |
| `Emission` | ⚠️ | Emission is set, but the surface's base albedo is forced to black and metalness to 1.0 — emissive geometry reads as self-lit only. |
| `Glass`, `Water` | ⚠️ | Renders, but transmission, IOR, thickness, subsurface and transparency are dropped. Looks closer to plastic than to glass. |
| `Collision` | ✅ | Treated as plastic. |

### PBR properties

| Property | Status |
|---|---|
| `color` (RGBA) | ✅ |
| `opacity` | ⚠️ folded into albedo alpha; not flipped to a true transparent material |
| `roughness`, `metallic`, `emissive` | ✅ |
| `double_sided` | ✅ |
| `ior` | ❌ |
| `smooth` flag | ❌ |

### Textures

| Slot | Status |
|---|---|
| `diffuse_texture` | ✅ |
| `normal_texture` | ✅ |
| `emissive_texture` | ✅ |
| `roughness` / `metallic` / `specular` / `opacity` / `transmission` / `thickness` textures | ❌ — only the scalar values |
| `ColorTexture` (single-color "texture") | ⚠️ |
| `BatchTexture` | ❌ |

## Lighting and environment

```{important}
Lighting is configured through {py:class}`~gs_nyx_plugin.nyx_camera_options.NyxCameraOptions`, **not** Genesis `VisOptions`. Any lights you set on `gs.options.VisOptions(lights=...)` are ignored by Nyx — see {doc}`advanced/lights`.
```

| Feature | Status |
|---|---|
| Point light | ✅ |
| Directional light | ✅ |
| Spot light | ✅ |
| Ambient light | ❌ |
| Shadow toggle | ✅ |
| HDRI environment map | ✅ via `NyxCameraOptions.env_maps`; per-env switching supported for domain randomization |
| Light fields (gaussian splats) | ✅ |
| Area lights (rectangle / sphere / disc / tube) | ❌ |

## Cameras

| Property | Status |
|---|---|
| Pinhole model | ✅ |
| Thin-lens / fisheye / orthographic | ❌ |
| `res`, `pos`, `lookat`, `up`, `fov`, `near`, `far` | ✅ |
| `spp`, `denoise`, `tone_mapper`, `anti_aliasing` | ✅ |
| Render mode ({py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.Forward` / {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.FastPathTracer` / {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.RefPathTracer` / {py:attr}`~gs_nyx.nyx_py_renderer.ERenderMode.Debug`) | ✅ — must be the **same across all cameras** in the scene |
| Attached camera (mount on entity/link with offset) | ✅ — see {doc}`examples/attached_camera` |
| Runtime pose update | ✅ |
| `aperture`, `focal_len` | ❌ |

## Sensors / output channels

| Channel | Status |
|---|---|
| RGB (`uint8`, `(B, H, W, 3)` on CUDA) | ✅ |
| Depth | ❌ |
| Segmentation | ❌ |
| Normals / world-position / optical-flow passes | ❌ |

Non-visual sensors (IMU, contact, force, proximity, temperature grid) are unaffected — they run through Genesis directly.

## Multi-environment

Multi-env (`n_envs > 1`) works, but the plugin renders each environment in a Python loop rather than batching across the GPU. Cost grows linearly with `n_envs`. Each environment can show a different HDRI for domain randomization.

## Bottom line

You're on the well-trodden path if your scene uses **rigid bodies, articulated robots (URDF/MJCF), FEM/PBD cloth, MPM solids, simple PBR materials, point/directional/spot lights, and HDRI environments**.

Expect rough edges if you rely on **refractive glass, fluids/smoke, particle rendering, area lights, depth-of-field, depth or segmentation passes, ambient lighting from Genesis `VisOptions`, or runtime topology changes**.

For the operational details behind these caveats (scene-lifecycle, CUDA requirement, multi-camera constraints), continue to {doc}`advanced/sensor_lifecycle`.
