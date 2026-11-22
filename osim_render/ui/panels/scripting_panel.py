"""
Scripting panel - Write and execute Python animation scripts.

Provides a code editor for users to create complex animations using
the manim-style Scene API.
"""

from pathlib import Path
from typing import Any, Optional, Protocol

from PySide6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QComboBox,
    QLabel,
    QFileDialog,
    QMessageBox,
    QTextEdit,
    QProgressBar,
)
from PySide6.QtGui import (
    QFont,
    QSyntaxHighlighter,
    QTextDocument,
    QColor,
    QTextCharFormat,
)
from PySide6.QtCore import QRegularExpression

from osim_render.api.animation.script_executor import ScriptExecutor
from osim_render.api.animation.timeline import Timeline


class ParentWidgetProtocol(Protocol):
    """Protocol for parent widget of ScriptingPanel."""

    def _init_unified_renderer(self, timeline: Timeline) -> None:
        """Initialize unified renderer with timeline."""
        ...

    class PlayAction:
        """Protocol for play action."""

        def setEnabled(self, enabled: bool) -> None:
            """Enable or disable play action."""
            ...

    class PauseAction:
        """Protocol for pause action."""

        def setEnabled(self, enabled: bool) -> None:
            """Enable or disable pause action."""
            ...

    play_action: PlayAction
    pause_action: PauseAction

    class SettingsManager:
        """Protocol for settings manager."""

        def get_settings(self) -> Any:
            """Get current settings."""
            ...

        def update_settings(self, settings: Any) -> None:
            """Update settings."""
            ...

    settings_manager: SettingsManager


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """Simple Python syntax highlighter."""

    def __init__(self, document: QTextDocument):
        """Initialize syntax highlighter.

        Args:
            document: QTextDocument to highlight
        """
        super().__init__(document)

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(0, 0, 255))  # Blue

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(0, 128, 0))  # Green

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(128, 128, 128))  # Gray

        # Python keywords
        self.keywords = [
            "def",
            "class",
            "import",
            "from",
            "if",
            "else",
            "elif",
            "for",
            "while",
            "return",
            "True",
            "False",
            "None",
            "and",
            "or",
            "not",
            "in",
            "is",
            "lambda",
        ]

    def highlightBlock(self, text: str) -> None:
        """Highlight a block of text.

        Args:
            text: Text block to highlight
        """
        # Highlight comments
        comment_index = text.find("#")
        if comment_index >= 0:
            self.setFormat(
                comment_index, len(text) - comment_index, self.comment_format
            )
            text = text[:comment_index]

        # Highlight strings
        for quote_char in ['"', "'"]:
            quote_start = 0
            while True:
                quote_start = text.find(quote_char, quote_start)
                if quote_start == -1:
                    break
                quote_end = text.find(quote_char, quote_start + 1)
                if quote_end == -1:
                    quote_end = len(text)
                else:
                    quote_end += 1
                self.setFormat(quote_start, quote_end -
                               quote_start, self.string_format)
                quote_start = quote_end

        # Highlight keywords
        for keyword in self.keywords:
            pattern = f"\\b{keyword}\\b"
            regex = QRegularExpression(pattern)
            match_iterator = regex.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), self.keyword_format
                )


class ScriptingPanel(QDockWidget):
    """
    Docked panel for writing and executing animation scripts.

    Provides:
    - Python code editor with syntax highlighting
    - Execute button to run scripts
    - Example scripts to learn from
    - Output console for errors and messages
    - Timeline display when animation is created

    Attributes:
        script_executor: Executor for running scripts
        current_timeline: Currently loaded timeline from script
    """

    def __init__(
        self,
        script_executor: ScriptExecutor,
        parent: Optional[QWidget] = None,
    ):
        """Initialize scripting panel.

        Args:
            script_executor: ScriptExecutor instance
            parent: Parent widget
        """
        super().__init__("Animation Scripts", parent)
        self.script_executor = script_executor
        self.current_timeline: Optional[Timeline] = None
        self.current_script_path: Optional[Path] = None

        main_widget = QWidget()
        self.setWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)

        # ===== Top Toolbar =====
        toolbar_layout = QHBoxLayout()

        # Example scripts dropdown
        toolbar_layout.addWidget(QLabel("Examples:"))
        self.examples_combo = QComboBox()
        self.examples_combo.addItem("Select example...")
        for example_name in script_executor.get_example_scripts():
            self.examples_combo.addItem(example_name)
        self.examples_combo.currentTextChanged.connect(
            self._on_example_selected)
        toolbar_layout.addWidget(self.examples_combo)

        toolbar_layout.addStretch()

        # File buttons
        self.new_button = QPushButton("New")
        self.new_button.clicked.connect(self._on_new)
        toolbar_layout.addWidget(self.new_button)

        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self._on_open)
        toolbar_layout.addWidget(self.open_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save)
        toolbar_layout.addWidget(self.save_button)

        main_layout.addLayout(toolbar_layout)

        # ===== Code Editor =====
        editor_layout = QHBoxLayout()
        editor_layout.addWidget(QLabel("Script:"))

        self.code_editor = QPlainTextEdit()
        self.code_editor.setFont(QFont("Consolas", 10))
        self.code_editor.setPlaceholderText(
            "# Write your animation script here\n"
            "# Use: scene = Scene(...)\n"
            "# Then: timeline = scene.build_timeline()"
        )

        self.highlighter = PythonSyntaxHighlighter(self.code_editor.document())

        editor_layout.addWidget(self.code_editor)
        main_layout.addLayout(editor_layout)

        # ===== Execute Button =====
        execute_layout = QHBoxLayout()
        self.execute_button = QPushButton("Execute Script")
        self.execute_button.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        self.execute_button.clicked.connect(self._on_execute)
        execute_layout.addWidget(self.execute_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(0)  # Indeterminate
        execute_layout.addWidget(self.progress_bar)

        main_layout.addLayout(execute_layout)

        # ===== Output Console =====
        console_layout = QHBoxLayout()
        console_layout.addWidget(QLabel("Output:"))

        self.output_console = QTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setFont(QFont("Consolas", 9))
        self.output_console.setMaximumHeight(150)
        console_layout.addWidget(self.output_console)
        main_layout.addLayout(console_layout)

        # ===== Status =====
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: green;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        self.timeline_info_label = QLabel("No timeline loaded")
        status_layout.addWidget(self.timeline_info_label)

        main_layout.addLayout(status_layout)

        self._load_example("Simple Hip Animation")

    def _on_example_selected(self, example_name: str) -> None:
        """Handle example selection.

        Args:
            example_name: Name of selected example
        """
        if example_name == "Select example...":
            return
        self._load_example(example_name)
        self.examples_combo.setCurrentIndex(0)  # Reset to "Select example..."

    def _load_example(self, example_name: str) -> None:
        """Load an example script.

        Args:
            example_name: Name of example to load
        """
        examples = self.script_executor.get_example_scripts()
        if example_name in examples:
            self.code_editor.setPlainText(examples[example_name])
            self.current_script_path = None

    def _on_new(self) -> None:
        """Handle new script button."""
        if self.code_editor.toPlainText().strip():
            reply = QMessageBox.question(
                self,
                "New Script",
                "Discard current script?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.code_editor.clear()
        self.current_script_path = None
        self.output_console.clear()
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: green;")

    def _on_open(self) -> None:
        """Handle open script button."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Animation Script",
            "",
            "Python Files (*.py);;All Files (*)",
        )

        if file_path:
            with open(file_path, "r") as f:
                code = f.read()
            self.code_editor.setPlainText(code)
            self.current_script_path = Path(file_path)
            self.output_console.clear()
            self.status_label.setText(f"Loaded: {Path(file_path).name}")
            self.status_label.setStyleSheet("color: blue;")

    def _on_save(self) -> None:
        """Handle save script button."""
        if not self.current_script_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Animation Script",
                "",
                "Python Files (*.py);;All Files (*)",
            )
            if not file_path:
                return
            self.current_script_path = Path(file_path)

        with open(self.current_script_path, "w") as f:
            f.write(self.code_editor.toPlainText())
        self.status_label.setText(f"Saved: {self.current_script_path.name}")
        self.status_label.setStyleSheet("color: green;")

    def _on_execute(self) -> None:
        """Handle execute script button."""
        code = self.code_editor.toPlainText().strip()

        if not code:
            QMessageBox.warning(
                self, "Empty Script", "Please write some code to execute"
            )
            return

        # Show progress
        self.execute_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.output_console.clear()
        self.status_label.setText("Executing...")
        self.status_label.setStyleSheet("color: orange;")

        # Execute script
        result = self.script_executor.execute(code, "user_script")

        if result.output:
            self.output_console.setText(result.output)

        if result.success:
            # Success!
            self.current_timeline = result.timeline
            self.status_label.setText("Success!")
            self.status_label.setStyleSheet("color: green;")

            if result.timeline:
                self.timeline_info_label.setText(
                    f"Timeline created: {result.timeline.duration:.2f}s, "
                    f"{len(result.timeline.animations)} animation(s)"
                )
                # Auto-load timeline into renderer for playback
                self._load_timeline_to_renderer(result.timeline)

            if result.output:
                self.output_console.append("\n[Script executed successfully]")
        else:
            # Error
            self.status_label.setText("Error!")
            self.status_label.setStyleSheet("color: red;")
            self.output_console.setText(result.error)
            self.timeline_info_label.setText("No timeline loaded")

        # Hide progress
        self.execute_button.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _load_timeline_to_renderer(self, timeline: Timeline) -> None:
        """Load timeline into main window renderer for playback.

        Args:
            timeline: Timeline to load

        Raises:
            AttributeError: If parent lacks required renderer methods
            RuntimeError: If timeline loading fails
        """
        raw_parent = self.parent()
        if raw_parent is None:
            return

        from typing import cast
        parent = cast(ParentWidgetProtocol, raw_parent)
        parent._init_unified_renderer(timeline)
        # Enable play controls
        parent.play_action.setEnabled(True)
        parent.pause_action.setEnabled(True)

        # Track script if it was loaded from a file
        if self.current_script_path:
            settings = parent.settings_manager.get_settings()
            settings = settings.with_recent_script(self.current_script_path)
            parent.settings_manager.update_settings(settings)

    def get_timeline(self) -> Optional[Timeline]:
        """Get the currently loaded timeline.

        Returns:
            Timeline created by last successful script execution, or None
        """
        return self.current_timeline


if __name__ == "__main__":
    # Smoke test
    print("Testing scripting_panel module...")

    from PySide6.QtWidgets import QApplication
    from osim_render.api.animation.script_executor import ScriptExecutor
    from osim_render.api.managers.model_manager import ModelManager
    from osim_render.api.managers.event_bus import EventBus

    _app = QApplication([])
    _executor = ScriptExecutor(ModelManager(EventBus()), None, EventBus())
    panel = ScriptingPanel(_executor)
    assert panel is not None
    print("[OK] ScriptingPanel creation works")

    print("\n[OK] Scripting panel module OK!")
