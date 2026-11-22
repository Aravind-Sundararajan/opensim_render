"""Shared pytest fixtures for all test suites."""

from pathlib import Path

import pytest

# Importing osim_render before PySide6 runs qt_preload.preload_system_icu(),
# which must happen before the first Qt import (see osim_render/qt_preload.py).
import osim_render  # noqa: F401
from PySide6.QtWidgets import QApplication

from osim_render.api.managers.event_bus import EventBus
from osim_render.api.managers.settings_manager import SettingsManager
from osim_render.api.managers.model_manager import ModelManager


@pytest.fixture(scope="session")
def app() -> QApplication:
    """Session-scoped QApplication instance for all tests."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


@pytest.fixture
def event_bus() -> EventBus:
    """Fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def settings_manager(tmp_path: Path) -> SettingsManager:
    """SettingsManager with temporary config path."""
    return SettingsManager(config_path=tmp_path / "settings.json")


@pytest.fixture
def model_manager(event_bus: EventBus) -> ModelManager:
    """ModelManager with event_bus."""
    return ModelManager(event_bus)
