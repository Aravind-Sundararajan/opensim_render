"""
Render all animation scripts to video files.

Usage:
    poetry run python scripts/render_animation_scripts.py --model path/to/model.osim
    poetry run python scripts/render_animation_scripts.py --model model.osim -g /path/to/geometry
    poetry run python scripts/render_animation_scripts.py --model model.osim --output-dir renders/
    poetry run python scripts/render_animation_scripts.py --model model.osim --scripts 05_walking 06_running
    poetry run python scripts/render_animation_scripts.py --model model.osim --fps 30 --resolution 1920 1080
"""

from osim_render.api.logging.logger import get_logger_for
from osim_render.api.rendering.video_exporter import VideoExporter, VideoExportConfig
from osim_render.api.rendering.scene import SceneManager
from osim_render.api.rendering.offscreen_renderer import OffscreenRenderer
from osim_render.api.animation.script_executor import ScriptExecutor
from osim_render.api.managers.model_manager import ModelManager
from osim_render.api.managers.event_bus import EventBus
from vtkmodules.vtkRenderingCore import vtkRenderer
import argparse
import sys
from pathlib import Path

logger = get_logger_for(__name__)

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


def build_scene_manager(
    model_manager: ModelManager,
    model_path: Path,
    geometry_paths: list[Path],
    renderer: "vtkRenderer",
) -> SceneManager:
    geometry_strs = tuple(str(p)
                          for p in geometry_paths) if geometry_paths else None
    scene_manager = SceneManager(model_manager, model_path, geometry_strs)
    scene_manager.create_scene(renderer=renderer)
    return scene_manager


def render_script(
    script_path: Path,
    model_manager: ModelManager,
    model_path: Path,
    geometry_paths: list[Path],
    output_dir: Path,
    fps: int,
    resolution: tuple[int, int],
    quality: str,
    playback_speed: float = 1.0,
) -> Path:
    event_bus = EventBus()

    offscreen = OffscreenRenderer(
        resolution=resolution, background_color=(0.2, 0.2, 0.2))
    scene_manager = build_scene_manager(
        model_manager, model_path, geometry_paths, offscreen.renderer)

    executor = ScriptExecutor(
        model_manager, scene_manager, event_bus, time_scale=playback_speed)
    code = script_path.read_text(encoding="utf-8")
    result = executor.execute(code, script_name=script_path.name)

    output_file = output_dir / f"{script_path.stem}.mp4"
    config = VideoExportConfig(
        output_file=output_file,
        resolution=resolution,
        fps=fps,
        quality=quality,
    )

    total_frames = [0]

    def progress(current: int, total: int) -> None:
        total_frames[0] = total
        pct = int(100 * current / total) if total else 100
        print(f"  {pct:3d}% [{current}/{total}]", end="\r")

    assert result.timeline is not None, "executor.execute() must return a timeline"
    exporter = VideoExporter(scene_manager, config, renderer=offscreen)
    export = exporter.export_timeline(
        result.timeline, progress_callback=progress)

    print(f"  100% [{export.frame_count}/{export.frame_count}]")
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render animation scripts to video")
    parser.add_argument(
        "--model",
        type=Path,
        required=True,
        help="Path to OpenSim model file (.osim)",
    )
    parser.add_argument(
        "-g",
        "--geometry-path",
        type=Path,
        dest="geometry_paths",
        action="append",
        default=[],
        help="Geometry search directory (can be used multiple times)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "renders",
        help="Directory to write MP4 files (default: renders/)",
    )
    parser.add_argument("--fps", type=int, default=30,
                        help="Frames per second (default: 30)")
    parser.add_argument(
        "--resolution",
        type=int,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=[1280, 720],
        help="Output resolution (default: 1280 720)",
    )
    parser.add_argument(
        "--quality",
        choices=["high", "medium", "low"],
        default="medium",
        help="Video quality (default: medium)",
    )
    parser.add_argument(
        "--playback-speed",
        type=float,
        default=1.0,
        dest="playback_speed",
        help="Playback speed multiplier (default: 1.0, e.g. 2.0 = 2x faster, 0.5 = half speed)",
    )
    parser.add_argument(
        "--scripts",
        nargs="+",
        metavar="NAME",
        help="Only render scripts whose filename contains NAME (e.g. 05_walking V01)",
    )
    args = parser.parse_args()

    if not args.model.exists():
        print(f"ERROR: Model file not found: {args.model}")
        sys.exit(1)

    scripts_dir = REPO_ROOT / "animation_scripts"
    all_scripts = sorted(p for p in scripts_dir.glob("*.py"))

    if args.scripts:
        scripts = [p for p in all_scripts if any(
            s in p.name for s in args.scripts)]
        if not scripts:
            print(f"No scripts matched: {args.scripts}")
            sys.exit(1)
    else:
        scripts = all_scripts

    args.output_dir.mkdir(parents=True, exist_ok=True)
    resolution: tuple[int, int] = (args.resolution[0], args.resolution[1])

    print(f"Model: {args.model}")
    if args.geometry_paths:
        print(f"Geometry paths: {[str(p) for p in args.geometry_paths]}")
    print(f"Rendering {len(scripts)} script(s) -> {args.output_dir}/")
    print(
        f"Settings: {resolution[0]}x{resolution[1]} @ {args.fps}fps, quality={args.quality}")
    print()

    # Load model once — shared across all scripts
    event_bus = EventBus()
    model_manager = ModelManager(event_bus)
    print("Loading model...")
    model_manager.load_model(args.model)
    print("Model loaded.\n")

    failed = []
    for i, script_path in enumerate(scripts, 1):
        print(f"[{i}/{len(scripts)}] {script_path.name}")
        try:
            output_file = render_script(
                script_path,
                model_manager=model_manager,
                model_path=args.model,
                geometry_paths=args.geometry_paths,
                output_dir=args.output_dir,
                fps=args.fps,
                resolution=resolution,
                quality=args.quality,
                playback_speed=args.playback_speed,
            )
            size_kb = output_file.stat().st_size // 1024
            print(f"  -> {output_file.name} ({size_kb} KB)")
        except Exception as e:
            print(f"  FAILED: {e}")
            failed.append(script_path.name)
        print()

    print(f"Done. {len(scripts) - len(failed)}/{len(scripts)} succeeded.")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
