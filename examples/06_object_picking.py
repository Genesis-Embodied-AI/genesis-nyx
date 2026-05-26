"""Object picking example for the Nyx renderer plugin.

Demonstrates the **ray API** exposed through
``NyxCameraSensor.pick_pixel``: given a pixel coordinate, the renderer
traces a ray from the camera through that pixel and reports the first
scene entity it hits (or ``None`` for background).

The script names each ball by its colour, renders the scene, then casts
a coarse grid of rays. Every hit drops a translucent dot on the overlay
so the image reads like a low-resolution ID buffer. The per-ball hit
count and the mean world hit position recovered from ``pick_pixel`` are
printed to stdout — the API's return value is the only data source.

Usage:
    uv run python examples/06_object_picking.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

import genesis as gs
import gs_nyx.nyx_py_renderer as npr
import gs_nyx.nyx_py_sdk as nps
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions


HERE        = os.path.dirname(__file__)
ENV_MAP     = os.path.join(HERE, "assets", "kloppenheim_07_puresky_4k.hdr")
OUTPUT_PATH = os.path.join(HERE, "out", "06_object_picking.png")

CAM_RES        = (960, 720)
GRID_W, GRID_H = 48, 36

# Four balls named by colour. ``name -> (surface, world_pos, dot_rgba)``.
# The plane is rendered for shadows but kept out of this dict, so any
# ray that hits the ground falls into the "not in BALLS" branch and is
# silently ignored.
BALLS = {
    "gold":   (gs.surfaces.Gold(),                                                      (-1.0,  0.5, 0.4), (255, 200,  50, 180)),
    "copper": (gs.surfaces.Copper(),                                                    ( 0.0,  0.0, 0.4), (255, 120,  60, 180)),
    "red":    (gs.surfaces.Plastic(color=(0.85, 0.10, 0.10)),                           ( 1.0,  0.5, 0.4), (255,  60,  60, 180)),
    "cyan":   (gs.surfaces.BSDF(color=(0.10, 0.60, 0.65), metallic=0.0, roughness=0.2), ( 0.5, -0.8, 0.4), ( 60, 220, 220, 180)),
}


def main() -> None:
    gs.init()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    scene = gs.Scene(sim_options=gs.options.SimOptions(dt=0.01), show_viewer=False)
    scene.add_entity(morph=gs.morphs.Plane(plane_size=(10.0, 10.0)))

    # Single lookup that ties an entity returned by ``pick_pixel`` back
    # to its colour name. Plane is not in here on purpose.
    name_by_eid: dict[int, str] = {}
    for name, (surface, pos, _) in BALLS.items():
        e = scene.add_entity(
            morph=gs.morphs.Sphere(pos=pos, radius=0.4, fixed=True, collision=False),
            surface=surface,
        )
        name_by_eid[id(e)] = name

    env_map            = nps.EnvironmentMapAsset()
    env_map.texture    = ENV_MAP
    env_map.layout     = nps.EEnvMapLayout.LongLat
    env_map.multiplier = 2.0

    cam = scene.add_sensor(NyxCameraOptions(
        res         = CAM_RES,
        pos         = (2.5, -3.5, 2.6),
        lookat      = (0.0, 0.0, 0.3),
        fov         = 30.0,
        spp         = 64,
        render_mode = npr.ERenderMode.FastPathTracer,
        env_maps    = (env_map,),
    ))

    scene.build(n_envs=1)
    scene.step()

    base    = Image.fromarray(cam.read().rgb[0].cpu().numpy()).convert("RGBA")
    W, H    = CAM_RES
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    dot_r   = max(1, min(W // GRID_W, H // GRID_H) // 2 - 1)

    # Per-ball: [hit count, sum world x, sum world y, sum world z].
    # Stays empty for any ball the grid never lands on.
    hits: dict[str, list[float]] = {n: [0.0, 0.0, 0.0, 0.0] for n in BALLS}

    for gy in range(GRID_H):
        py = int((gy + 0.5) * H / GRID_H)
        for gx in range(GRID_W):
            px  = int((gx + 0.5) * W / GRID_W)
            res = cam.pick_pixel(0, px, py)
            if res is None:
                continue                  # background (sky)
            name = name_by_eid.get(id(res.entity))
            if name is None:
                continue                  # entity outside the picking set (plane)
            draw.ellipse((px - dot_r, py - dot_r, px + dot_r, py + dot_r), fill=BALLS[name][2])
            wx, wy, wz = res.position
            h = hits[name]
            h[0] += 1; h[1] += wx; h[2] += wy; h[3] += wz

    Image.alpha_composite(base, overlay).convert("RGB").save(OUTPUT_PATH)

    print(f"Saved {OUTPUT_PATH}")
    for name, (n, sx, sy, sz) in hits.items():
        if n:
            print(f"  {name:<6} {int(n):>4} hits   mean pos=({sx/n:+.2f}, {sy/n:+.2f}, {sz/n:+.2f})")
        else:
            print(f"  {name:<6}    0 hits")


if __name__ == "__main__":
    main()
