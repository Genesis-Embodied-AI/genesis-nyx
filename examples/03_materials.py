"""Materials example for the Nyx renderer plugin.

Renders a row of spheres, each with a different ``gs.surfaces`` variant, to
show how common Genesis materials look when shaded by Nyx. The scene is lit
by an HDRI environment map plus a single directional key light so both
diffuse and reflective materials read clearly.

Usage:
    uv run python examples/03_materials.py
"""

from __future__ import annotations

import os
from PIL import Image

import genesis as gs
import gs_nyx.nyx_py_renderer as npr
import gs_nyx.nyx_py_sdk as nps
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions


HERE        = os.path.dirname(__file__)
ENV_MAP     = os.path.join(HERE, "assets", "kloppenheim_07_puresky_4k.hdr")
OUTPUT_PATH = os.path.join(HERE, "out", "03_materials.png")


# A few representative surfaces: a diffuse plastic, a custom PBR BSDF,
# a tinted glass (rendered as plastic, Nyx does not support transparency),
# an emissive material, and two metal shortcuts.
SURFACES = [
    ("plastic",  lambda: gs.surfaces.Plastic(color=(0.85, 0.20, 0.20))),
    ("bsdf",     lambda: gs.surfaces.BSDF(color=(0.20, 0.40, 0.85), metallic=0.0, roughness=0.25)),
    ("glass",    lambda: gs.surfaces.Glass(color=(0.70, 0.95, 1.00))),
    ("gold",     lambda: gs.surfaces.Gold()),
    ("copper",   lambda: gs.surfaces.Copper()),
    ("emission", lambda: gs.surfaces.Emission(emissive=(4.0, 1.5, 0.4))),
]

SPHERE_RADIUS = 0.4
SPACING       = 1.1
SPHERE_Z      = SPHERE_RADIUS

CAM_POS    = (0.0, -4.5, 1.5)
CAM_LOOKAT = (0.0,  0.0, SPHERE_Z)
CAM_RES    = (1600, 600)
CAM_FOV    = 35.0


def main() -> None:
    gs.init()

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=0.01),
        show_viewer=False,
    )

    scene.add_entity(morph=gs.morphs.Plane(plane_size=(10.0, 10.0)))

    # Lay the spheres out along X so the camera frames them in a single row.
    x0 = -SPACING * (len(SURFACES) - 1) * 0.5
    for i, (_, factory) in enumerate(SURFACES):
        scene.add_entity(
            morph=gs.morphs.Sphere(
                pos=(x0 + i * SPACING, 0.0, SPHERE_Z),
                radius=SPHERE_RADIUS,
                fixed=True,
                collision=False,
            ),
            surface=factory(),
        )

    env_map            = nps.EnvironmentMapAsset()
    env_map.texture    = ENV_MAP
    env_map.layout     = nps.EEnvMapLayout.LongLat
    env_map.multiplier = 2.0

    key_light = {
        "type":      "directional",
        "dir":       (-0.3, 0.6, -1.0),
        "color":     (1.0, 1.0, 1.0),
        "intensity": 3.0,
    }

    cam = scene.add_sensor(NyxCameraOptions(
        res         = CAM_RES,
        pos         = CAM_POS,
        lookat      = CAM_LOOKAT,
        fov         = CAM_FOV,
        spp         = 64,
        denoise     = True,
        render_mode = npr.ERenderMode.FastPathTracer,
        env_maps    = (env_map,),
        lights      = [key_light],
    ))

    scene.build(n_envs=1)
    scene.step()

    rgb = cam.read().rgb[0].cpu().numpy()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    Image.fromarray(rgb).save(OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
