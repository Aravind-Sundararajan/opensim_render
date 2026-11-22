"""
Script executor for creating animations via Python code.

Provides a safe execution environment for user scripts that create animations
using the manim-style Scene API.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any, Optional
from contextlib import redirect_stdout, redirect_stderr

from osim_render.api.animation.animation import ParallelAnimation
from osim_render.api.animation.scene import Scene
from osim_render.api.animation.timeline import Timeline

if TYPE_CHECKING:
    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.rendering.scene import SceneManager
    from osim_render.api.managers.event_bus import EventBus
    from osim_render.api.managers.visualization_state_manager import VisualizationStateManager
    from osim_render.api.loaders.motion_loader import MotionData


class ScriptExecutionResult:
    """Result of executing an animation script."""

    success: bool
    timeline: Optional[Timeline]
    output: str
    error: str

    def __init__(
        self,
        success: bool,
        timeline: Optional[Timeline] = None,
        output: str = "",
        error: str = "",
    ):
        """Initialize execution result."""
        self.success = success
        self.timeline = timeline
        self.output = output
        self.error = error


class ScriptExecutor:
    """Executes Python scripts that create animations.

    Provides a safe namespace with the Scene API and utility functions
    for users to create complex animations programmatically.

    Attributes:
        model_manager: Manager for OpenSim model access
        scene_manager: Manager for scene rendering
        event_bus: Event bus for publishing events
    """

    def __init__(
        self,
        model_manager: ModelManager,
        scene_manager: Optional[SceneManager],
        event_bus: EventBus,
        motion_data: Optional[MotionData] = None,
        vis_state_manager: Optional[VisualizationStateManager] = None,
        time_scale: float = 1.0,
    ):
        """Initialize script executor.

        Args:
            model_manager: Manager providing access to OpenSim model
            scene_manager: Manager for rendering and visualization, or None
            event_bus: Event system for publishing events
            motion_data: Optional loaded motion data for scripts to use
            vis_state_manager: Optional visualization state manager for property control
            time_scale: Multiplier applied to all animation durations (default 1.0)
        """
        self.model_manager = model_manager
        self.scene_manager = scene_manager
        self.event_bus = event_bus
        self.motion_data = motion_data
        self.vis_state_manager = vis_state_manager
        self.time_scale = time_scale

    def execute(
        self, code: str, script_name: str = "animation"
    ) -> ScriptExecutionResult:
        """Execute a Python script that creates an animation.

        Args:
            code: Python code as string
            script_name: Name for the script (for context)

        Returns:
            ScriptExecutionResult with timeline and output

        Raises:
            SyntaxError: If code has syntax errors
            RuntimeError: If code execution fails
            ValueError: If script does not create a timeline
        """
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        namespace = self._create_namespace()

        # Execute code in the namespace - let exceptions propagate
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, namespace)

        timeline = namespace.get("timeline")

        if timeline is None:
            raise ValueError(
                "Script did not create a timeline. "
                "Use 'timeline = scene.build_timeline()' at the end."
            )

        # Success!
        return ScriptExecutionResult(
            success=True,
            timeline=timeline,
            output=stdout_capture.getvalue(),
        )

    def _create_namespace(self) -> dict[str, Any]:
        """Create namespace with API functions for scripts.

        Returns:
            Dictionary with functions and classes available to scripts
        """
        import functools
        SceneClass = functools.partial(
            Scene, time_scale=self.time_scale) if self.time_scale != 1.0 else Scene

        namespace = {
            # Import the Scene class
            "Scene": SceneClass,
            "Timeline": Timeline,
            "ParallelAnimation": ParallelAnimation,
            "create_scene": self._create_scene,
            # Utility functions
            "print": print,
            # Access to managers for advanced usage
            "model_manager": self.model_manager,
            "scene_manager": self.scene_manager,
            "event_bus": self.event_bus,
            # Motion data access (if available)
            "motion_data": self.motion_data,
            # Helper functions for motion data
            "load_motion_from_file": self._load_motion_from_file,
            "create_animation_from_motion": self._create_animation_from_motion,
        }
        return namespace

    def _create_scene(self) -> Scene:
        """Create a Scene object in the script context.

        Returns:
            Scene ready for animation composition
        """
        property_manager = None
        if self.vis_state_manager is not None and self.scene_manager is not None:
            from osim_render.api.managers.property_control_manager import (
                PropertyControlManager,
            )

            property_manager = PropertyControlManager(
                self.scene_manager,
                self.vis_state_manager,
                self.event_bus,
            )

        scene = Scene(
            self.model_manager,
            self.scene_manager,
            self.event_bus,
            property_manager=property_manager,
        )
        return scene

    def _load_motion_from_file(self, filepath: str) -> Any:
        """Load motion data from a .sto or .mot file.

        Args:
            filepath: Path to motion file

        Returns:
            MotionData object with frames and metadata

        Raises:
            FileNotFoundError: If motion file does not exist
            ValueError: If motion file format is invalid
            RuntimeError: If motion loading fails

        Example:
            motion = load_motion_from_file("path/to/motion.sto")
            print(f"Loaded {motion.num_frames} frames")
            print(f"Duration: {motion.end_time - motion.start_time} seconds")
        """
        from osim_render.api.loaders.motion_loader import MotionLoader
        from pathlib import Path

        loader = MotionLoader()
        model = self.model_manager.get_opensim_model()
        motion = loader.load(Path(filepath), model=model)
        return motion

    def _create_animation_from_motion(
        self, motion_data: Any = None, name: str = ""
    ) -> Any:
        """Create an animation from motion data.

        Args:
            motion_data: MotionData to animate (uses pre-loaded if None)
            name: Optional name for the animation

        Returns:
            Animation object ready to use in Scene

        Example:
            # Using pre-loaded motion
            animation = create_animation_from_motion()

            # Or using a specific motion file
            motion = load_motion_from_file("gait.sto")
            animation = create_animation_from_motion(motion)
        """
        from osim_render.api.animation.integration import MotionDataAnimation

        data = motion_data if motion_data is not None else self.motion_data

        if data is None:
            raise RuntimeError(
                "No motion data available. Either:\n"
                "1. Load a motion file in the UI (File  Open Motion File)\n"
                "2. Pass motion_data to this function\n"
                "3. Use load_motion_from_file() to load from disk"
            )

        return MotionDataAnimation(name=name, motion_data=data, time_scale=self.time_scale)

    @staticmethod
    def get_example_scripts() -> dict[str, str]:
        """Get example scripts for users to learn from.

        Returns:
            Dictionary of example name -> code
        """
        return {
            "Simple Hip Animation": """
# Simple animation of the hip coordinate (gait2392 model)
scene = Scene(model_manager, scene_manager, event_bus)

# Animate hip flexion from 0 to 45 degrees over 2 seconds
scene.animate_coordinate("hip_flexion_r", 0, 45, duration=2.0)

timeline = scene.build_timeline()
""",
            "Multiple Coordinates": """
# Animate multiple coordinates simultaneously (gait2392 model)
scene = Scene(model_manager, scene_manager, event_bus)

scene.animate_coordinate("hip_flexion_r", 0, 45, duration=2.0)
scene.animate_coordinate("knee_angle_r", 0, 60, duration=2.0)

timeline = scene.build_timeline()
""",
            "Sequential Animation": """
# Chain animations one after another (gait2392 model)
scene = Scene(model_manager, scene_manager, event_bus)

# Animate hip first
scene.animate_coordinate("hip_flexion_r", 0, 45, duration=1.0)

# Then animate knee (starts at 1.0 seconds)
scene.animate_coordinate("knee_angle_r", 0, 60, duration=1.0, start_time=1.0)

timeline = scene.build_timeline()
""",
            "Easing Functions": """
from osim_render.api.animation.easing import ease_in_out_cubic
from osim_render.api.animation.tween import TweenConfig

# Smooth hip flexion with easing (gait2392 model)
scene = Scene(model_manager, scene_manager, event_bus)

config = TweenConfig(duration=2.0, easing=ease_in_out_cubic)
scene.animate_coordinate("hip_flexion_r", 0, 45, duration=config.duration, easing=config.easing, delay=config.delay)

timeline = scene.build_timeline()
""",
            "Camera Animation": """
# Animate the camera while moving the model (gait2392 model)
from osim_render.api.animation.value_types import CameraState

scene = Scene(model_manager, scene_manager, event_bus)

# Animate hip flexion
scene.animate_coordinate("hip_flexion_r", 0, 45, duration=2.0)

# Animate camera (smooth rotation around model)
scene.animate_camera_to(
    target_state=CameraState.front_view(),
    duration=2.0
)

timeline = scene.build_timeline()
""",
            "Complex Motion": """
# Walking-like motion (gait2392 model)
scene = Scene(model_manager, scene_manager, event_bus)

# Hip flexion
scene.animate_coordinate("hip_flexion_r", 0, 30, duration=0.5)
scene.animate_coordinate("hip_flexion_r", 30, 0, duration=0.5, start_time=0.5)

# Knee follows hip with offset phase
scene.animate_coordinate("knee_angle_r", 0, 45, duration=0.5, start_time=0.25)
scene.animate_coordinate("knee_angle_r", 45, 0, duration=0.5, start_time=0.75)

timeline = scene.build_timeline()
""",
        }


if __name__ == "__main__":
    # Smoke test
    print("Testing script_executor module...")

    from osim_render.api.managers.model_manager import ModelManager as _ModelManager
    from osim_render.api.managers.event_bus import EventBus as _EventBus

    executor = ScriptExecutor(
        _ModelManager(_EventBus()),
        None,
        _EventBus(),
    )

    # Test with valid script that creates timeline
    code = """
scene = Scene(model_manager, scene_manager, event_bus)
scene.animate_coordinate("test", 0, 45, duration=1.0)
timeline = scene.build_timeline()
print(f"Timeline duration: {timeline.duration}")
"""

    result = executor.execute(code, "test")
    print(f"Execution success: {result.success}")
    if result.success:
        print(f"Timeline created: {result.timeline is not None}")

    # Test examples
    examples = executor.get_example_scripts()
    print(f"\nAvailable examples: {list(examples.keys())}")

    print("\n[OK] Script executor module smoke test passed!")
