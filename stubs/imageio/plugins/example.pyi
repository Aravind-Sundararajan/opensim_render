from .. import formats as formats
from ..core import Format as Format
from _typeshed import Incomplete

class DummyFormat(Format):
    class Reader(Format.Reader): ...
    class Writer(Format.Writer):
        def set_meta_data(self, meta) -> None: ...

format: Incomplete
