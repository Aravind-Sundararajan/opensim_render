from .tifffile import TiffFormat as TiffFormat

class FEISEMFormat(TiffFormat):
    class Reader(TiffFormat.Reader): ...
