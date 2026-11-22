import numpy as np
from ..core.request import IOMode as IOMode, InitializationError as InitializationError, Request as Request
from ..core.v3_plugin_api import ImageProperties as ImageProperties, PluginV3 as PluginV3
from _typeshed import Incomplete
from datetime import datetime
from typing import Any, Callable, Iterator, Mapping, Sequence

logger: Incomplete

class Spec:
    basic: Incomplete
    metadata: Incomplete
    data_start: int
    dtypes: Incomplete
    controllers: Incomplete
    readout_modes: Incomplete
    no_decode: Incomplete

class SDTControlSpec:
    months: Incomplete
    sequence_types: Incomplete
    class CommentDesc:
        n: int
        slice: slice
        cvt: Callable[[str], Any]
        scale: None | float
        def __init__(self, n: int, slice: slice, cvt: Callable[[str], Any] = ..., scale: float | None = None) -> None: ...
    comment_fields: Incomplete
    @staticmethod
    def get_comment_version(comments: Sequence[str]) -> tuple[int, int]: ...
    @staticmethod
    def parse_comments(comments: Sequence[str], version: tuple[int, int]) -> dict[str, Any]: ...
    @staticmethod
    def get_datetime(date: str, time: str) -> datetime | None: ...
    @staticmethod
    def extract_metadata(meta: Mapping, char_encoding: str = 'latin1'): ...

class SpePlugin(PluginV3):
    def __init__(self, request: Request, check_filesize: bool = True, char_encoding: str | None = None, sdt_meta: bool | None = None) -> None: ...
    def read(self, *, index: int = ...) -> np.ndarray: ...
    def iter(self) -> Iterator[np.ndarray]: ...
    def metadata(self, index: int = ..., exclude_applied: bool = True, char_encoding: str = 'latin1', sdt_control: bool = True) -> dict[str, Any]: ...
    def properties(self, index: int = ...) -> ImageProperties: ...

def roi_array_to_dict(a: np.ndarray) -> list[dict[str, list[int]]]: ...
