"""Scene animation package.

Re-exports the :class:`Scene` fluent-API class and its concern-focused mixins
so existing imports such as ``from osim_render.api.animation.scene import Scene``
keep working after the module was split into a package.
"""

from osim_render.api.animation.scene.coordinate_animation import (
    CoordinateAnimationMixin,
)
from osim_render.api.animation.scene.camera_animation import CameraAnimationMixin
from osim_render.api.animation.scene.property_animation import (
    PropertyAnimationMixin,
)
from osim_render.api.animation.scene.scene import Scene

__all__ = [
    "Scene",
    "CoordinateAnimationMixin",
    "CameraAnimationMixin",
    "PropertyAnimationMixin",
]
