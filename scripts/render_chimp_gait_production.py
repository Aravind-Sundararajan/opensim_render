"""Production multi-view render of the chimp fullbody muscle-tracking gait cycle.

The camera slerps between three viewpoints, holding ~2 gait cycles at each:
    sagittal (side)  ->  frontal (anterior)  ->  isometric 3/4
Muscles are colored by their per-frame activation (cool blue = inactive,
hot red = fully active) read from states.sto, and the ground-reaction contact-
force arrows fade in and out with each foot's stance phase.

Design notes:
  - one continuous animation: the ~0.8s cycle is looped CYCLES_PER_VIEW * 3
    times; every frame gets a fresh camera + activation colors + force opacity
  - the camera focal point tracks the pelvis so the chimp stays centered in all
    views and the periodic loop reads as continuous walking
  - camera transitions are great-circle (slerp) interpolations of the view
    direction with smoothstep easing, centered on the 2-cycle boundaries
  - force arrows are recolored white (the activation ramp already owns red) and
    their opacity is eased toward each foot's stance signal for a soft fade

Usage:
    C:\\Users\\asundar4\\.conda\\envs\\osim-render\\python.exe scripts/render_chimp_gait_production.py
"""

import math
from pathlib import Path

import imageio
import opensim
import vtkmodules.all as vtk

from osim_render.api.animation.animation import AnimationState
from osim_render.api.loaders.motion_loader import MotionLoader
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.rendering.scene import SceneManager

SIM_DIR = Path(
    r"F:\dev\projects\gait_sim\output\muscle\chimp_fullbody\EMG\Tracking_wEMG_w0_june2026\met"
)
MODEL_PATH = Path(r"F:\dev\projects\gait_sim\models\chimp_fullbody\model_May2025.osim")
MOTION_PATH = SIM_DIR / "states.sto"
OUTPUT_PATH = Path("renders/chimp_gait_production_multiview.mp4")

RESOLUTION = (1600, 1600)   # square suits sagittal, frontal and iso equally
FPS = 30
TIME_SCALE = 0.3            # slow-motion: ~0.8s cycle -> ~2.7s
CYCLES_PER_VIEW = 2
FILL_FRACTION = 0.92        # chimp fills this fraction of the frame's half-extent
TRANSITION_CYCLES = 0.6     # slerp window (in cycles) centered on view changes

# Bone tone keeps the activation coloring the visual focus.
BONE_COLOR = (0.86, 0.82, 0.74)
# Force arrows are white so they never read as "high activation" (ramp red).
FORCE_COLOR = (0.97, 0.97, 1.0)
FORCE_FADE_ALPHA = 0.25     # per-frame easing toward the stance on/off target

# Arms are not tracked by the lower-body sim; hold the chimp's standard elbow
# flexion (~15 deg) for a natural carriage.
ELBOW_FLEX_RAD = math.radians(15.0)

# The shoulders are untracked too, so drive a procedural arm counter-swing off
# the pelvis's axial rotation (transverse plane). In this sim pelvis_rotation is
# anti-phase to the ipsilateral leg (its minimum ~= right-leg-back), so each arm
# swings forward when its own leg swings back -> arm swing OUT OF PHASE with the
# legs, per Thompson, O'Neill et al. 2015 (Nat Commun 6:8416), where trunk
# rotation functions to "facilitate arm swing out of phase with the legs".
ARM_SWING_GAIN = 1.8               # arm_flex per rad of pelvis_rotation
ARM_FLEX_BIAS = math.radians(5.0)  # slight forward carriage off the dead-hang
ARM_ADD_RAD = math.radians(-12.0)  # shoulder abduction, arms held wide of the legs

# IDEALIZATION (not the sim's actual kinematics): the tracking sim's thorax
# counter-rotates the pelvis (human-like, ~0.46 ratio, out of phase). Thompson &
# O'Neill 2015 report chimps rotate the thorax IN-PHASE with the pelvis
# (26.9 deg / 42.8 deg = 0.63 ratio). Since thorax_abs ~= pelvis_rotation +
# lumbar_rotation, overriding lumbar_rotation = (ratio-1)*pelvis_rotation forces
# the absolute thorax in-phase at that ratio. Toggle off for the faithful sim.
FORCE_TRUNK_INPHASE = True
THORAX_PELVIS_RATIO = 0.63

# The sim's lumbar_bending (frontal plane) bends the trunk IN the direction of
# the pelvic list, so the absolute thorax leans ~2x the pelvis (+/-13.7 vs +/-7.1
# deg) -- an over-exaggerated side-to-side sway. Damp it so the thorax lean
# stays nearer the pelvis rather than amplifying it.
LUMBAR_BENDING_SCALE = 0.4

# Camera view directions (unit vectors from focal point to camera). Model axes:
# X = anterior/walking, Y = up, Z = lateral. The isometric corner (1,1,1)/sqrt3
# is az 45 deg / el 35.26 deg.
_ISO = 1.0 / math.sqrt(3.0)
VIEWS: tuple[tuple[str, tuple[float, float, float]], ...] = (
    ("Sagittal", (0.0, 0.0, 1.0)),
    ("Frontal", (1.0, 0.0, 0.0)),
    ("Isometric", (_ISO, _ISO, _ISO)),
)


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def slerp(
    a: tuple[float, float, float], b: tuple[float, float, float], t: float
) -> tuple[float, float, float]:
    """Great-circle interpolation between two unit direction vectors."""
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))
    if dot > 0.9995:  # nearly colinear: linear interp + renormalize
        v = tuple(a[i] + t * (b[i] - a[i]) for i in range(3))
    else:
        omega = math.acos(dot)
        so = math.sin(omega)
        wa = math.sin((1.0 - t) * omega) / so
        wb = math.sin(t * omega) / so
        v = tuple(wa * a[i] + wb * b[i] for i in range(3))
    length = math.sqrt(sum(c * c for c in v))
    return (v[0] / length, v[1] / length, v[2] / length)


def blended_view(cycle_pos: float) -> tuple[str, tuple[float, float, float]]:
    """Label + slerped camera direction at a given cycle position (0..3*CPV)."""
    half = TRANSITION_CYCLES / 2.0
    for i in range(len(VIEWS) - 1):
        boundary = (i + 1) * CYCLES_PER_VIEW
        if cycle_pos < boundary - half:
            return VIEWS[i][0], VIEWS[i][1]
        if cycle_pos < boundary + half:
            t = smoothstep((cycle_pos - (boundary - half)) / TRANSITION_CYCLES)
            label = VIEWS[i][0] if t < 0.5 else VIEWS[i + 1][0]
            return label, slerp(VIEWS[i][1], VIEWS[i + 1][1], t)
    return VIEWS[-1][0], VIEWS[-1][1]


def union_bounds(actors: list[vtk.vtkActor]) -> tuple[float, ...] | None:
    """Axis-aligned union of the given actors' current world bounds, or None."""
    lo = [math.inf, math.inf, math.inf]
    hi = [-math.inf, -math.inf, -math.inf]
    found = False
    for actor in actors:
        if not actor.GetVisibility():
            continue
        b = actor.GetBounds()  # (xmin, xmax, ymin, ymax, zmin, zmax)
        if b[0] > b[1]:
            continue  # invalid/empty bounds
        found = True
        for k in range(3):
            lo[k] = min(lo[k], b[2 * k])
            hi[k] = max(hi[k], b[2 * k + 1])
    if not found:
        return None
    return (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])


def pose_coordinates(frame: object) -> dict[str, float]:
    """Coordinate values for a motion frame plus the procedural arm pose.

    The elbows hold a fixed flexion and the shoulders counter-swing off the
    pelvis's axial rotation (opposite sign per arm), so the arm swing stays
    phase-locked to the gait without a hand-tuned sinusoid.
    """
    coords: dict[str, float] = dict(frame.coordinate_values)  # type: ignore[attr-defined]
    pelvis_rot = coords.get("pelvis_rotation", 0.0)
    if FORCE_TRUNK_INPHASE:
        # thorax_abs = pelvis_rotation + lumbar_rotation -> set lumbar so the
        # absolute thorax rotates in-phase with the pelvis at THORAX_PELVIS_RATIO.
        coords["lumbar_rotation"] = (THORAX_PELVIS_RATIO - 1.0) * pelvis_rot
    coords["lumbar_bending"] = LUMBAR_BENDING_SCALE * coords.get("lumbar_bending", 0.0)
    swing = ARM_SWING_GAIN * pelvis_rot
    coords["elbow_flex_r"] = ELBOW_FLEX_RAD
    coords["elbow_flex_l"] = ELBOW_FLEX_RAD
    # Minus on the right: pelvis_rotation is anti-phase to the ipsilateral leg,
    # so -swing puts the right arm forward when the right leg is back.
    coords["arm_flex_r"] = ARM_FLEX_BIAS - swing
    coords["arm_flex_l"] = ARM_FLEX_BIAS + swing
    coords["arm_add_r"] = ARM_ADD_RAD
    coords["arm_add_l"] = ARM_ADD_RAD
    return coords


def build_activation_lut() -> vtk.vtkColorTransferFunction:
    lut = vtk.vtkColorTransferFunction()
    lut.AddRGBPoint(0.0, 0.10, 0.20, 0.65)   # inactive: deep blue
    lut.AddRGBPoint(0.25, 0.10, 0.65, 0.85)  # cyan
    lut.AddRGBPoint(0.50, 0.95, 0.85, 0.20)  # yellow
    lut.AddRGBPoint(0.75, 0.95, 0.45, 0.10)  # orange
    lut.AddRGBPoint(1.0, 0.90, 0.10, 0.10)   # fully active: hot red
    return lut


def load_activations(sto_path: Path) -> tuple[list[float], dict[str, list[float]]]:
    """Return (times, {muscle_name: [activation_per_frame]}) from states.sto.

    MotionLoader keeps only /value columns, so activations under
    /forceset/<muscle>/activation are parsed directly here.
    """
    table = opensim.TimeSeriesTable(str(sto_path))
    times = list(table.getIndependentColumn())
    labels = list(table.getColumnLabels())

    act_cols: list[tuple[int, str]] = []
    for j, label in enumerate(labels):
        parts = label.split("/")
        if label.startswith("/") and len(parts) >= 4 and parts[-1] == "activation":
            act_cols.append((j, parts[-2]))

    muscle_activations: dict[str, list[float]] = {name: [] for _, name in act_cols}
    for i in range(table.getNumRows()):
        row = table.getRowAtIndex(i)
        for j, name in act_cols:
            muscle_activations[name].append(row[j])

    return times, muscle_activations


def activation_at_time(
    times: list[float],
    muscle_activations: dict[str, list[float]],
    target_time: float,
) -> dict[str, float]:
    idx = min(range(len(times)), key=lambda i: abs(times[i] - target_time))
    return {name: vals[idx] for name, vals in muscle_activations.items()}


def add_three_point_lighting(renderer: vtk.vtkRenderer) -> None:
    """Camera-relative key/fill/back lights so illumination is view-consistent."""
    renderer.RemoveAllLights()
    for azimuth, elevation, intensity in (
        (-35.0, 25.0, 1.0),   # key
        (35.0, 10.0, 0.5),    # fill
        (0.0, -40.0, 0.4),    # back/rim
    ):
        light = vtk.vtkLight()
        light.SetLightTypeToCameraLight()
        light.SetPosition(
            math.sin(math.radians(azimuth)) * math.cos(math.radians(elevation)),
            math.sin(math.radians(elevation)),
            math.cos(math.radians(azimuth)) * math.cos(math.radians(elevation)),
        )
        light.SetFocalPoint(0.0, 0.0, 0.0)
        light.SetIntensity(intensity)
        renderer.AddLight(light)


def make_color_bar(lut: vtk.vtkColorTransferFunction) -> vtk.vtkScalarBarActor:
    bar = vtk.vtkScalarBarActor()
    bar.SetLookupTable(lut)
    bar.SetTitle("Muscle\nactivation")
    bar.SetNumberOfLabels(3)
    bar.SetMaximumWidthInPixels(80)
    bar.SetMaximumHeightInPixels(420)
    bar.GetPositionCoordinate().SetValue(0.04, 0.10)
    bar.SetTextPositionToSucceedScalarBar()
    for prop in (bar.GetTitleTextProperty(), bar.GetLabelTextProperty()):
        prop.SetColor(0.95, 0.95, 0.95)
        prop.SetFontFamilyToArial()
        prop.ShadowOff()
    bar.GetTitleTextProperty().SetFontSize(26)
    bar.GetLabelTextProperty().SetFontSize(20)
    return bar


def make_caption() -> vtk.vtkTextActor:
    text = vtk.vtkTextActor()
    prop = text.GetTextProperty()
    prop.SetFontFamilyToArial()
    prop.SetFontSize(32)
    prop.SetColor(0.95, 0.95, 0.95)
    prop.ShadowOn()
    text.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
    text.SetPosition(0.04, 0.95)
    return text


def main() -> None:
    print("Loading activations...")
    times, muscle_activations = load_activations(MOTION_PATH)
    print(f"  {len(muscle_activations)} muscles, {len(times)} frames")

    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    model_manager.load_model(MODEL_PATH)

    motion_loader = MotionLoader()
    motion_data = motion_loader.load(MOTION_PATH, model_manager.get_opensim_model())

    offscreen = OffscreenRenderer(resolution=RESOLUTION, background_color=(0.06, 0.07, 0.10))
    renderer = offscreen.renderer
    renderer.SetBackground(0.03, 0.04, 0.06)
    renderer.SetBackground2(0.12, 0.14, 0.20)
    renderer.GradientBackgroundOn()
    offscreen.render_window.SetMultiSamples(8)
    renderer.SetUseFXAA(True)

    scene_manager = SceneManager(model_manager, MODEL_PATH)
    scene = scene_manager.create_scene(renderer=renderer)

    for actor in scene.actors.values():
        actor.GetProperty().SetColor(*BONE_COLOR)

    muscle_actors = scene.muscle_actors
    if muscle_actors is None:
        raise SystemExit("Scene has no muscle actors to render")
    for muscle_actor in muscle_actors.values():
        muscle_actor.SetVisibility(True)
        muscle_actor.GetProperty().SetSpecular(0.3)
        muscle_actor.GetProperty().SetSpecularPower(15)

    force_actors = scene.contact_force_actors or {}
    for force_actor in force_actors.values():
        force_actor.GetProperty().SetColor(*FORCE_COLOR)
    force_opacity: dict[str, float] = {name: 0.0 for name in force_actors}
    print(f"  {len(force_actors)} contact-force arrows")

    lut = build_activation_lut()
    add_three_point_lighting(renderer)
    renderer.AddViewProp(make_color_bar(lut))
    caption = make_caption()
    renderer.AddViewProp(caption)

    model = model_manager.get_opensim_model()
    state = model_manager.get_opensim_state()
    if model is None or state is None:
        raise SystemExit(f"Model failed to load from {MODEL_PATH}")
    camera = renderer.GetActiveCamera()

    duration = motion_data.end_time - motion_data.start_time
    frames_per_cycle = round(FPS * duration / TIME_SCALE)
    total_cycles = CYCLES_PER_VIEW * len(VIEWS)
    total_frames = frames_per_cycle * total_cycles

    # --- Framing pre-pass ---------------------------------------------------
    # Fit ONE parallel scale that keeps the chimp fully in-frame for every pose
    # and every view. Bounds are measured relative to the pelvis (so the forward
    # walking translation never inflates them) using only bone+muscle actors
    # (the force arrows scale with load and would otherwise skew the fit). The
    # pelvis-relative bounding-sphere radius fits any view direction.
    frame_actors = list(scene.actors.values()) + list(muscle_actors.values())
    focal_y = focal_z = 0.0
    radius = 0.0
    FRAMING_SAMPLES = 24
    for s in range(FRAMING_SAMPLES):
        phase = s / FRAMING_SAMPLES
        mt = motion_data.start_time + phase * duration
        fr = motion_loader.get_frame_at_time(motion_data, mt)
        scene_manager.update_frame(
            AnimationState(
                time=mt,
                coordinate_values=pose_coordinates(fr),
                camera_state=None,
                actor_properties={},
            )
        )
        bounds = union_bounds(frame_actors)
        if bounds is None:
            continue
        px = model.getBodySet().get("pelvis").getPositionInGround(state).get(0)
        if s == 0:
            focal_y = (bounds[2] + bounds[3]) / 2.0
            focal_z = (bounds[4] + bounds[5]) / 2.0
        dx = max(bounds[1] - px, px - bounds[0])
        dy = max(bounds[3] - focal_y, focal_y - bounds[2])
        dz = max(bounds[5] - focal_z, focal_z - bounds[4])
        radius = max(radius, math.sqrt(dx * dx + dy * dy + dz * dz))

    parallel_scale = radius / FILL_FRACTION
    cam_distance = 4.0 * radius  # well outside the model; clipping reset per frame
    camera.SetParallelProjection(True)
    camera.SetParallelScale(parallel_scale)
    camera.SetViewUp(0, 1, 0)
    print(f"  framing: radius={radius:.3f} m  parallel_scale={parallel_scale:.3f}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Rendering {total_frames} frames ({total_cycles} cycles)...")
    with imageio.get_writer(
        str(OUTPUT_PATH),
        fps=FPS,
        codec="libx264",
        quality=None,
        output_params=["-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p"],
    ) as writer:
        for frame_num in range(total_frames):
            cycle_pos = frame_num / frames_per_cycle
            cycle_phase = cycle_pos % 1.0
            motion_time = motion_data.start_time + cycle_phase * duration

            frame = motion_loader.get_frame_at_time(motion_data, motion_time)
            posed = AnimationState(
                time=motion_time,
                coordinate_values=pose_coordinates(frame),
                camera_state=None,
                actor_properties={},
            )
            scene_manager.update_frame(posed)

            # Muscle color by activation at this instant in the cycle.
            activations = activation_at_time(times, muscle_activations, motion_time)
            for muscle_name, muscle_actor in muscle_actors.items():
                act = max(0.0, min(1.0, activations.get(muscle_name, 0.0)))
                muscle_actor.GetProperty().SetColor(*lut.GetColor(act))

            # Fade force arrows toward each foot's stance signal (update_frame
            # has set visibility True only where the force is active this frame).
            for name, force_actor in force_actors.items():
                target = 1.0 if force_actor.GetVisibility() else 0.0
                op = force_opacity[name] + (target - force_opacity[name]) * FORCE_FADE_ALPHA
                force_opacity[name] = op
                force_actor.GetProperty().SetOpacity(op)
                force_actor.SetVisibility(op > 0.01)

            pelvis_x = model.getBodySet().get("pelvis").getPositionInGround(state).get(0)

            # Fixed parallel scale (from the framing pre-pass); only the focal
            # point tracks the pelvis and the view direction slerps.
            label, direction = blended_view(cycle_pos)
            focal = (pelvis_x, focal_y, focal_z)
            camera.SetFocalPoint(*focal)
            camera.SetPosition(
                focal[0] + direction[0] * cam_distance,
                focal[1] + direction[1] * cam_distance,
                focal[2] + direction[2] * cam_distance,
            )
            camera.SetViewUp(0, 1, 0)
            renderer.ResetCameraClippingRange()

            caption.SetInput(f"Chimpanzee gait  -  {label}    {cycle_phase * 100:4.0f}%")

            writer.append_data(offscreen.render_frame(posed))
            if (frame_num + 1) % 20 == 0 or frame_num + 1 == total_frames:
                print(f"  frame {frame_num + 1}/{total_frames}  ({label})")

    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
