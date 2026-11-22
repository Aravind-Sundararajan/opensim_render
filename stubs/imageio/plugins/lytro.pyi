from ..core import Format as Format
from ..v2 import imread as imread
from _typeshed import Incomplete

logger: Incomplete
LYTRO_ILLUM_IMAGE_SIZE: Incomplete
LYTRO_F01_IMAGE_SIZE: Incomplete
HEADER_LENGTH: int
SIZE_LENGTH: int
SHA1_LENGTH: int
PADDING_LENGTH: int
DATA_CHUNKS_ILLUM: int
DATA_CHUNKS_F01: int

class LytroFormat(Format):
    class Writer(Format.Writer): ...

class LytroIllumRawFormat(LytroFormat):
    @staticmethod
    def rearrange_bits(array): ...
    class Reader(Format.Reader): ...

class LytroLfrFormat(LytroFormat):
    class Reader(Format.Reader): ...

class LytroF01RawFormat(LytroFormat):
    @staticmethod
    def rearrange_bits(array): ...
    class Reader(Format.Reader): ...

class LytroLfpFormat(LytroFormat):
    class Reader(Format.Reader): ...
