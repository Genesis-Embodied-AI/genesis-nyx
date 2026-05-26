# Materials

A side-by-side render of the most common `gs.surfaces` variants on identical spheres. Use this page to get a feel for how each material shades under Nyx before choosing one for your own scene.

{{ example_03_materials_screenshot }}

## What it shows

Six spheres are laid out in a row on a ground plane. Geometry, lighting, and camera are identical for every sphere, only the `surface=` argument changes, so each ball is a direct visual sample of one Genesis material:

| Sphere | Surface | What to look for |
|---|---|---|
| 1 | `gs.surfaces.Plastic(color=...)` | Diffuse base colour with a soft, low-intensity specular highlight from the key light. |
| 2 | `gs.surfaces.BSDF(metallic=0, roughness=0.25)` | Custom PBR: same base colour as plastic but a sharper, blurred reflection of the HDRI. |
| 3 | `gs.surfaces.Glass(color=...)` | Transparency is not supported, glass is rendered as plastic with the given tint. |
| 4 | `gs.surfaces.Gold()` | Saturated yellow metal reflection of the HDRI, no diffuse component. |
| 5 | `gs.surfaces.Copper()` | Same metal model as gold with the copper preset's complex IOR, warmer and less saturated. |
| 6 | `gs.surfaces.Emission(emissive=...)` | Glowing surface unaffected by the lights or the env map. |

A few things worth noting:

- **No plugin-specific surface types.** Everything passed to `surface=` is a stock `genesis.surfaces.*` value. The Nyx plugin translates each one to its own material at `scene.build()`, so anything documented in the Genesis material reference works here unchanged.
- **Metal shortcuts vs. `BSDF`.** `Gold()`, `Copper()`, `Iron()`, etc. are presets over the same underlying PBR model. Use them when you want a named real-world metal, drop down to `BSDF(metallic=..., roughness=...)` when you want full control.
- **`Emission` ignores lighting.** The emissive ball stays the same brightness regardless of the env map or the key light. That makes it useful for indicator markers, screens, or any geometry that should read as "self-lit".
- **Surfaces are single-use.** A `gs.surfaces.*` instance can only be attached to one entity, which is why the example stores factories (`lambda: gs.surfaces.Plastic(...)`) rather than pre-built objects.

## Source

```{literalinclude} ../../../../examples/03_materials.py
:language: python
:linenos:
```

Run it:

```bash
uv run python examples/03_materials.py
```

The PNG is written to `examples/out/03_materials.png`. The Sphinx build copies it to `_static/generated/examples/03_materials.png` and embeds it at the top of this page, so the docs site always shows whatever the latest run produced.

## See also

- {doc}`light_types` — A complementary scene where the lights vary and the material stays fixed.
- {doc}`../advanced/environment_maps` — HDR image-based lighting ({py:class}`~gs_nyx.nyx_py_sdk.EnvironmentMapAsset` reference).
- {doc}`../advanced/lights` — Point / directional / spot light schema and photometric units.
