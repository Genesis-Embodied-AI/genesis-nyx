"""Multi-camera, multi-environment example for the Nyx renderer plugin.

Builds a scene with **two** ``NyxCameraSensor`` instances and ``n_envs=4``
parallel Genesis environments, then teleports the rendered ball to a
different spot on the plane in each env. The first camera is a static
high overhead view shared across every env; the second is a low follow
camera attached to an invisible rigid rig whose position **and** orientation
are set per env, so each follow cell approaches the ball from a different
direction. A single ``read()`` per camera returns a batched
``(N_ENVS, H, W, 3)`` tensor, which the script tiles into one PNG
(rows = cameras, columns = envs).

Usage:
    uv run python examples/07_multi_camera_multi_env.py
"""

from __future__ import annotations

import math
import os

import torch
from PIL import Image

import genesis as gs
import gs_nyx.nyx_py_renderer as npr
import gs_nyx.nyx_py_sdk as nps
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions


HERE         = os.path.dirname(__file__)
PBR_BALL     = os.path.join(HERE, "assets", "PBR_Ball.glb")
ENV_MAP_SKY  = os.path.join(HERE, "assets", "kloppenheim_07_puresky_4k.hdr")
ENV_MAP_STUD = os.path.join(HERE, "assets", "green_sanctuary_4k.hdr")
OUTPUT_PATH  = os.path.join(HERE, "out", "07_multi_camera_multi_env.png")

N_ENVS  = 4
CAM_RES = (640, 480)

# One ball position per env, arranged on a circle of radius R so the wide
# overview shows the ball at four clearly different spots. The Z component
# lifts the ball off the plane so it sits cleanly above the ground.
R = 1.2
BALL_POSITIONS = [
    [ 0.0,  R, 0.0],
    [  R, 0.0, 0.0],
    [ 0.0, -R, 0.0],
    [ -R, 0.0, 0.0],
]

# Per-env rig orientation (Z-axis rotation, WXYZ quaternion). Rotates the
# rig so that the follow camera's "behind" direction always points outward
# from the centre of the plane — every env sees the ball from a different
# radial angle, which is what makes the follow row visually distinct.
RIG_OUTWARD_QUATS = [
    [           0.0, 0.0, 0.0,            1.0],  # 180° around Z
    [math.sqrt(0.5), 0.0, 0.0, -math.sqrt(0.5)],  # -90° around Z
    [           1.0, 0.0, 0.0,            0.0],  #   0° around Z
    [math.sqrt(0.5), 0.0, 0.0,  math.sqrt(0.5)],  # +90° around Z
]


def main() -> None:
    gs.init()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=0.01),
        show_viewer=False,
    )

    scene.add_entity(morph=gs.morphs.Plane(plane_size=(10.0, 10.0)))

    # Override the GLB's embedded materials with a polished sapphire-blue
    # chrome — low roughness + full metallic so each follow camera's
    # reflection of the HDRI sky reads as a distinct slice of the dome.
    # ``align=False`` keeps the link origin at the GLB's authored pivot
    # (the cup base) instead of re-framing it to the composite's COM, so
    # ``set_pos(z=0)`` lands the cup cleanly on the plane.
    ball = scene.add_entity(
        morph=gs.morphs.Mesh(file=PBR_BALL, pos=(0.0, 0.0, 0.0), align=False),
        surface=gs.surfaces.BSDF(metallic=1.0, roughness=0.15),
    )

    # Invisible rigid rig used as the follow camera's attachment point.
    # Both its position and its orientation are set per env, which is how
    # the follow camera ends up at a different world pose in every env.
    # Must be added before any FEM / MPM / PBD entity so its ``entity.idx``
    # matches the rigid solver's index — that's what
    # ``NyxCameraOptions.entity_idx`` uses.
    follow_rig = scene.add_entity(
        morph=gs.morphs.Sphere(
            pos=(0.0, 0.0, 0.0), radius=0.01,
            visualization=False, fixed=True,
        ),
    )

    # Lighting. ``env_maps`` is indexed positionally by env: env ``i`` is
    # lit by ``env_maps[i]``. We alternate two HDRIs across the four envs
    # so even envs render under a clear outdoor sky and odd envs render
    # under a studio softbox setup — same scene, two completely different
    # lighting moods, visible side by side in the tiled output. ``lights``
    # and ``light_fields`` (not used here) are merged scene-wide instead.
    def _make_env_map(path: str) -> nps.EnvironmentMapAsset:
        asset            = nps.EnvironmentMapAsset()
        asset.texture    = path
        asset.layout     = nps.EEnvMapLayout.LongLat
        asset.multiplier = 2.0
        return asset

    env_map_sky    = _make_env_map(ENV_MAP_SKY)
    env_map_studio = _make_env_map(ENV_MAP_STUD)
    per_env_maps   = (env_map_sky, env_map_studio, env_map_sky, env_map_studio)

    # Camera A — high overhead overview. Same world pose in every env; what
    # differs per column is the simulator state inside the frame.
    wide_cam = scene.add_sensor(NyxCameraOptions(
        res         = CAM_RES,
        pos         = (0.5, -2.5, 4.0),
        lookat      = (0.0,  0.0, 0.5),
        fov         = 42.0,
        spp         = 64,
        render_mode = npr.ERenderMode.FastPathTracer,
        env_maps    = per_env_maps,
    ))

    # Camera B — eye-level follow camera. ``offset_T`` is the camera pose
    # in the rig's local frame: 1.1 m back along the rig's -Y axis and
    # 0.45 m above it, aimed at the ball portion of the composite (0.25 m
    # above the cup base). Rotating the rig per env rotates the camera's
    # relative pose with it, so the follow cell for each env shows a
    # different radial angle on the same ball.
    offset_T = gs.utils.geom.pos_lookat_up_to_T(
        torch.tensor((0.0, -1.1, 0.45), dtype=torch.float32),
        torch.tensor((0.0,  0.0, 0.25), dtype=torch.float32),
        torch.tensor((0.0,  0.0, 1.0),  dtype=torch.float32),
    ).cpu().numpy()

    follow_cam = scene.add_sensor(NyxCameraOptions(
        res         = CAM_RES,
        fov         = 45.0,
        spp         = 64,
        render_mode = npr.ERenderMode.FastPathTracer,
        entity_idx  = follow_rig.idx,
        offset_T    = offset_T,
    ))

    # ``n_envs=N`` makes every sensor return a batched tensor:
    # ``cam.read().rgb`` has shape ``(N_ENVS, H, W, 3)``.
    scene.build(n_envs=N_ENVS)

    # Per-env state setters. All three calls share the outer dimension
    # ``N_ENVS``: ball position, rig position (rig follows the ball), and
    # rig orientation (rig points outward in each env).
    ball.set_pos(BALL_POSITIONS)
    follow_rig.set_pos(BALL_POSITIONS)
    follow_rig.set_quat(RIG_OUTWARD_QUATS)

    # One step drives every sensor; one ``read()`` returns the full batch.
    scene.step()
    wide_batch   = wide_cam.read().rgb.cpu().numpy()
    follow_batch = follow_cam.read().rgb.cpu().numpy()

    # Tile: rows = cameras (wide on top, follow below), columns = envs.
    H, W = CAM_RES[1], CAM_RES[0]
    grid = Image.new("RGB", (W * N_ENVS, H * 2))
    for env_idx in range(N_ENVS):
        grid.paste(Image.fromarray(wide_batch[env_idx]),   (env_idx * W, 0))
        grid.paste(Image.fromarray(follow_batch[env_idx]), (env_idx * W, H))
    grid.save(OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
