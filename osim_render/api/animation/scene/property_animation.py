"""Property animation mixin for the Scene fluent API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Self

from osim_render.api.animation.easing import EasingFunction, ease_smooth_step
from osim_render.api.animation.group_tween import ParallelTween
from osim_render.api.animation.property_tween import ColorTween
from osim_render.api.animation.tween import TweenConfig
from osim_render.api.animation.value_types import ColorValue

if TYPE_CHECKING:
    from osim_render.api.animation.animation import AnimationBuilder
    from osim_render.api.managers.property_control_manager import (
        PropertyControlManager,
    )


class PropertyAnimationMixin:
    """Fluent methods for animating actor visual properties."""

    if TYPE_CHECKING:
        # Shared state owned by Scene (set in Scene.__init__); declared here so
        # the mixin type-checks in isolation under strict mypy.
        time_scale: float
        _current_time: float
        property_manager: Optional[PropertyControlManager]
        _builder: AnimationBuilder

    def set_visibility(self, actor_name: str, visible: bool) -> Self:
        """
        Set visibility instantly (no animation).

        Convenience method for instantly showing or hiding an actor.

        Args:
            actor_name: Name of the actor
            visible: Whether actor should be visible

        Returns:
            Self for method chaining

        Examples:
            >>> scene.set_visibility("pelvis", True)
            >>> scene.set_visibility("femur", False)
        """
        if self.property_manager:
            self.property_manager.set_visibility(actor_name, visible)
        return self

    def set_opacity(self, actor_name: str, opacity: float) -> Self:
        """
        Set opacity instantly (no animation).

        Convenience method for instantly setting opacity.

        Args:
            actor_name: Name of the actor
            opacity: Opacity value (0.0-1.0)

        Returns:
            Self for method chaining

        Examples:
            >>> scene.set_opacity("pelvis", 0.5)  # Semi-transparent
        """
        if self.property_manager:
            self.property_manager.set_opacity(actor_name, opacity)
        return self

    def set_color(self, actor_name: str, color: ColorValue) -> Self:
        """
        Set color instantly (no animation).

        Convenience method for instantly setting actor color.

        Args:
            actor_name: Name of the actor
            color: Target color as ColorValue

        Returns:
            Self for method chaining

        Examples:
            >>> red = ColorValue(r=1.0, g=0.0, b=0.0)
            >>> scene.set_color("pelvis", red)
        """
        if self.property_manager:
            self.property_manager.set_color(actor_name, color)
        return self

    def fade_out(
        self,
        *actor_names: str,
        duration: float = 0.5,
        easing: Optional[EasingFunction] = None,
        start_time: Optional[float] = None,
    ) -> Self:
        """
        Fade out actors by reducing opacity to zero.

        Args:
            *actor_names: Names of actors to fade out
            duration: Duration of fade in seconds (default 0.5)
            easing: Easing function (default ease_smooth_step)

        Returns:
            Self for method chaining

        Examples:
            >>> scene.fade_out("pelvis", "femur", duration=0.5)
        """
        if easing is None:
            easing = ease_smooth_step

        duration = duration / self.time_scale
        delay = (
            start_time / self.time_scale) if start_time is not None else self._current_time

        from osim_render.api.animation.property_tween import ActorPropertyTween

        tweens = tuple(
            ActorPropertyTween(
                actor_name,
                "opacity",
                1.0,
                0.0,
                TweenConfig(duration=duration, easing=easing, delay=delay),
            )
            for actor_name in actor_names
        )

        if len(tweens) == 1:
            self._builder.add_tween(tweens[0])
        else:
            self._builder.add_tween(ParallelTween(tweens=tweens))

        if start_time is None:
            self._current_time += duration  # Move forward in time

        return self

    def fade_in(
        self,
        *actor_names: str,
        duration: float = 0.5,
        easing: Optional[EasingFunction] = None,
        start_time: Optional[float] = None,
    ) -> Self:
        """
        Fade in actors by increasing opacity from zero to one.

        Args:
            *actor_names: Names of actors to fade in
            duration: Duration of fade in seconds (default 0.5)
            easing: Easing function (default ease_smooth_step)

        Returns:
            Self for method chaining

        Examples:
            >>> scene.fade_in("pelvis", duration=0.5)
        """
        if easing is None:
            easing = ease_smooth_step

        duration = duration / self.time_scale
        delay = (
            start_time / self.time_scale) if start_time is not None else self._current_time

        from osim_render.api.animation.property_tween import ActorPropertyTween

        tweens = tuple(
            ActorPropertyTween(
                actor_name,
                "opacity",
                0.0,
                1.0,
                TweenConfig(duration=duration, easing=easing, delay=delay),
            )
            for actor_name in actor_names
        )

        if len(tweens) == 1:
            self._builder.add_tween(tweens[0])
        else:
            self._builder.add_tween(ParallelTween(tweens=tweens))

        if start_time is None:
            self._current_time += duration  # Move forward in time

        return self

    def change_color(
        self,
        actor_name: str,
        start_color: ColorValue,
        end_color: ColorValue,
        duration: float = 1.0,
        easing: Optional[EasingFunction] = None,
        start_time: Optional[float] = None,
    ) -> Self:
        """
        Animate an actor's color from start to end.

        Args:
            actor_name: Name of the actor to recolor
            start_color: Starting ColorValue
            end_color: Ending ColorValue
            duration: Animation duration in seconds (default 1.0)
            easing: Easing function (default ease_smooth_step)
            start_time: Optional start time (if None, uses current time)

        Returns:
            Self for method chaining

        Examples:
            >>> red = ColorValue(r=1.0, g=0.0, b=0.0)
            >>> blue = ColorValue(r=0.0, g=0.0, b=1.0)
            >>> scene.change_color("pelvis", red, blue, duration=2.0)
            >>> scene.change_color("femur_r", red, blue, duration=1.0, start_time=0.5)
        """
        if easing is None:
            easing = ease_smooth_step

        scaled_duration = duration / self.time_scale
        if start_time is None:
            effective_delay = self._current_time
            advance = True
        else:
            effective_delay = start_time / self.time_scale
            advance = False

        tween = ColorTween(
            actor_name,
            start_color,
            end_color,
            TweenConfig(duration=scaled_duration,
                        easing=easing, delay=effective_delay),
        )
        self._builder.add_tween(tween)

        if advance:
            self._current_time += scaled_duration

        return self

    def animate_opacity(
        self,
        actor_name: str,
        start_opacity: float,
        end_opacity: float,
        duration: float = 1.0,
        easing: Optional[EasingFunction] = None,
        start_time: Optional[float] = None,
    ) -> Self:
        """
        Animate an actor's opacity (transparency).

        Args:
            actor_name: Name of the actor to animate
            start_opacity: Starting opacity (0.0 = transparent, 1.0 = opaque)
            end_opacity: Ending opacity
            duration: Animation duration in seconds (default 1.0)
            easing: Easing function (default ease_smooth_step)
            start_time: Optional start time (if None, uses current time)

        Returns:
            Self for method chaining

        Examples:
            >>> scene.animate_opacity("femur", 1.0, 0.5, duration=1.0)  # Semi-transparent
            >>> scene.animate_opacity("tibia", 0.0, 1.0, duration=1.0)  # Fade in
        """
        if easing is None:
            easing = ease_smooth_step

        scaled_duration = duration / self.time_scale
        if start_time is None:
            effective_delay = self._current_time
            advance = True
        else:
            effective_delay = start_time / self.time_scale
            advance = False

        from osim_render.api.animation.property_tween import ActorPropertyTween

        tween = ActorPropertyTween(
            actor_name,
            "opacity",
            start_opacity,
            end_opacity,
            TweenConfig(duration=scaled_duration,
                        easing=easing, delay=effective_delay),
        )
        self._builder.add_tween(tween)

        if advance:
            self._current_time += scaled_duration

        return self

    def highlight_actor(
        self,
        actor_name: str,
        highlight_color: Optional[ColorValue] = None,
        duration: float = 0.3,
        start_time: Optional[float] = None,
    ) -> Self:
        """
        Highlight an actor by changing its color.

        Args:
            actor_name: Name of the actor to highlight
            highlight_color: Color to highlight with (default: yellow/bright)
            duration: Duration of highlight in seconds (default 0.3)
            start_time: Absolute start time. If provided (including 0.0), seeks
                the scene cursor to that time before adding the highlight tweens.

        Returns:
            Self for method chaining

        Examples:
            >>> scene.highlight_actor("femur")  # Yellow highlight
            >>> red = ColorValue(r=1.0, g=0.0, b=0.0)
            >>> scene.highlight_actor("tibia", red, duration=0.5)
        """
        if highlight_color is None:
            # Default: bright yellow
            highlight_color = ColorValue(r=1.0, g=1.0, b=0.0, a=1.0)

        if start_time is not None:
            self._current_time = start_time / self.time_scale

        self.change_color(
            actor_name,
            ColorValue(r=0.5, g=0.5, b=0.5, a=1.0),
            highlight_color,
            duration=duration / 2,
        )
        self.change_color(
            actor_name,
            highlight_color,
            ColorValue(r=0.5, g=0.5, b=0.5, a=1.0),
            duration=duration / 2,
        )

        return self

    def show_actor(
        self, *actor_names: str, start_time: Optional[float] = None
    ) -> Self:
        """
        DEPRECATED: Use set_visibility() instead.

        Instantly show (make visible) actors.

        Args:
            *actor_names: Names of actors to show
            start_time: Optional start time (deprecated, ignored)

        Returns:
            Self for method chaining

        Examples:
            >>> scene.show_actor("pelvis", "femur", "tibia")
        """
        import warnings

        warnings.warn(
            "show_actor() is deprecated, use set_visibility() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        for actor_name in actor_names:
            self.set_visibility(actor_name, True)

        return self

    def hide_actor(
        self, *actor_names: str, start_time: Optional[float] = None
    ) -> Self:
        """
        DEPRECATED: Use set_visibility() instead.

        Instantly hide (make invisible) actors.

        Args:
            *actor_names: Names of actors to hide
            start_time: Optional start time (deprecated, ignored)

        Returns:
            Self for method chaining

        Examples:
            >>> scene.hide_actor("fibula", "patella")
        """
        import warnings

        warnings.warn(
            "hide_actor() is deprecated, use set_visibility() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        for actor_name in actor_names:
            self.set_visibility(actor_name, False)

        return self

    def pulse_opacity(
        self,
        actor_name: str,
        min_opacity: float = 0.3,
        max_opacity: float = 1.0,
        duration: float = 1.0,
        cycles: int = 1,
        easing: Optional[EasingFunction] = None,
        start_time: Optional[float] = None,
    ) -> Self:
        """
        Pulse an actor's opacity (fade in and out).

        Args:
            actor_name: Name of the actor to pulse
            min_opacity: Minimum opacity during pulse (default 0.3)
            max_opacity: Maximum opacity during pulse (default 1.0)
            duration: Total duration for one cycle in seconds (default 1.0)
            cycles: Number of pulse cycles (default 1)
            easing: Easing function (default ease_smooth_step)
            start_time: Absolute start time. If provided (including 0.0), seeks
                the scene cursor to that time before adding pulse tweens.

        Returns:
            Self for method chaining

        Examples:
            >>> scene.pulse_opacity("pelvis", min_opacity=0.2, max_opacity=1.0, cycles=3)
        """
        if easing is None:
            easing = ease_smooth_step

        half_duration = duration / 2.0

        if start_time is not None:
            self._current_time = start_time / self.time_scale

        for _ in range(cycles):
            self.animate_opacity(
                actor_name,
                min_opacity,
                max_opacity,
                duration=half_duration,
                easing=easing,
            )
            self.animate_opacity(
                actor_name,
                max_opacity,
                min_opacity,
                duration=half_duration,
                easing=easing,
            )

        return self


if __name__ == "__main__":
    print(f"[OK] {PropertyAnimationMixin.__name__} imports cleanly")
