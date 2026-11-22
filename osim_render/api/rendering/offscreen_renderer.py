"""
Offscreen VTK rendering for export without UI window.

Provides rendering to images for video export and screenshots
without requiring a visible window on screen.
"""

from pathlib import Path
from typing import Any, cast, Tuple

import numpy as np
from vtk import (
    vtkRenderWindow,
    vtkRenderer,
    vtkWindowToImageFilter,
    vtkPNGWriter,
)
from vtk.util.numpy_support import vtk_to_numpy

from osim_render.api.animation.animation import AnimationState


class OffscreenRenderer:
    """
    Renders VTK scenes to images without displaying a window.

    Uses VTK's offscreen rendering capabilities to create images
    for exporting to video or image sequences.

    Attributes:
        resolution: Output resolution as (width, height)
        background_color: Background color as (r, g, b) in [0, 1]
    """

    def __init__(
        self,
        resolution: Tuple[int, int] = (1920, 1080),
        background_color: Tuple[float, float, float] = (0.2, 0.2, 0.2),
        transparent_background: bool = False,
    ):
        """
        Initialize offscreen renderer.

        Args:
            resolution: Output image resolution (width, height) in pixels
            background_color: Background RGB color in [0, 1]
            transparent_background: If True, render with an alpha channel and
                a fully transparent background instead of background_color
        """
        self.resolution = resolution
        self.background_color = background_color
        self.transparent_background = transparent_background
        self.render_window = vtkRenderWindow()
        self.renderer = vtkRenderer()

        self.render_window.SetOffScreenRendering(1)
        self.render_window.SetSize(*resolution)
        self.render_window.AddRenderer(self.renderer)

        self.renderer.SetBackground(*background_color)

        if transparent_background:
            self.render_window.SetAlphaBitPlanes(1)
            self.render_window.SetMultiSamples(0)
            self.renderer.SetBackgroundAlpha(0.0)

    def render_frame(self, state: AnimationState) -> "np.ndarray[Any, Any]":
        """
        Render a single frame to a numpy array.

        Args:
            state: AnimationState describing what to render

        Returns:
            Image as numpy array with shape (height, width, 3) and dtype uint8,
            with RGB values in range [0, 255]

        Notes:
            This is a placeholder that returns a black image.
            In integration, it will update VTK actors based on AnimationState.
        """
        # Render the scene
        self.render_window.Render()

        # Capture to image
        window_to_image = vtkWindowToImageFilter()
        window_to_image.SetInput(self.render_window)
        if self.transparent_background:
            window_to_image.SetInputBufferTypeToRGBA()
        window_to_image.Update()

        # Convert VTK image to numpy array
        image_data = window_to_image.GetOutput()
        width, height = self.resolution
        num_components = image_data.GetNumberOfScalarComponents()

        flat = vtk_to_numpy(image_data.GetPointData().GetScalars())
        np_array = flat.reshape(height, width, num_components)
        # VTK origin is bottom-left; flip to top-left for standard image orientation
        np_array = np.flipud(np_array)

        if num_components >= 4 and not self.transparent_background:
            return cast("np.ndarray[Any, Any]", np_array[:, :, :3].astype(np.uint8))
        return cast("np.ndarray[Any, Any]", np_array.astype(np.uint8))

    def save_frame(self, state: AnimationState, output_path: Path) -> None:
        """
        Render and save a single frame to a PNG file.

        Args:
            state: AnimationState describing what to render
            output_path: Path to save PNG file
        """
        # Render the scene
        self.render_window.Render()

        # Capture to image
        window_to_image = vtkWindowToImageFilter()
        window_to_image.SetInput(self.render_window)
        if self.transparent_background:
            window_to_image.SetInputBufferTypeToRGBA()
        window_to_image.Update()

        writer = vtkPNGWriter()
        writer.SetFileName(str(output_path))
        writer.SetInputConnection(window_to_image.GetOutputPort())
        writer.Write()

    def reset(self) -> None:
        """Reset the renderer (remove all actors)."""
        self.renderer.RemoveAllViewProps()


if __name__ == "__main__":
    # Smoke test
    print("Testing offscreen_renderer module...")

    renderer = OffscreenRenderer(resolution=(800, 600))
    assert renderer.resolution == (800, 600)
    print("[PASS] OffscreenRenderer creation works")

    state = AnimationState(
        time=0.0,
        coordinate_values={"hip": 0.0},
        camera_state=None,
        actor_properties={},
    )

    # Try rendering (will render empty scene)
    frame = renderer.render_frame(state)
    assert frame.shape == (
        600,
        800,
        3,
    ), f"Expected shape (600, 800, 3), got {frame.shape}"
    assert frame.dtype == np.uint8
    print(f"[PASS] OffscreenRenderer.render_frame works (shape: {frame.shape})")

    print("\n[PASS] All offscreen_renderer tests passed!")
