"""Factory for creating configured coordinate sliders."""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QSlider,
    QLineEdit,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette, QKeyEvent, QMouseEvent, QFocusEvent

from .state import CoordinateInfo
from osim_render.api.logging import get_logger_for

logger = get_logger_for(__name__)


class EditableValueLabel(QLineEdit):
    """A value display that becomes editable on double-click.

    Shows a read-only value that can be edited by double-clicking.
    Emits valueSubmitted signal when a new value is entered.
    """

    valueSubmitted = Signal(float)

    def __init__(
        self,
        initial_value: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize editable value label.

        Args:
            initial_value: Initial numeric value to display
            min_value: Minimum allowed value (for validation)
            max_value: Maximum allowed value (for validation)
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_value = initial_value
        self.min_value = min_value
        self.max_value = max_value
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setText(f"{initial_value:.4f}")
        self.setMaximumWidth(80)

        # Styling to look like a label when read-only
        self.setStyleSheet(
            "QLineEdit { border: none; background-color: transparent; }")

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Enable editing on double-click."""
        self.setReadOnly(False)
        self.selectAll()
        self.setFocus()
        self._set_edit_style()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """Disable editing and submit value on focus loss."""
        if not self.isReadOnly():
            self._submit_value()
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle Enter key to submit value."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._submit_value()
        elif event.key() == Qt.Key.Key_Escape:
            # Cancel editing
            self.setReadOnly(True)
            self.setText(f"{self.current_value:.4f}")
            self._set_readonly_style()
        else:
            super().keyPressEvent(event)

    def _set_edit_style(self) -> None:
        """Apply editable style using system colors."""
        palette = self.palette()
        base_color = palette.color(QPalette.ColorRole.Base)
        text_color = palette.color(QPalette.ColorRole.Text)
        border_color = palette.color(QPalette.ColorRole.Mid)

        self.setStyleSheet(
            f"QLineEdit {{ "
            f"border: 1px solid {border_color.name()}; "
            f"background-color: {base_color.name()}; "
            f"color: {text_color.name()}; "
            f"}}"
        )

    def _set_readonly_style(self) -> None:
        """Apply read-only style to blend with surrounding widgets."""
        self.setStyleSheet(
            "QLineEdit { border: none; background-color: transparent; }")

    def _submit_value(self) -> None:
        """Validate and submit the entered value."""
        try:
            new_value = float(self.text())

            # Clamp value to valid range if range is defined
            if self.min_value is not None:
                new_value = max(self.min_value, new_value)
            if self.max_value is not None:
                new_value = min(self.max_value, new_value)

            self.current_value = new_value
            self.valueSubmitted.emit(new_value)
            self.setText(f"{new_value:.4f}")
        except ValueError:
            logger.debug(
                f"Invalid coordinate input '{self.text()}', reverting to {self.current_value:.4f}")
            self.setText(f"{self.current_value:.4f}")
        finally:
            self.setReadOnly(True)
            self._set_readonly_style()

    def set_value(self, value: float) -> None:
        """Update the displayed value.

        Args:
            value: New value to display
        """
        self.current_value = value
        self.setText(f"{value:.4f}")


class CoordinateSliderRow(QWidget):
    """A single coordinate slider with label, value display and constraints."""

    SLIDER_RANGE = 1000  # Internal slider range for precision

    lockToggled = Signal(str, bool)
    clampToggled = Signal(str, bool)

    def __init__(self, coord_info: CoordinateInfo, parent: Optional[QWidget] = None):
        """Initialize slider row.

        Args:
            coord_info: CoordinateInfo with name and range
            parent: Parent widget
        """
        super().__init__(parent)

        self.coord_info = coord_info
        self.current_value = coord_info.default_value

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)

        # Label with coordinate name
        label = QLabel(coord_info.name)
        label.setMaximumWidth(150)
        layout.addWidget(label)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(self.SLIDER_RANGE)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(self.SLIDER_RANGE // 10)
        self.slider.setPageStep(self.SLIDER_RANGE // 20)

        # Map coordinate default to slider position
        slider_pos = self._value_to_slider(coord_info.default_value)
        self.slider.setValue(slider_pos)

        self.slider.setProperty("coordinate_name", coord_info.name)
        self.slider.setProperty("coord_min", coord_info.min_value)
        self.slider.setProperty("coord_max", coord_info.max_value)

        layout.addWidget(self.slider, 1)

        # Value display (editable on double-click)
        self.value_label = EditableValueLabel(
            coord_info.default_value,
            min_value=coord_info.min_value,
            max_value=coord_info.max_value,
        )
        layout.addWidget(self.value_label)

        self.lock_box = QCheckBox("L")
        self.lock_box.setToolTip(
            "Lock: hold this coordinate fixed. Locked coordinates cannot be "
            "moved by sliders, motion playback or IK posing."
        )
        layout.addWidget(self.lock_box)

        self.clamp_box = QCheckBox("C")
        self.clamp_box.setToolTip(
            f"Clamp: keep this coordinate inside its range "
            f"[{coord_info.min_value:.3f}, {coord_info.max_value:.3f}] while IK solves."
        )
        layout.addWidget(self.clamp_box)

        self.setLayout(layout)

        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.slider.valueChanged.connect(self._on_slider_moved)

        self.value_label.valueSubmitted.connect(self._on_value_submitted)

        self.lock_box.toggled.connect(self._on_lock_toggled)
        self.clamp_box.toggled.connect(self._on_clamp_toggled)

    def _on_lock_toggled(self, locked: bool) -> None:
        """Disable editing while locked and announce the change.

        Args:
            locked: True when the coordinate should be held fixed
        """
        self.slider.setEnabled(not locked)
        self.value_label.setEnabled(not locked)
        self.lockToggled.emit(self.coord_info.name, locked)

    def _on_clamp_toggled(self, clamped: bool) -> None:
        """Announce a change to range enforcement.

        Args:
            clamped: True when the range should be enforced during IK
        """
        self.clampToggled.emit(self.coord_info.name, clamped)

    def is_locked(self) -> bool:
        """Whether this coordinate is locked.

        Returns:
            True if the lock toggle is checked
        """
        return self.lock_box.isChecked()

    def is_clamped(self) -> bool:
        """Whether this coordinate's range is enforced during IK.

        Returns:
            True if the clamp toggle is checked
        """
        return self.clamp_box.isChecked()

    def set_constraints(self, locked: bool, clamped: bool) -> None:
        """Reflect model state in the toggles without re-emitting signals.

        Args:
            locked: Current lock flag
            clamped: Current clamp flag
        """
        for box, value in ((self.lock_box, locked), (self.clamp_box, clamped)):
            box.blockSignals(True)
            box.setChecked(value)
            box.blockSignals(False)

        self.slider.setEnabled(not locked)
        self.value_label.setEnabled(not locked)

    def _value_to_slider(self, value: float) -> int:
        """Convert coordinate value to slider position."""
        if self.coord_info.max_value == self.coord_info.min_value:
            return self.SLIDER_RANGE // 2

        normalized = (value - self.coord_info.min_value) / (
            self.coord_info.max_value - self.coord_info.min_value
        )
        normalized = max(0, min(1, normalized))  # Clamp to [0, 1]
        return int(normalized * self.SLIDER_RANGE)

    def _slider_to_value(self, slider_pos: int) -> float:
        """Convert slider position to coordinate value."""
        normalized = slider_pos / self.SLIDER_RANGE
        return self.coord_info.min_value + normalized * (
            self.coord_info.max_value - self.coord_info.min_value
        )

    def _on_slider_moved(self, slider_value: int) -> None:
        """Handle slider movement."""
        self.current_value = self._slider_to_value(slider_value)
        self.value_label.set_value(self.current_value)

    def _on_value_submitted(self, value: float) -> None:
        """Handle direct value input from double-click editing.

        Args:
            value: New value entered by user (already clamped by EditableValueLabel)
        """
        slider_pos = self._value_to_slider(value)
        self.current_value = value
        self.slider.setValue(slider_pos)

    def get_coordinate_name(self) -> str:
        """Get the coordinate name."""
        return self.coord_info.name

    def get_current_value(self) -> float:
        """Get the current coordinate value."""
        return self.current_value

    def set_value(self, value: float) -> None:
        """Set the slider value programmatically."""
        slider_pos = self._value_to_slider(value)
        self.slider.blockSignals(True)
        self.slider.setValue(slider_pos)
        self.slider.blockSignals(False)
        self.current_value = value
        self.value_label.set_value(value)
