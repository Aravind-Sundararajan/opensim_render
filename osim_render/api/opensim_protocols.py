"""Structural Protocols for OpenSim objects.

Centralises all Protocol definitions for OpenSim API objects so visualizers
and loaders share one source of truth. VTK objects and OpenSim collection
types (BodySet, etc.) remain typed as Any — they have no usable Python stubs.
"""

from __future__ import annotations

from typing import Any, Protocol


class Vec3Protocol(Protocol):
    """Protocol for OpenSim Vec3."""

    def get(self, index: int) -> float:
        ...


class Mat33Protocol(Protocol):
    """Protocol for OpenSim Mat33."""

    def get(self, i: int, j: int) -> float:
        ...


class RotationProtocol(Protocol):
    """Protocol for OpenSim Rotation."""

    def asMat33(self) -> Mat33Protocol:
        ...


class TransformProtocol(Protocol):
    """Protocol for OpenSim Transform."""

    def R(self) -> RotationProtocol:
        ...

    def p(self) -> Vec3Protocol:
        ...

    def compose(self, other: TransformProtocol) -> TransformProtocol:
        ...


class StateProtocol(Protocol):
    """Opaque protocol for OpenSim State — passed through to OpenSim methods."""

    pass


class FrameProtocol(Protocol):
    """Protocol for OpenSim Frame objects."""

    def getName(self) -> str:
        ...

    def getTransformInGround(self, state: StateProtocol) -> TransformProtocol:
        ...


class ModelProtocol(Protocol):
    """Protocol for OpenSim Model objects."""

    def getName(self) -> str:
        ...

    def getBodySet(self) -> Any:
        ...

    def getBodyList(self) -> Any:
        ...

    def getCoordinateSet(self) -> Any:
        ...

    def getContactGeometrySet(self) -> Any:
        ...

    def getJointSet(self) -> Any:
        ...

    def getJointList(self) -> Any:
        ...

    def getMuscles(self) -> Any:
        ...

    def getGround(self) -> FrameProtocol:
        ...

    def realizePosition(self, state: StateProtocol) -> None:
        ...
