"""Gaussian splat example for the Nyx renderer plugin.

Renders a captured Gaussian splat (``plant.ply``) sitting on a Genesis
``Plane``, lit by the ``green_sanctuary`` HDRI environment map. Demonstrates
declaring a ``LightFieldAsset`` on ``NyxCameraOptions.light_fields`` so the
radiance field renders alongside simulated geometry every frame.

Usage:
    uv run python examples/05_gaussian_splat.py
"""

from __future__ import annotations

import os

from PIL import Image

import genesis as gs
import gs_nyx.nyx_py_renderer as npr
import gs_nyx.nyx_py_sdk as nps
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions


HERE        = os.path.dirname(__file__)
PLANT_PLY   = os.path.join(HERE, "assets", "plant.ply")
ENV_MAP     = os.path.join(HERE, "assets", "green_sanctuary_4k.hdr")
OUTPUT_PATH = os.path.join(HERE, "out", "05_gaussian_splat.png")


def main() -> None:
    gs.init()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=0.01),
        show_viewer=False,
    )

    scene.add_entity(morph=gs.morphs.Plane(plane_size=(2.0, 2.0)))

    # The splat is declared on the camera as a LightFieldAsset rather than as
    # a Genesis entity. light_fields from every Nyx sensor are collected at
    # scene.build() and rendered alongside simulated geometry.
    plant          = nps.LightFieldAsset()
    plant.type     = nps.ELightFieldType.GaussianField
    plant.uri      = PLANT_PLY
    # 90° rotation about Z stands the capture upright in Genesis' Z-up world.
    plant.rotation = nps.quaternion(0.0, 0.0, -0.70710678, 0.70710678)

    # HDRI environment lighting the plane. The splat already has
    # view-dependent colour baked in, so only the simulated geometry needs
    # the env map as a light source.
    env_map            = nps.EnvironmentMapAsset()
    env_map.texture    = ENV_MAP
    env_map.layout     = nps.EEnvMapLayout.LongLat
    env_map.multiplier = 2.0

    cam = scene.add_sensor(NyxCameraOptions(
        res          = (1920, 1080),
        pos          = (1.0, 1.5, 0.8),
        lookat       = (0.0, 0.0, 0.1),
        fov          = 30.0,
        spp          = 64,
        render_mode  = npr.ERenderMode.FastPathTracer,
        env_maps     = [env_map],
        light_fields = [plant],
    ))

    scene.build(n_envs=1)
    scene.step()

    rgb = cam.read().rgb[0].cpu().numpy()
    Image.fromarray(rgb).save(OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
