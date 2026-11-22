from ..config import known_plugins as known_plugins
from ..config.extensions import known_extensions as known_extensions
from .request import IOMode as IOMode, InitializationError as InitializationError, Request as Request, SPECIAL_READ_URIS as SPECIAL_READ_URIS, URI_FILENAME as URI_FILENAME

def imopen(uri, io_mode, *, plugin=None, extension=None, format_hint=None, legacy_mode: bool = False, **kwargs): ...
