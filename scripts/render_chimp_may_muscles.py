"""Render HQ orthographic and perspective views of the chimp fullbody model
(May 2025 version) with muscles color-coded by functional group, all with
transparent backgrounds.

Produces four individual PNGs plus a 2x2 composite:
  - frontal    (anterior, camera along +X)
  - sagittal   (side, camera along +Z)
  - transverse (from below looking up at feet, camera along -Y)
  - perspective (45 deg azimuth / 45 deg elevation, perspective projection)

Usage:
    C:\\Users\\asundar4\\.conda\\envs\\osim-render\\python.exe scripts/render_chimp_may_muscles.py
"""

import math
from pathlib import Path
from typing import Callable

import vtkmodules.all as vtk
from PIL import Image

from osim_render.api.animation.animation import AnimationState
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager

MODEL_PATH = Path(r"F:\dev\projects\gait_sim\models\chimp_fullbody\model_May2025.osim")
RESOLUTION = (2160, 2160)

# Pose the elbows at the chimp's standard ~15 deg of flexion (radians) rather
# than the model's near-zero default (fully extended arms).
ELBOW_FLEX_RAD = math.radians(15.0)
POSE = AnimationState(
    time=0.0,
    coordinate_values={"elbow_flex_r": ELBOW_FLEX_RAD, "elbow_flex_l": ELBOW_FLEX_RAD},
    camera_state=None,
    actor_properties={},
)
STATE = AnimationState(time=0.0, coordinate_values={}, camera_state=None, actor_properties={})

MUSCLE_GROUPS: dict[str, tuple[tuple[float, float, float], tuple[str, ...]]] = {
    "glutes_hip_extensors": (
        (0.90, 0.30, 0.10),
        ("glmax1", "glmax2", "glmax3", "glmax4", "glmed1", "glmed2", "glmed3",
         "glmin1", "glmin2", "glmin3", "piri", "gem", "quadfem", "obex"),
    ),
    "hip_flexors": (
        (0.10, 0.50, 0.90),
        ("iliacus", "psoas", "recfem", "sart"),
    ),
    "hamstrings": (
        (0.90, 0.70, 0.10),
        ("bflh", "bfsh", "semimem", "semiten"),
    ),
    "quadriceps": (
        (0.20, 0.90, 0.40),
        ("vasint", "vaslat", "vasmed"),
    ),
    "adductors": (
        (0.70, 0.20, 0.90),
        ("adbrev", "adlong", "admag1", "admag2", "admag3", "admag4", "grac", "pect"),
    ),
    "plantarflexors": (
        (0.95, 0.40, 0.60),
        ("gaslat", "gasmed", "sol", "tibpos", "fdf", "fdt"),
    ),
    "dorsiflexors_evertors": (
        (0.20, 0.85, 0.85),
        ("tibant", "edl", "ehl", "perbrev", "perlong"),
    ),
}


def muscle_color(muscle_name: str) -> tuple[float, float, float] | None:
    base = muscle_name.removesuffix("_l").removesuffix("_r")
    for color, members in MUSCLE_GROUPS.values():
        if base in members:
            return color
    return None


def render_view(
    output_path: Path,
    configure_camera: Callable[[vtk.vtkRenderer], None],
) -> None:
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(MODEL_PATH)

    offscreen = OffscreenRenderer(resolution=RESOLUTION, transparent_background=True)
    scene_manager = SceneManager(model_manager, MODEL_PATH)
    scene = scene_manager.create_scene(renderer=offscreen.renderer)

    muscle_actors = scene.muscle_actors
    if muscle_actors is None:
        raise SystemExit("Scene has no muscle actors to color")

    for muscle_name, muscle_actor in muscle_actors.items():
        color = muscle_color(muscle_name)
        if color is not None:
            muscle_actor.GetProperty().SetColor(*color)
        muscle_actor.SetVisibility(True)

    # Apply the elbow-flexion pose before framing so the camera sees the
    # bent-arm posture (save_frame itself does not apply coordinate values).
    scene_manager.update_frame(POSE)

    renderer = offscreen.renderer
    renderer.ResetCamera()
    configure_camera(renderer)
    renderer.ResetCameraClippingRange()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    offscreen.save_frame(STATE, output_path)
    print(f"Saved {output_path}")


def frontal_camera(renderer: vtk.vtkRenderer) -> None:
    camera = renderer.GetActiveCamera()
    distance = camera.GetDistance()
    cx, cy, cz = camera.GetFocalPoint()
    camera.SetPosition(cx + distance, cy, cz)
    camera.SetFocalPoint(cx, cy, cz)
    camera.SetViewUp(0, 1, 0)
    camera.SetParallelProjection(True)


def sagittal_camera(renderer: vtk.vtkRenderer) -> None:
    camera = renderer.GetActiveCamera()
    distance = camera.GetDistance()
    cx, cy, cz = camera.GetFocalPoint()
    camera.SetPosition(cx, cy, cz + distance)
    camera.SetFocalPoint(cx, cy, cz)
    camera.SetViewUp(0, 1, 0)
    camera.SetParallelProjection(True)


def transverse_feet_camera(renderer: vtk.vtkRenderer) -> None:
    """Look up from below the model — feet face the camera, anterior (+X) is up."""
    camera = renderer.GetActiveCamera()
    distance = camera.GetDistance()
    cx, cy, cz = camera.GetFocalPoint()
    camera.SetPosition(cx, cy - distance, cz)
    camera.SetFocalPoint(cx, cy, cz)
    camera.SetViewUp(1, 0, 0)
    camera.SetParallelProjection(True)


def perspective_45_camera(renderer: vtk.vtkRenderer) -> None:
    """45 deg azimuth (front-right diagonal) and 45 deg elevation, perspective."""
    camera = renderer.GetActiveCamera()
    distance = camera.GetDistance()
    cx, cy, cz = camera.GetFocalPoint()
    # 45 deg in XZ plane, 45 deg elevation
    h = math.cos(math.radians(45)) * distance   # horizontal reach
    dx = math.sin(math.radians(45)) * h          # anterior component
    dz = math.cos(math.radians(45)) * h          # lateral component
    dy = math.sin(math.radians(45)) * distance   # vertical component
    camera.SetPosition(cx + dx, cy + dy, cz + dz)
    camera.SetFocalPoint(cx, cy, cz)
    camera.SetViewUp(0, 1, 0)
    camera.SetParallelProjection(False)
    camera.SetViewAngle(30)


if __name__ == "__main__":
    views = [
        ("renders/chimp_may2025_muscles_frontal_hq.png",    frontal_camera),
        ("renders/chimp_may2025_muscles_sagittal_hq.png",   sagittal_camera),
        ("renders/chimp_may2025_muscles_feet_hq.png",       transverse_feet_camera),
        ("renders/chimp_may2025_muscles_perspective_hq.png", perspective_45_camera),
    ]

    for path_str, cam_fn in views:
        render_view(Path(path_str), cam_fn)

    # Compose 2x2 grid: [frontal | sagittal] / [feet | perspective]
    # Crop each panel to its content bounding box before compositing.
    GAP = 40  # pixels between panels
    images = [Image.open(p).crop(Image.open(p).getbbox()) for p, _ in views]
    col_w = max(img.width  for img in images)
    col_h = max(img.height for img in images)
    total_w = col_w * 2 + GAP
    total_h = col_h * 2 + GAP
    composite = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    grid_positions = [(0, 0), (col_w + GAP, 0), (0, col_h + GAP), (col_w + GAP, col_h + GAP)]
    for img, (gx, gy) in zip(images, grid_positions, strict=False):
        # Center each panel within its cell
        ox = (col_w - img.width)  // 2
        oy = (col_h - img.height) // 2
        composite.paste(img, (gx + ox, gy + oy), img)

    out = Path("renders/chimp_may2025_muscles_2x2.png")
    composite.save(out)
    print(f"Saved {out}")
