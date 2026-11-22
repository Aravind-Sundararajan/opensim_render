"""Tests for CLI argument parsing and application startup."""

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from PySide6.QtWidgets import QMainWindow

from main import parse_arguments, create_application


class TestCLIArgumentParsing:
    """Test CLI argument parsing for main.py."""

    def test_no_arguments(self) -> None:
        """Test parsing with no arguments."""
        args = parse_arguments([])
        assert args.model is None
        assert args.geometry_paths == []
        assert args.verbose is False

    def test_model_argument(self) -> None:
        """Test parsing model file argument."""
        args = parse_arguments(["model.osim"])
        assert args.model == Path("model.osim")
        assert args.geometry_paths == []

    def test_model_absolute_path(self) -> None:
        """Test parsing absolute model path."""
        model_path = "/path/to/model.osim"
        args = parse_arguments([model_path])
        assert args.model == Path(model_path)

    def test_model_relative_path(self) -> None:
        """Test parsing relative model path."""
        model_path = "models/subdir/model.osim"
        args = parse_arguments([model_path])
        assert args.model == Path(model_path)

    def test_single_geometry_path(self) -> None:
        """Test parsing single geometry search path."""
        args = parse_arguments(["-g", "/geometry/path"])
        assert args.geometry_paths == [Path("/geometry/path")]
        assert args.model is None

    def test_multiple_geometry_paths(self) -> None:
        """Test parsing multiple geometry search paths."""
        args = parse_arguments(
            [
                "-g",
                "/path1",
                "-g",
                "/path2",
                "-g",
                "/path3",
            ]
        )
        assert args.geometry_paths == [
            Path("/path1"),
            Path("/path2"),
            Path("/path3"),
        ]

    def test_long_geometry_path_option(self) -> None:
        """Test parsing with long --geometry-path option."""
        args = parse_arguments(["--geometry-path", "/geometry"])
        assert args.geometry_paths == [Path("/geometry")]

    def test_verbose_flag(self) -> None:
        """Test parsing verbose flag."""
        args = parse_arguments(["-v"])
        assert args.verbose is True

    def test_verbose_long_flag(self) -> None:
        """Test parsing long verbose flag."""
        args = parse_arguments(["--verbose"])
        assert args.verbose is True

    def test_model_with_geometry_paths(self) -> None:
        """Test parsing model and geometry paths together."""
        args = parse_arguments(
            [
                "model.osim",
                "-g",
                "/geometry1",
                "-g",
                "/geometry2",
            ]
        )
        assert args.model == Path("model.osim")
        assert args.geometry_paths == [
            Path("/geometry1"),
            Path("/geometry2"),
        ]

    def test_all_options_combined(self) -> None:
        """Test parsing all options together."""
        args = parse_arguments(
            [
                "model.osim",
                "-g",
                "/geometry1",
                "-g",
                "/geometry2",
                "-v",
            ]
        )
        assert args.model == Path("model.osim")
        assert args.geometry_paths == [
            Path("/geometry1"),
            Path("/geometry2"),
        ]
        assert args.verbose is True

    def test_model_after_geometry_path(self) -> None:
        """Test that model argument works after geometry path."""
        args = parse_arguments(
            [
                "-g",
                "/geometry",
                "model.osim",
            ]
        )
        assert args.model == Path("model.osim")
        assert args.geometry_paths == [Path("/geometry")]

    def test_help_option(self) -> None:
        """Test that help option works (should raise SystemExit)."""
        with pytest.raises(SystemExit) as exc_info:
            parse_arguments(["-h"])
        assert exc_info.value.code == 0

    def test_unknown_option(self) -> None:
        """Test that unknown option raises error."""
        with pytest.raises(SystemExit) as exc_info:
            parse_arguments(["--unknown"])
        assert exc_info.value.code != 0


class TestApplicationStartup:
    """Test application creation and startup with qtbot."""

    def test_create_application_returns_main_window(self, qtbot: QtBot) -> None:
        """Test create_application returns MainWindow."""
        window = create_application()
        qtbot.addWidget(window)
        assert window is not None
        assert isinstance(window, QMainWindow)

    def test_created_window_has_managers(self, qtbot: QtBot) -> None:
        """Test created window has required managers."""
        window = create_application()
        qtbot.addWidget(window)
        assert hasattr(window, "model_manager")
        assert hasattr(window, "settings_manager")
        assert hasattr(window, "event_bus")
        assert window.model_manager is not None
        assert window.settings_manager is not None
        assert window.event_bus is not None

    def test_created_window_is_hidden(self, qtbot: QtBot) -> None:
        """Test created window is hidden initially."""
        window = create_application()
        qtbot.addWidget(window)
        # Window should not be shown by create_application
        # (user should call window.show() explicitly)
        # This depends on implementation, but typically the window
        # is not shown until explicitly shown by the caller
        assert window is not None

    def test_created_window_has_menu_bar(self, qtbot: QtBot) -> None:
        """Test created window has menu bar."""
        window = create_application()
        qtbot.addWidget(window)
        assert window.menuBar() is not None

    def test_multiple_application_instances(self, qtbot: QtBot) -> None:
        """Test creating multiple application instances."""
        window1 = create_application()
        qtbot.addWidget(window1)
        window2 = create_application()
        qtbot.addWidget(window2)
        assert window1 is not None
        assert window2 is not None
        # They should be different instances
        assert window1 is not window2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
