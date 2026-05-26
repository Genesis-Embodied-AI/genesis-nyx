"""Light types example for the Nyx renderer plugin.

Renders the same trio of PBR balls under all three light types the plugin
exposes through ``NyxCameraOptions.lights``: a coloured **point** light on
the left, a white **directional** "sun" from above, and a coloured **spot**
cone aimed at the ball on the right. A pitch-black colour-only environment
map is attached so the default grey HDRI sky is suppressed and every
photon reaching a surface comes from the three explicit lights.

Usage:
    uv run python examples/04_light_types.py
"""

from __future__ import annotations

import math
import os

from PIL import Image

import genesis as gs
import gs_nyx.nyx_py_sdk as nps
import gs_nyx.nyx_py_renderer as npr
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions


HERE        = os.path.dirname(__file__)
PBR_BALL    = os.path.join(HERE, "assets", "PBR_Ball.glb")
OUTPUT_PATH = os.path.join(HERE, "out", "04_light_types.png")

# Ball positions on the plane (Z-up). Each ball is the "hero" for one light;
# the spacing is wide enough that the coloured falloffs don't bleed into the
# neighbour.
BALL_LEFT   = (-0.93, 0.0, 0.0)
BALL_MID    = ( 0.00, 0.0, 0.0)
BALL_RIGHT  = ( 0.93, 0.0, 0.0)

# Point light: hovers just above the left ball, saturated red, short range so
# the falloff is visible on the plane and doesn't reach the middle ball.
POINT_LIGHT = {
    "type":      "point",
    "pos":       (-0.93, 0.0, 0.5),
    "color":     (1.0, 0.15, 0.05),
    "intensity": 4.0,
    "range":     0.8,
}

# Directional light: a soft green "sun" tilted from the front-top. Reaches
# every ball equally; aimed at the middle ball so it dominates only there.
DIRECTIONAL_LIGHT = {
    "type":      "directional",
    "dir":       (0.0, 0.3, -0.95),
    "color":     (0.25, 1.0, 0.35),
    "intensity": 2.0,
}

# Spot light: high and to the right, aimed down-and-in at the right ball. A
# narrow inner / outer cone produces a clear blue hotspot with a soft edge.
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


def main() -> None:
    gs.init()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=0.01),
        show_viewer=False,
    )

    scene.add_entity(morph=gs.morphs.Plane(plane_size=(10.0, 10.0)))
    for pos in (BALL_LEFT, BALL_MID, BALL_RIGHT):
        scene.add_entity(
            morph=gs.morphs.Mesh(file=PBR_BALL, pos=pos),
            surface=gs.surfaces.Default(),
        )

    # Suppress Nyx's default grey HDRI sky. An EnvironmentMapAsset with no
    # texture is treated as a solid-colour HDRI whose value is `tint`, so
    # setting tint to (0, 0, 0) makes the sky pitch black and the three
    # explicit lights are the only contributors to the image.
    black_sky      = nps.EnvironmentMapAsset()
    black_sky.tint = nps.float3(0.0, 0.0, 0.0)

    cam = scene.add_sensor(NyxCameraOptions(
        res         = (1920, 1080),
        pos         = (0.0, 4.5, 1.8),
        lookat      = (0.0, 0.0, 0.15),
        fov         = 21.0,
        spp         = 64,
        render_mode = npr.ERenderMode.FastPathTracer,
        lights      = [POINT_LIGHT, DIRECTIONAL_LIGHT, SPOT_LIGHT],
        env_maps    = (black_sky,),
    ))

    scene.build(n_envs=1)
    scene.step()

    rgb = cam.read().rgb[0].cpu().numpy()
    Image.fromarray(rgb).save(OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
