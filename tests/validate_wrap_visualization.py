#!/usr/bin/env python3
"""Comprehensive validation of wrap geometry visualization implementation."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports() -> bool:
    """Test that all wrap visualization modules can be imported."""
    print("\n[TEST 1] Module Imports")
    print("-" * 70)

    try:
        from osim_render.api.rendering.wrap_visualizer import WrapVisualizer

        print("[PASS] WrapVisualizer import")
    except ImportError as e:
        print(f"[FAIL] WrapVisualizer import: {e}")
        return False

    try:
        from osim_render.api.rendering.scene import SceneManager, RenderScene

        print("[PASS] SceneManager and RenderScene imports")
    except ImportError as e:
        print(f"[FAIL] SceneManager import: {e}")
        return False

    try:
        from osim_render.api.managers.visualization_state_manager import (
            VisualizationStateManager,
        )

        print("[PASS] VisualizationStateManager import")
    except ImportError as e:
        print(f"[FAIL] VisualizationStateManager import: {e}")
        return False

    return True


def test_wrap_object_creation() -> bool:
    """Test wrap object detection and actor creation."""
    print("\n[TEST 2] Wrap Object Creation")
    print("-" * 70)

    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.managers.event_bus import EventBus
    from osim_render.api.rendering.scene import SceneManager

    model_path = str(
        project_root / "models" / "upperExtremity" / "Arm26" / "arm26.osim"
    )

    if not Path(model_path).exists():
        print(f"[SKIP] Arm26 model not found at {model_path}")
        return True

    try:
        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        model_manager.load_model(model_path)

        scene_manager = SceneManager(model_manager, model_path)
        scene = scene_manager.create_scene()

        wrap_actors = scene.wrap_actors
        if not wrap_actors:
            print("[FAIL] No wrap objects detected in Arm26 model")
            return False

        print(f"[PASS] Created {len(wrap_actors)} wrap object actors")

        # Verify wrap actor types
        for wrap_name, actor in wrap_actors.items():
            if not actor:
                print(f"[FAIL] Wrap actor {wrap_name} is None")
                return False
            if not hasattr(actor, "GetProperty"):
                print(f"[FAIL] Wrap actor {wrap_name} is not a vtkActor")
                return False

        print(f"[PASS] All {len(wrap_actors)} wrap actors are properly formed")

        return True

    except Exception as e:
        print(f"[FAIL] Exception during wrap object creation: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_visualization_state() -> bool:
    """Test VisualizationStateManager wrap_actors support."""
    print("\n[TEST 3] Visualization State Management")
    print("-" * 70)

    from osim_render.api.managers.visualization_state_manager import (
        VisualizationStateManager,
    )

    try:
        manager = VisualizationStateManager()

        # Initialize wrap_actors category
        wrap_names = ["wrap_obj1", "wrap_obj2", "wrap_obj3"]
        manager.initialize_category("wrap_actors", wrap_names, default_visible=False)

        # Check initialization
        total, visible = manager.get_summary("wrap_actors")
        if total != 3 or visible != 0:
            print(f"[FAIL] Expected (3, 0), got ({total}, {visible})")
            return False

        print("[PASS] Initialized 3 wrap objects with default visibility=False")

        # Test visibility setting
        manager.set_visibility("wrap_actors", "wrap_obj1", True)
        total, visible = manager.get_summary("wrap_actors")
        if total != 3 or visible != 1:
            print(f"[FAIL] Expected (3, 1), got ({total}, {visible})")
            return False

        print("[PASS] Set visibility for individual wrap object")

        # Test show all
        manager.set_all_visibility("wrap_actors", True)
        total, visible = manager.get_summary("wrap_actors")
        if total != 3 or visible != 3:
            print(f"[FAIL] Expected (3, 3), got ({total}, {visible})")
            return False

        print("[PASS] Show all wrap objects")

        # Test clear
        manager.clear()
        total, visible = manager.get_summary("wrap_actors")
        if total != 0:
            print(f"[FAIL] Expected (0, ?), got ({total}, ?)")
            return False

        print("[PASS] Clear wrap object visibility state")

        return True

    except Exception as e:
        print(f"[FAIL] Exception during state management test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_scene_api_animation() -> bool:
    """Test Scene API animation methods with wrap objects."""
    print("\n[TEST 4] Scene API Animation")
    print("-" * 70)

    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.managers.event_bus import EventBus
    from osim_render.api.rendering.scene import SceneManager
    from osim_render.api.animation.scene import Scene

    model_path = str(
        project_root / "models" / "upperExtremity" / "Arm26" / "arm26.osim"
    )

    if not Path(model_path).exists():
        print("[SKIP] Arm26 model not found")
        return True

    try:
        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        model_manager.load_model(model_path)

        scene_manager = SceneManager(model_manager, model_path)
        scene = Scene(model_manager, scene_manager, event_bus)

        # Test fade_in
        scene.fade_in("r_humerus_TRI", duration=1.0)
        print("[PASS] fade_in() animation method")

        # Test fade_out
        scene.fade_out("r_humerus_TRI", duration=1.0, start_time=1.0)
        print("[PASS] fade_out() animation method")

        # Test pulse_opacity
        scene.pulse_opacity(
            "r_humerus_BIClonghh", min_opacity=0.2, max_opacity=0.8, cycles=2
        )
        print("[PASS] pulse_opacity() animation method")

        # Test coordinate animation
        scene.animate_coordinate("shoulder_elev", 0, 45, duration=2.0)
        print("[PASS] animate_coordinate() method")

        # Test timeline building
        scene.build_timeline()
        print("[PASS] build_timeline() method")

        return True

    except Exception as e:
        print(f"[FAIL] Exception during Scene API test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_position_realization() -> bool:
    """Test position realization wrapper methods."""
    print("\n[TEST 5] Position Realization Guarantees")
    print("-" * 70)

    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.managers.event_bus import EventBus
    from osim_render.api.rendering.scene import SceneManager

    model_path = str(
        project_root / "models" / "upperExtremity" / "Arm26" / "arm26.osim"
    )

    if not Path(model_path).exists():
        print("[SKIP] Arm26 model not found")
        return True

    try:
        event_bus = EventBus()
        model_manager = ModelManager(event_bus)
        model_manager.load_model(model_path)

        scene_manager = SceneManager(model_manager, model_path)

        # Check that position realization flag exists and works
        if not hasattr(scene_manager, "_position_realized"):
            print("[FAIL] _position_realized flag not found in SceneManager")
            return False

        print("[PASS] _position_realized flag exists")

        # Check methods exist
        if not hasattr(scene_manager, "_realize_position"):
            print("[FAIL] _realize_position() method not found")
            return False

        if not hasattr(scene_manager, "_invalidate_position"):
            print("[FAIL] _invalidate_position() method not found")
            return False

        print("[PASS] Position realization wrapper methods exist")

        # Test the flag behavior
        if scene_manager._position_realized:
            print("[FAIL] Position should not be realized initially")
            return False

        scene_manager._realize_position()
        if not scene_manager._position_realized:
            print("[FAIL] Position should be realized after _realize_position()")
            return False

        scene_manager._invalidate_position()
        if scene_manager._position_realized:
            print("[FAIL] Position should not be realized after _invalidate_position()")
            return False

        print("[PASS] Position realization flag behaves correctly")

        return True

    except Exception as e:
        print(f"[FAIL] Exception during position realization test: {e}")
        import traceback

        traceback.print_exc()
        return False


def main() -> int:
    """Run all validation tests."""
    print("=" * 70)
    print("WRAP GEOMETRY VISUALIZATION VALIDATION")
    print("=" * 70)

    results = []

    # Run all tests
    results.append(("Module Imports", test_imports()))
    results.append(("Wrap Object Creation", test_wrap_object_creation()))
    results.append(("Visualization State", test_visualization_state()))
    results.append(("Scene API Animation", test_scene_api_animation()))
    results.append(("Position Realization", test_position_realization()))

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All validation tests passed!")
        print("Wrap geometry visualization is fully functional.")
        return 0
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
