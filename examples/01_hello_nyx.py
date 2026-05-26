"""
Minimal Nyx example: a PBR ball on a plane lit by an environment map.

Loads PBR_Ball.glb (GLTF embedded materials are forwarded to Nyx as-is) and
lights it purely with an .exr environment map.

Usage:
    uv run python examples/01_hello_nyx.py
"""

import os
from PIL import Image

import genesis as gs
import gs_nyx.nyx_py_renderer as npr
import gs_nyx.nyx_py_sdk as nps
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions


HERE        = os.path.dirname(__file__)
PBR_BALL    = os.path.join(HERE, "assets", "PBR_Ball.glb")
ENV_MAP     = os.path.join(HERE, "assets", "kloppenheim_07_puresky_4k.hdr")
OUTPUT_PATH = os.path.join(HERE, "out", "01_hello_nyx.png")


def main():
    gs.init()

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=0.01),
        show_viewer=False,
    )

    scene.add_entity(
        morph=gs.morphs.Plane(plane_size=(10.0, 10.0)),
    )

    scene.add_entity(
        morph=gs.morphs.Mesh(file=PBR_BALL, pos=(0.0, 0.0, 0.0)),
        surface=gs.surfaces.Gold(),
    )

    # Describe how the env map is encoded
    env_map            = nps.EnvironmentMapAsset()
    env_map.texture    = ENV_MAP
    env_map.layout     = nps.EEnvMapLayout.LongLat
    env_map.multiplier = 8

    # Describe the Nyx camera sensor
    cam = scene.add_sensor(NyxCameraOptions(
        res         = (1920, 1080),
        pos         = (-1.0, 1.0, 1.2),
        lookat      = (0.0, 0.0, 0.1),
        fov         = 20.0,
        spp         = 64,
        render_mode = npr.ERenderMode.FastPathTracer,
        env_maps    = (env_map,),
    ))

    # Build the scene with a single env
    scene.build(n_envs=1)

    # This simulation step makes the camera sensor render the frame
    scene.step()

    # Read back the sensor frame and save it
    rgb = cam.read().rgb[0].cpu().numpy()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    Image.fromarray(rgb).save(OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
