# Object picking

The Nyx plugin exposes a **ray API** on every Nyx camera: {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.pick_pixel` `(camera_index, x, y)` casts a ray from the camera through one pixel of its framebuffer and returns the first Genesis entity it hits, along with the world-space hit point. It's the entry point for picking, hover hit-tests, click-to-select tooling, and any "what's under this pixel?" question you'd otherwise need a separate ID buffer for.

This example names four balls by their colour, casts a grid of rays across the rendered frame, and uses `pick_pixel`'s return value to (a) drop a colour-keyed dot on top of every hit and (b) print a per-ball hit count and mean world position to stdout.

{{ example_06_object_picking_screenshot }}

## What it shows

- Four spheres named by their colour (`gold`, `copper`, `red`, `cyan`) on a Genesis `Plane`, lit by an HDR environment map.
- A 48 × 36 grid of `pick_pixel` calls across the rendered frame — one ray per grid cell, 1 728 rays total.
- Each hit drawn as a translucent coloured dot keyed by entity. **Plane hits and sky misses are both filtered out** — the overlay isolates only the four balls.
- A stdout summary line per ball: `<name>  <count> hits  mean pos=(x, y, z)`. The name comes from a Python dict keyed by the entity object the API returned; the position comes from the `position` field of the same `pick_pixel` result averaged across every hit on that ball.

## The ray API in one call

```python
result = cam.pick_pixel(camera_index=0, x=px, y=py)
```

- `camera_index` indexes into the cameras that share this sensor's renderer. For a single `NyxCameraSensor` it's always `0`; multi-camera setups index in registration order.
- `x`, `y` are pixel coordinates with the **origin at the top-left** of the framebuffer. They must lie inside the camera's configured `res`.
- The call returns either `None` (the ray hit nothing in the scene — the background / sky) or a {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxPickPixelResult` named tuple with three fields:

| Field | Type | Meaning |
|---|---|---|
| `entity` | `genesis.engine.entities.base_entity.Entity` | The same Python object the user passed to `scene.add_entity` — `id(result.entity)` is stable, so dict lookups by entity work. This is how the example recovers a colour name from a ray hit. |
| `link_name` | `str` | Sub-geometry hit. For URDF entities it's the link name; for MJCF entities it's `"<link>_<vgeom_idx>"`; empty string for `Mesh`, `Plane`, `Sphere`, etc. — primitives like the spheres in this example don't have nameable sub-parts. |
| `position` | `tuple[float, float, float]` | World-space hit point `(x, y, z)` in **Genesis Z-up** coordinates — the plugin converts from Nyx's internal Y-up before returning. |

## Getting a name back from the API

Genesis primitives don't carry a string identifier the renderer can hand you, so for non-URDF / non-MJCF entities `link_name` is empty. To label a hit with something the rendered image is named *by*, hold onto your own `{entity: name}` mapping at construction time and resolve through it after the pick:

```python
scene.add_entity(morph=gs.morphs.Plane(...))                                          # in the scene, NOT in the name table
gold = scene.add_entity(morph=gs.morphs.Sphere(...), surface=gs.surfaces.Gold())
red  = scene.add_entity(morph=gs.morphs.Sphere(...), surface=gs.surfaces.Plastic(...))

names = {id(gold): "gold", id(red): "red", ...}

res = cam.pick_pixel(0, px, py)
if res is None:
    ...                                   # background (sky); ignore
elif id(res.entity) not in names:
    ...                                   # hit something we don't care about (the plane); ignore
else:
    name = names[id(res.entity)]          # "gold", "red", ...
    print(f"hit {name} at {res.position}")
```

The `id()` key works because `pick_pixel` returns the same Python object you passed to `scene.add_entity` — no copy, no proxy. Plain `==` works for the same reason, but `id()` keeps the lookup O(1) and side-effect-free. Leaving entities you don't want to pick *out* of the lookup table is also how the example filters the plane: any ray that hits the ground falls into the `not in names` branch and is dropped, without ever needing a per-entity blacklist.

## The picking loop

The overlay is a transparent RGBA image the script draws into, then alpha-composites over the rendered RGB. Each accepted hit does two things — splat a dot, and accumulate the world hit position into a running sum keyed by name so the stdout summary at the end shows a mean rather than a single noisy sample:

```python
for gy in range(GRID_H):
    py = int((gy + 0.5) * H / GRID_H)
    for gx in range(GRID_W):
        px  = int((gx + 0.5) * W / GRID_W)
        res = cam.pick_pixel(0, px, py)
        if res is None:
            continue                          # background (sky)
        name = name_by_eid.get(id(res.entity))
        if name is None:
            continue                          # entity outside the picking set (plane)

        draw.ellipse(..., fill=BALLS[name][2])
        wx, wy, wz = res.position
        h = hits[name]
        h[0] += 1; h[1] += wx; h[2] += wy; h[3] += wz
```

## Notes worth keeping in mind

- **Picking does not require a render.** The renderer can pick-trace a ray as soon as the scene has been built — [`cam.read()`](https://genesis-world.readthedocs.io/en/latest/api_reference/sensor/index.html#reading-sensor-data) (or even [`scene.step()`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.step)) is not a prerequisite. The example happens to render first because it wants to draw the overlay over the rendered image, but the same `pick_pixel` calls would work right after [`scene.build(...)`](https://genesis-world.readthedocs.io/en/latest/api_reference/scene/scene.html#genesis.engine.scene.Scene.build).
- **Picking does not consume samples.** Sample budgets (`spp`, `render_mode`, denoising) configure the *render* pipeline. `pick_pixel` always traces a single deterministic ray and is unaffected by those settings.
- **The picked entity object is the registered one.** `result.entity is entity_you_added_to_the_scene` holds, so identity comparisons and `id()`-keyed dicts both work.
- **`None` is background, an unregistered entity is "ignore".** Sky rays return `None`; rays that hit something *in* the scene but *not* in your lookup table (the plane, in this example) come back as a fully valid {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxPickPixelResult` you simply choose to skip. Both branches leave the original render untouched in the overlay.
- **One pick = one native call.** The plugin doesn't currently batch picks; {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.pick_pixel` is a thin Python wrapper around a single native ray trace. For a few hundred picks per frame this is fine; for full-screen ID buffers you'll want to render once at full resolution and only pick the pixels you actually need (the cursor location, a small lasso, etc.).

## Reading the saved image and the stdout

- The coloured dots in the saved PNG are the entity-ID buffer: each one is one `pick_pixel` hit that resolved to a registered ball, coloured to match the rendered surface it landed on.
- Where the dots disappear, the ray either missed every entity (sky) or hit the plane (filtered out by leaving it out of the picking table). Both cases let the original render show through unmodified.
- The terminal output prints one line per ball, e.g. `gold   123 hits   mean pos=(-1.00, +0.50, +0.65)`. The colour name came back out of `pick_pixel` via the `name_by_eid` lookup; the mean position is `res.position` averaged across every hit on that ball, which is stable enough to compare against `add_entity(pos=...)` and confirm Z-up world coordinates.

## Source

```{literalinclude} ../../../../examples/06_object_picking.py
:language: python
:linenos:
```

Run it:

```bash
uv run python examples/06_object_picking.py
```

The PNG is written to `examples/out/06_object_picking.png`. The Sphinx build copies it to `_static/generated/examples/06_object_picking.png` and embeds it at the top of this page, so the docs site always shows whatever the latest run produced.

## See also

- {doc}`hello_nyx` — The minimal Nyx scene the picking grid is layered on top of conceptually: same camera + env-map setup, without the overlay step.
- {doc}`attached_camera` — How {py:class}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor` integrates with Genesis' sensor manager. Picking inherits the same lifecycle: any sensor returned by `scene.add_sensor(NyxCameraOptions(...))` exposes {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.pick_pixel`.
- {doc}`../advanced/sensor_lifecycle` — When the sensor is built, when the renderer is ready, and what does (and does not) need to happen before {py:meth}`~gs_nyx_plugin.nyx_camera_sensor.NyxCameraSensor.pick_pixel` is callable.
