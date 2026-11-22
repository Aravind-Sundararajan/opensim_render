"""Unit tests for script executor."""

import pytest

from osim_render.api.animation.script_executor import ScriptExecutor, ScriptExecutionResult
from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.model_manager import ModelManager


class TestScriptExecutionResult:
    """Test ScriptExecutionResult class."""

    def test_successful_result(self) -> None:
        """Test creating successful result."""
        result = ScriptExecutionResult(success=True, output="test")
        assert result.success is True
        assert result.output == "test"
        assert result.error == ""
        assert result.timeline is None

    def test_failed_result(self) -> None:
        """Test creating failed result."""
        result = ScriptExecutionResult(success=False, error="test error")
        assert result.success is False
        assert result.error == "test error"

    def test_result_with_timeline(self) -> None:
        """Test result with timeline."""
        from osim_render.api.animation.timeline import Timeline
        from osim_render.api.animation.animation import Animation
        from osim_render.api.animation.coordinate_tween import CoordinateTween
        from osim_render.api.animation.tween import TweenConfig

        tween = CoordinateTween(
            coordinate_name="test",
            start_value=0.0,
            end_value=100.0,
            config=TweenConfig(duration=1.0),
        )
        animation = Animation(name="test", tweens=(tween,), duration=1.0)
        timeline = Timeline(animations=(animation,))
        result = ScriptExecutionResult(success=True, timeline=timeline)
        assert result.timeline is timeline


class TestScriptExecutor:
    """Test ScriptExecutor class."""

    @pytest.fixture
    def executor(self) -> ScriptExecutor:
        """Create script executor with real ModelManager and minimal SceneManager stub."""
        model_manager = ModelManager(EventBus())
        event_bus = EventBus()
        return ScriptExecutor(
            model_manager,
            None,
            event_bus,
        )

    def test_executor_creation(self, executor: ScriptExecutor) -> None:
        """Test creating script executor."""
        assert executor is not None

    def test_execute_empty_code(self, executor: ScriptExecutor) -> None:
        """Test executing empty code raises ValueError."""
        # Empty code has no timeline - should raise
        with pytest.raises(ValueError):
            executor.execute("")

    def test_execute_simple_assignment(self, executor: ScriptExecutor) -> None:
        """Test executing simple Python assignment."""
        code = """
x = 1 + 1
timeline = None  # For test
"""
        # Should raise because no timeline
        with pytest.raises(ValueError):
            executor.execute(code)

    def test_execute_with_print(self, executor: ScriptExecutor) -> None:
        """Test executing code with print output."""
        code = """
print('hello world')
from osim_render.api.animation.scene import Scene
scene = Scene(model_manager, scene_manager, event_bus)
scene.animate_coordinate("test", 0, 45, duration=1.0)
timeline = scene.build_timeline()
"""
        result = executor.execute(code)
        assert result.success is True
        assert "hello world" in result.output

    def test_execute_syntax_error(self, executor: ScriptExecutor) -> None:
        """Test executing syntax error raises."""
        code = "x = ("  # Syntax error
        with pytest.raises(SyntaxError):
            executor.execute(code)

    def test_execute_runtime_error(self, executor: ScriptExecutor) -> None:
        """Test executing code with runtime error."""
        code = """
raise ValueError('boom')
"""
        with pytest.raises(ValueError):
            executor.execute(code)

    def test_execute_indentation_error(self, executor: ScriptExecutor) -> None:
        """Test indentation error."""
        code = """
if True:
x = 1  # Indentation error
"""
        with pytest.raises(IndentationError):
            executor.execute(code)

    def test_execute_requires_timeline(self, executor: ScriptExecutor) -> None:
        """Test execution fails without timeline."""
        code = """
x = 1
"""
        with pytest.raises(ValueError, match="timeline"):
            executor.execute(code)

    def test_get_example_scripts_not_empty(self, executor: ScriptExecutor) -> None:
        """Test get_example_scripts returns dict."""
        examples = ScriptExecutor.get_example_scripts()
        assert isinstance(examples, dict)
        assert len(examples) > 0

    def test_get_example_scripts_keys(self, executor: ScriptExecutor) -> None:
        """Test example scripts have expected keys."""
        examples = ScriptExecutor.get_example_scripts()
        assert "Simple Hip Animation" in examples
        assert "Multiple Coordinates" in examples
        assert "Sequential Animation" in examples

    def test_get_example_scripts_content(self, executor: ScriptExecutor) -> None:
        """Test example scripts contain code."""
        examples = ScriptExecutor.get_example_scripts()
        for code in examples.values():
            assert isinstance(code, str)
            assert len(code) > 0
            assert "scene" in code.lower() or "timeline" in code.lower()

    def test_example_script_is_valid_python(self, executor: ScriptExecutor) -> None:
        """Test example scripts are valid Python."""
        examples = ScriptExecutor.get_example_scripts()
        for name, code in examples.items():
            # Should not raise SyntaxError
            compile(code, name, "exec")

    def test_execute_with_scene_api(self, executor: ScriptExecutor) -> None:
        """Test executing code that uses Scene API."""
        code = """
from osim_render.api.animation.scene import Scene
from osim_render.api.animation.tween import TweenConfig
from osim_render.api.animation.coordinate_tween import CoordinateTween

scene = Scene(model_manager, scene_manager, event_bus)
scene.animate_coordinate("test", 0, 45, duration=1.0)
timeline = scene.build_timeline()
"""
        result = executor.execute(code)
        assert result.success is True
        assert result.timeline is not None

    def test_create_scene_method(self, executor: ScriptExecutor) -> None:
        """Test _create_scene method."""
        scene = executor._create_scene()
        assert scene is not None
        from osim_render.api.animation.scene import Scene

        assert isinstance(scene, Scene)

    def test_namespace_has_required_items(self, executor: ScriptExecutor) -> None:
        """Test namespace has required items."""
        namespace = executor._create_namespace()
        assert "Scene" in namespace
        assert "Timeline" in namespace
        assert "create_scene" in namespace
        assert "print" in namespace
        assert "model_manager" in namespace
        assert "scene_manager" in namespace
        assert "event_bus" in namespace

    def test_motion_data_in_namespace(self) -> None:
        """Test motion_data is wired into namespace when None."""
        model_manager = ModelManager(EventBus())
        event_bus = EventBus()

        executor = ScriptExecutor(
            model_manager,
            None,
            event_bus,
            motion_data=None,
        )

        namespace = executor._create_namespace()
        assert namespace["motion_data"] is None

    def test_execute_with_script_name(self, executor: ScriptExecutor) -> None:
        """Test execute with script_name parameter."""
        code = """
from osim_render.api.animation.scene import Scene
scene = Scene(model_manager, scene_manager, event_bus)
scene.animate_coordinate("test", 0, 45, duration=1.0)
timeline = scene.build_timeline()
"""
        result = executor.execute(code, script_name="my_animation")
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
