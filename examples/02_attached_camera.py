"""Attached camera example for the Nyx renderer plugin.

Mounts a ``NyxCameraOptions`` on the Franka panda's wrist via Genesis'
built-in sensor-attachment fields (``entity_idx`` / ``link_idx_local`` /
``offset_T``), then streams its RGB output to an MP4 through
``scene.start_recording`` while the robot performs a short pick. The camera
follows the link automatically every step, no plugin-specific glue.

Usage:
    uv run python examples/02_attached_camera.py
"""

from __future__ import annotations

import os

import numpy as np

import genesis as gs
import gs_nyx.nyx_py_renderer as npr
from gs_nyx_plugin.nyx_camera_options import NyxCameraOptions


HERE        = os.path.dirname(__file__)
OUTPUT_PATH = os.path.join(HERE, "out", "02_attached_camera.mp4")

FPS = 30

# Wrist camera pose in the Franka "hand" link frame. The camera sits at
# (10 cm, 8 cm, 0) in the hand frame and is rotated to look at the gripper
# fingertip at (0, 0, 10 cm) — the rotation is a standard look-at with
# hand -Z as the up hint, which is world up during the grasp because the
# wrist's R_x(180°) pose flips Z between hand and world. That keeps the
# closing jaws centered as the gripper descends onto the cube.
WRIST_OFFSET_T = np.array(
    [
        [ 0.624695, -0.480604,  0.615457,  0.10],
        [-0.780869, -0.384483,  0.492366,  0.08],
        [ 0.000000, -0.788170, -0.615457,  0.00],
        [ 0.000000,  0.000000,  0.000000,  1.00],
    ],
    dtype=np.float64,
)


def main() -> None:
    gs.init(backend=gs.cpu)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    scene = gs.Scene(
        sim_options=gs.options.SimOptions(dt=1.0 / FPS, substeps=3),
        show_viewer=False,
    )

    scene.add_entity(gs.morphs.Plane())
    scene.add_entity(gs.morphs.Box(size=(0.04, 0.04, 0.04), pos=(0.65, 0.0, 0.02)), surface=gs.surfaces.Gold(roughness=0.1))
    franka = scene.add_entity(gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml"))

    # Camera intrinsics + attachment to the Franka wrist + lighting. The
    # ``lights`` list is plain Genesis sensor config; the plugin converts each
    # dict into an Nyx ``LightAsset`` at build time.
    cam = scene.add_sensor(NyxCameraOptions(
        res            = (1280, 720),
        fov            = 60.0,
        near           = 0.02,
        far            = 50.0,
        entity_idx     = franka.idx,
        link_idx_local = franka.get_link("hand").idx_local,
        offset_T       = WRIST_OFFSET_T,
        spp            = 32,
        render_mode    = npr.ERenderMode.FastPathTracer,
        lights         = [{
            "type":      "directional",
            "dir":       (-0.4, -0.4, -0.8),
            "color":     (1.0, 1.0, 1.0),
            "intensity": 5.0,
            "shadow":    True,
        }],
    ))

    # Stream RGB frames to an MP4 file. ``cam.read().rgb`` is shape
    # (H, W, 3) uint8 in single-env mode.
    scene.start_recording(
        data_func   = lambda: cam.read().rgb,
        rec_options = gs.recorders.VideoFile(filename=OUTPUT_PATH, fps=FPS),
    )

    scene.build()

    # Franka controller gains (from the Genesis IK tutorial)
    franka.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
    franka.set_dofs_kv(np.array([ 450,  450,  350,  350,  200,  200,  200,  10,  10]))
    franka.set_dofs_force_range(
        np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
        np.array([ 87,  87,  87,  87,  12,  12,  12,  100,  100]),
    )
    motors_dof  = np.arange(7)
    fingers_dof = np.arange(7, 9)
    hand        = franka.get_link("hand")

    def execute_path(target_pos, gripper=0.04, num_waypoints=60):
        qpos = franka.inverse_kinematics(
            link=hand, pos=np.array(target_pos), quat=np.array([0, 1, 0, 0]),
        )
        qpos[-2:] = gripper
        for waypoint in franka.plan_path(qpos_goal=qpos, num_waypoints=num_waypoints):
            franka.control_dofs_position(waypoint)
            scene.step()

    def hold(seconds: float):
        for _ in range(int(round(seconds * FPS))):
            scene.step()

    # --- Scripted pick task -------------------------------------------------
    execute_path((0.65, 0.0, 0.25))                                # pre-grasp above cube
    execute_path((0.65, 0.0, 0.13))                                # descend onto cube
    franka.control_dofs_force(np.array([-0.5, -0.5]), fingers_dof) # close gripper
    hold(0.5)

    qpos_lift = franka.inverse_kinematics(
        link=hand, pos=np.array([0.4, 0.2, 0.35]), quat=np.array([0, 1, 0, 0]),
    )
    franka.control_dofs_position(qpos_lift[:-2], motors_dof)       # lift while gripping
    hold(1.5)

    scene.stop_recording()
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
