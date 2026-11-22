"""
Tweens for animating visual properties of actors.

Allows animation of actor properties like color, opacity, and visibility
to create effects like fading, color transitions, and more.
"""

from dataclasses import dataclass
from typing import Union

from osim_render.api.animation.interpolation import lerp
from osim_render.api.animation.tween import TweenConfig, compute_eased_progress
from osim_render.api.animation.value_types import ColorValue


@dataclass(frozen=True)
class ActorPropertyTween:
    """
    Tween for animating a single visual property of an actor.

    Supports animation of properties like 'color', 'opacity', 'visibility', etc.
    Property values can be colors, floats, or booleans.

    Attributes:
        actor_name: Name of the actor to modify
        property_name: Name of the property ('color', 'opacity', 'visibility')
        start_value: Starting value (ColorValue, float, or bool)
        end_value: Ending value (ColorValue, float, or bool)
        config: TweenConfig with duration, easing, and delay

    Examples:
        >>> # Fade out effect (animate opacity)
        >>> tween = ActorPropertyTween(
        ...     actor_name="pelvis",
        ...     property_name="opacity",
        ...     start_value=1.0,
        ...     end_value=0.0,
        ...     config=TweenConfig(duration=1.0)
        ... )
        >>> # After 0.5 seconds: returns {"pelvis": {"opacity": 0.5}}
        >>> tween.compute_value(0.5)
        {'pelvis': {'opacity': 0.5}}
    """

    actor_name: str
    property_name: str
    start_value: Union[ColorValue, float, bool]
    end_value: Union[ColorValue, float, bool]
    config: TweenConfig

    def __post_init__(self) -> None:
        """Validate that start and end values are compatible types."""
        start_type = type(self.start_value)
        end_type = type(self.end_value)
        if start_type != end_type:
            raise TypeError(
                f"start_value and end_value must be same type. "
                f"Got {start_type} and {end_type}"
            )

    @property
    def duration(self) -> float:
        """Total duration of the tween in seconds."""
        return self.config.duration + self.config.delay

    def compute_value(
        self, elapsed_time: float
    ) -> dict[str, dict[str, Union[float, ColorValue]]]:
        """
        Compute the property value at the given elapsed time.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            Dictionary with structure {actor_name: {property_name: value}}
        """
        progress = compute_eased_progress(self.config, elapsed_time)

        # Interpolate based on value type
        if isinstance(self.start_value, ColorValue) and isinstance(
            self.end_value, ColorValue
        ):
            # Interpolate color channels
            color_value = ColorValue(
                r=lerp(self.start_value.r, self.end_value.r, progress),
                g=lerp(self.start_value.g, self.end_value.g, progress),
                b=lerp(self.start_value.b, self.end_value.b, progress),
                a=lerp(self.start_value.a, self.end_value.a, progress),
            )
            return {self.actor_name: {self.property_name: color_value}}
        elif isinstance(self.start_value, float) and isinstance(self.end_value, float):
            # Linear interpolation for numeric properties
            float_value = lerp(self.start_value, self.end_value, progress)
            return {self.actor_name: {self.property_name: float_value}}
        elif isinstance(self.start_value, bool) and isinstance(self.end_value, bool):
            # Binary switch at midpoint for boolean properties
            bool_value = self.end_value if progress >= 0.5 else self.start_value
            # Convert to float for consistency with return type
            return {self.actor_name: {self.property_name: float(bool_value)}}
        else:
            raise TypeError(f"Unsupported value type: {type(self.start_value)}")

    def is_complete(self, elapsed_time: float) -> bool:
        """
        Check if the animation is complete.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            True if elapsed_time >= duration + delay
        """
        return elapsed_time >= self.duration


@dataclass(frozen=True)
class ColorTween:
    """
    Convenience tween for animating an actor's color.

    Specialization of ActorPropertyTween for color animation.

    Attributes:
        actor_name: Name of the actor to modify
        start_color: Starting ColorValue
        end_color: Ending ColorValue
        config: TweenConfig with duration, easing, and delay

    Examples:
        >>> start = ColorValue(r=1.0, g=0.0, b=0.0)  # Red
        >>> end = ColorValue(r=0.0, g=0.0, b=1.0)    # Blue
        >>> tween = ColorTween("pelvis", start, end, TweenConfig(duration=2.0))
        >>> # After 1 second: returns purple-ish color
        >>> tween.compute_value(1.0)
    """

    actor_name: str
    start_color: ColorValue
    end_color: ColorValue
    config: TweenConfig

    @property
    def duration(self) -> float:
        """Total duration of the tween in seconds."""
        return self.config.duration + self.config.delay

    def compute_value(self, elapsed_time: float) -> dict[str, dict[str, ColorValue]]:
        """
        Compute the color value at the given elapsed time.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            Dictionary with structure {actor_name: {'color': ColorValue}}
        """
        progress = compute_eased_progress(self.config, elapsed_time)

        color = ColorValue(
            r=lerp(self.start_color.r, self.end_color.r, progress),
            g=lerp(self.start_color.g, self.end_color.g, progress),
            b=lerp(self.start_color.b, self.end_color.b, progress),
            a=lerp(self.start_color.a, self.end_color.a, progress),
        )

        return {self.actor_name: {"color": color}}

    def is_complete(self, elapsed_time: float) -> bool:
        """
        Check if the animation is complete.

        Args:
            elapsed_time: Time elapsed since animation start in seconds

        Returns:
            True if elapsed_time >= duration + delay
        """
        return elapsed_time >= self.duration


if __name__ == "__main__":
    # Smoke tests
    print("Testing property_tween module...")

    # Test ActorPropertyTween with opacity
    tween = ActorPropertyTween(
        actor_name="pelvis",
        property_name="opacity",
        start_value=1.0,
        end_value=0.0,
        config=TweenConfig(duration=1.0),
    )

    result = tween.compute_value(0.0)
    assert result == {"pelvis": {"opacity": 1.0}}
    print("[PASS] ActorPropertyTween at t=0 returns start opacity")

    result = tween.compute_value(0.5)
    assert result["pelvis"]["opacity"] == 0.5
    print("[PASS] ActorPropertyTween at t=0.5 returns 0.5 opacity")

    result = tween.compute_value(1.0)
    assert result == {"pelvis": {"opacity": 0.0}}
    print("[PASS] ActorPropertyTween at t=1 returns end opacity")

    # Test ActorPropertyTween with color
    red = ColorValue(r=1.0, g=0.0, b=0.0)
    blue = ColorValue(r=0.0, g=0.0, b=1.0)
    color_tween = ActorPropertyTween(
        actor_name="femur",
        property_name="color",
        start_value=red,
        end_value=blue,
        config=TweenConfig(duration=1.0),
    )

    result = color_tween.compute_value(0.0)
    assert isinstance(result["femur"]["color"], ColorValue)
    assert result["femur"]["color"].r > 0.99
    print("[PASS] ActorPropertyTween with color at t=0 returns red")

    result = color_tween.compute_value(0.5)
    color_val = result["femur"]["color"]
    assert isinstance(color_val, ColorValue)
    assert color_val.r > 0.4 and color_val.r < 0.6  # Should be purple-ish
    assert color_val.b > 0.4 and color_val.b < 0.6
    print("[PASS] ActorPropertyTween with color at t=0.5 returns purple")

    # Test ColorTween
    color_tween_simple = ColorTween(
        actor_name="tibia",
        start_color=red,
        end_color=blue,
        config=TweenConfig(duration=1.0),
    )

    result_color_start = color_tween_simple.compute_value(0.0)
    assert isinstance(result_color_start["tibia"]["color"], ColorValue)
    assert result_color_start["tibia"]["color"].r > 0.99
    print("[PASS] ColorTween at t=0 returns start color")

    result_color_end = color_tween_simple.compute_value(1.0)
    color_end = result_color_end["tibia"]["color"]
    assert isinstance(color_end, ColorValue)
    assert color_end.b > 0.99
    print("[PASS] ColorTween at t=1 returns end color")

    print("\n[PASS] All property_tween tests passed!")
