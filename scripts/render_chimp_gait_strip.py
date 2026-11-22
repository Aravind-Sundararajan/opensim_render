"""Render a sagittal-plane gait strip (0%, 25%, 50%, 75%, 100% of the cycle)
for the chimp fullbody muscle-tracking simulation.

Muscles are colored by activation level at each frame (dark = inactive,
bright red = fully active).

Usage:
    C:\\Users\\asundar4\\.conda\\envs\\osim-render\\python.exe scripts/render_chimp_gait_strip.py
"""

import math
from pathlib import Path

import opensim
from PIL import Image

from osim_render.api.animation.animation import AnimationState
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.loaders.motion_loader import MotionLoader
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager

SIM_DIR = Path(
    r"F:\dev\projects\gait_sim\output\muscle\chimp_fullbody\EMG\Tracking_wEMG_w0_june2026\met"
)
MODEL_PATH = Path(r"F:\dev\projects\gait_sim\models\chimp_fullbody\model_May2025.osim")
MOTION_PATH = SIM_DIR / "states.sto"
OUTPUT_PATH = Path("renders/chimp_gait_strip_sagittal.png")
PANEL_RESOLUTION = (900, 1300)
FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
ZOOM_FACTOR = 2.0       # >1 zooms in, making the model larger within each panel
PANEL_OVERLAP_PX = 320  # pixels each successive panel overlaps the previous one

# The gait sim tracks the lower body only, so the arms hold whatever pose the
# motion (or model default) leaves them in. Force the elbows to the chimp's
# standard ~15 deg of flexion for a natural-looking arm carriage.
ELBOW_FLEX_RAD = math.radians(15.0)

# Activation color ramp: 0 = blue, 1 = red
INACTIVE_COLOR = (0.0, 0.2, 1.0)   # blue
ACTIVE_COLOR   = (1.0, 0.0, 0.0)   # red


def activation_color(activation: float) -> tuple[float, float, float]:
    t = max(0.0, min(1.0, activation))
    r = INACTIVE_COLOR[0] + t * (ACTIVE_COLOR[0] - INACTIVE_COLOR[0])
    g = INACTIVE_COLOR[1] + t * (ACTIVE_COLOR[1] - INACTIVE_COLOR[1])
    b = INACTIVE_COLOR[2] + t * (ACTIVE_COLOR[2] - INACTIVE_COLOR[2])
    return (r, g, b)


# --- Load activations directly from states.sto via TimeSeriesTable ---
# MotionLoader only keeps /value columns; activations live under
# /forceset/<muscle>/activation which we parse here.
def load_activations(
    sto_path: Path,
) -> tuple[list[float], dict[str, list[float]]]:
    """Return (times, {muscle_name: [activation_per_frame]})."""
    table = opensim.TimeSeriesTable(str(sto_path))
    times = list(table.getIndependentColumn())
    labels = list(table.getColumnLabels())

    # Identify activation columns: /forceset/<muscle>/activation
    act_cols: list[tuple[int, str]] = []  # (col_index, muscle_name)
    for j, label in enumerate(labels):
        parts = label.split("/")
        if label.startswith("/") and len(parts) >= 4 and parts[-1] == "activation":
            muscle_name = parts[-2]
            act_cols.append((j, muscle_name))

    muscle_activations: dict[str, list[float]] = {name: [] for _, name in act_cols}
    for i in range(table.getNumRows()):
        row = table.getRowAtIndex(i)
        for j, muscle_name in act_cols:
            muscle_activations[muscle_name].append(row[j])

    return times, muscle_activations


def get_activations_at_time(
    times: list[float],
    muscle_activations: dict[str, list[float]],
    target_time: float,
) -> dict[str, float]:
    """Return {muscle_name: activation} for the nearest frame to target_time."""
    idx = min(range(len(times)), key=lambda i: abs(times[i] - target_time))
    return {name: vals[idx] for name, vals in muscle_activations.items()}


# ---------------------------------------------------------------------------
print("Loading activations...")
times, muscle_activations = load_activations(MOTION_PATH)
print(f"  {len(muscle_activations)} muscles, {len(times)} frames")

event_bus = EventBus()
model_manager = ModelManager(event_bus)
model_manager.load_model(MODEL_PATH)

motion_loader = MotionLoader()
motion_data = motion_loader.load(MOTION_PATH, model_manager.get_opensim_model())

offscreen = OffscreenRenderer(resolution=PANEL_RESOLUTION, transparent_background=True)
scene_manager = SceneManager(model_manager, MODEL_PATH)
scene = scene_manager.create_scene(renderer=offscreen.renderer)

muscle_actors = scene.muscle_actors
if muscle_actors is None:
    raise SystemExit("Scene has no muscle actors to render")

for muscle_actor in muscle_actors.values():
    muscle_actor.SetVisibility(True)

renderer = offscreen.renderer
model = model_manager.get_opensim_model()
state = model_manager.get_opensim_state()
if model is None or state is None:
    raise SystemExit(f"Model failed to load from {MODEL_PATH}")
camera = renderer.GetActiveCamera()

duration = motion_data.end_time - motion_data.start_time
panels: list[Image.Image] = []
camera_distance: float | None = None
focal_y: float | None = None
focal_z: float | None = None

for fraction in FRACTIONS:
    target_time = motion_data.start_time + fraction * duration
    frame = motion_loader.get_frame_at_time(motion_data, target_time)
    coordinate_values = {
        **frame.coordinate_values,
        "elbow_flex_r": ELBOW_FLEX_RAD,
        "elbow_flex_l": ELBOW_FLEX_RAD,
    }
    anim_state = AnimationState(
        time=frame.time,
        coordinate_values=coordinate_values,
        camera_state=None,
        actor_properties={},
    )
    scene_manager.update_frame(anim_state)

    # Color each muscle actor by its activation level at this frame
    activations = get_activations_at_time(times, muscle_activations, frame.time)
    for muscle_name, muscle_actor in muscle_actors.items():
        act = activations.get(muscle_name, 0.0)
        muscle_actor.GetProperty().SetColor(*activation_color(act))

    pelvis_pos = model.getBodySet().get("pelvis").getPositionInGround(state)
    pelvis_x = pelvis_pos.get(0)

    if camera_distance is None:
        renderer.ResetCamera()
        camera.Zoom(ZOOM_FACTOR)
        camera_distance = camera.GetDistance()
        focal_point = camera.GetFocalPoint()
        focal_y, focal_z = focal_point[1], focal_point[2]
        camera.SetViewUp(0, 1, 0)
        camera.SetParallelProjection(True)

    assert focal_y is not None and focal_z is not None
    camera.SetFocalPoint(pelvis_x, focal_y, focal_z)
    camera.SetPosition(pelvis_x, focal_y, focal_z + camera_distance)
    renderer.ResetCameraClippingRange()

    image = offscreen.render_frame(anim_state)
    panels.append(Image.fromarray(image, "RGBA"))

panel_w = panels[0].width
stride = panel_w - PANEL_OVERLAP_PX
strip_width = panel_w + stride * (len(panels) - 1)
strip_height = max(panel.height for panel in panels)
strip = Image.new("RGBA", (strip_width, strip_height), (0, 0, 0, 0))

for i, panel in enumerate(panels):
    strip.paste(panel, (i * stride, 0), panel)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
strip.save(OUTPUT_PATH)
print(f"Saved {OUTPUT_PATH}")
