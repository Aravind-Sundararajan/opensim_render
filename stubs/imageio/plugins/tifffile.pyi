from ..core import Format as Format
from ..core.request import URI_BYTES as URI_BYTES, URI_FILE as URI_FILE
from _typeshed import Incomplete

TIFF_FORMATS: Incomplete
WRITE_METADATA_KEYS: Incomplete
READ_METADATA_KEYS: Incomplete

class TiffFormat(Format):
    class Reader(Format.Reader): ...
    class Writer(Format.Writer):
        def set_meta_data(self, meta) -> None: ...
