from ..core import Dict as Dict, IS_PYPY as IS_PYPY, InternetNotAllowedError as InternetNotAllowedError, NeedDownloadError as NeedDownloadError, get_platform as get_platform, get_remote_file as get_remote_file, load_lib as load_lib, resource_dirs as resource_dirs
from _typeshed import Incomplete

logger: Incomplete
TEST_NUMPY_NO_STRIDES: bool
FNAME_PER_PLATFORM: Incomplete

def download(directory=None, force_download: bool = False) -> None: ...
def get_freeimage_lib(): ...
def efn(x): ...

GREY_PALETTE: Incomplete

class FI_TYPES:
    FIT_UNKNOWN: int
    FIT_BITMAP: int
    FIT_UINT16: int
    FIT_INT16: int
    FIT_UINT32: int
    FIT_INT32: int
    FIT_FLOAT: int
    FIT_DOUBLE: int
    FIT_COMPLEX: int
    FIT_RGB16: int
    FIT_RGBA16: int
    FIT_RGBF: int
    FIT_RGBAF: int
    dtypes: Incomplete
    fi_types: Incomplete
    extra_dims: Incomplete

class IO_FLAGS:
    FIF_LOAD_NOPIXELS: int
    BMP_DEFAULT: int
    BMP_SAVE_RLE: int
    CUT_DEFAULT: int
    DDS_DEFAULT: int
    EXR_DEFAULT: int
    EXR_FLOAT: int
    EXR_NONE: int
    EXR_ZIP: int
    EXR_PIZ: int
    EXR_PXR24: int
    EXR_B44: int
    EXR_LC: int
    FAXG3_DEFAULT: int
    GIF_DEFAULT: int
    GIF_LOAD256: int
    GIF_PLAYBACK: int
    HDR_DEFAULT: int
    ICO_DEFAULT: int
    ICO_MAKEALPHA: int
    IFF_DEFAULT: int
    J2K_DEFAULT: int
    JP2_DEFAULT: int
    JPEG_DEFAULT: int
    JPEG_FAST: int
    JPEG_ACCURATE: int
    JPEG_CMYK: int
    JPEG_EXIFROTATE: int
    JPEG_QUALITYSUPERB: int
    JPEG_QUALITYGOOD: int
    JPEG_QUALITYNORMAL: int
    JPEG_QUALITYAVERAGE: int
    JPEG_QUALITYBAD: int
    JPEG_PROGRESSIVE: int
    JPEG_SUBSAMPLING_411: int
    JPEG_SUBSAMPLING_420: int
    JPEG_SUBSAMPLING_422: int
    JPEG_SUBSAMPLING_444: int
    JPEG_OPTIMIZE: int
    JPEG_BASELINE: int
    KOALA_DEFAULT: int
    LBM_DEFAULT: int
    MNG_DEFAULT: int
    PCD_DEFAULT: int
    PCD_BASE: int
    PCD_BASEDIV4: int
    PCD_BASEDIV16: int
    PCX_DEFAULT: int
    PFM_DEFAULT: int
    PICT_DEFAULT: int
    PNG_DEFAULT: int
    PNG_IGNOREGAMMA: int
    PNG_Z_BEST_SPEED: int
    PNG_Z_DEFAULT_COMPRESSION: int
    PNG_Z_BEST_COMPRESSION: int
    PNG_Z_NO_COMPRESSION: int
    PNG_INTERLACED: int
    PNM_DEFAULT: int
    PNM_SAVE_RAW: int
    PNM_SAVE_ASCII: int
    PSD_DEFAULT: int
    PSD_CMYK: int
    PSD_LAB: int
    RAS_DEFAULT: int
    RAW_DEFAULT: int
    RAW_PREVIEW: int
    RAW_DISPLAY: int
    SGI_DEFAULT: int
    TARGA_DEFAULT: int
    TARGA_LOAD_RGB888: int
    TARGA_SAVE_RLE: int
    TIFF_DEFAULT: int
    TIFF_CMYK: int
    TIFF_PACKBITS: int
    TIFF_DEFLATE: int
    TIFF_ADOBE_DEFLATE: int
    TIFF_NONE: int
    TIFF_CCITTFAX3: int
    TIFF_CCITTFAX4: int
    TIFF_LZW: int
    TIFF_JPEG: int
    TIFF_LOGLUV: int
    WBMP_DEFAULT: int
    XBM_DEFAULT: int
    XPM_DEFAULT: int

class METADATA_MODELS:
    FIMD_COMMENTS: int
    FIMD_EXIF_MAIN: int
    FIMD_EXIF_EXIF: int
    FIMD_EXIF_GPS: int
    FIMD_EXIF_MAKERNOTE: int
    FIMD_EXIF_INTEROP: int
    FIMD_IPTC: int
    FIMD_XMP: int
    FIMD_GEOTIFF: int
    FIMD_ANIMATION: int

class METADATA_DATATYPE:
    FIDT_BYTE: int
    FIDT_ASCII: int
    FIDT_SHORT: int
    FIDT_LONG: int
    FIDT_RATIONAL: int
    FIDT_SBYTE: int
    FIDT_UNDEFINED: int
    FIDT_SSHORT: int
    FIDT_SLONG: int
    FIDT_SRATIONAL: int
    FIDT_FLOAT: int
    FIDT_DOUBLE: int
    FIDT_IFD: int
    FIDT_PALETTE: int
    FIDT_LONG8: int
    FIDT_SLONG8: int
    FIDT_IFD8: int
    dtypes: Incomplete

class Freeimage:
    def __init__(self) -> None: ...
    @property
    def lib(self): ...
    def has_lib(self): ...
    lib_version: Incomplete
    def load_freeimage(self) -> None: ...
    def __enter__(self): ...
    def __exit__(self, *args) -> None: ...
    def get_output_log(self): ...
    def getFIF(self, filename, mode, bb=None): ...
    def create_bitmap(self, filename, ftype, flags: int = 0): ...
    def create_multipage_bitmap(self, filename, ftype, flags: int = 0): ...

class FIBaseBitmap:
    def __init__(self, fi, filename, ftype, flags) -> None: ...
    def __del__(self) -> None: ...
    def close(self) -> None: ...
    def get_meta_data(self): ...
    def set_meta_data(self, metadata): ...

class FIBitmap(FIBaseBitmap):
    def allocate(self, array) -> None: ...
    def load_from_filename(self, filename=None) -> None: ...
    def save_to_filename(self, filename=None) -> None: ...
    def get_image_data(self): ...
    def set_image_data(self, array): ...
    def quantize(self, quantizer: int = 0, palettesize: int = 256): ...

class FIMultipageBitmap(FIBaseBitmap):
    def load_from_filename(self, filename=None) -> None: ...
    def save_to_filename(self, filename=None) -> None: ...
    def __len__(self) -> int: ...
    def get_page(self, index): ...
    def append_bitmap(self, bitmap) -> None: ...

fi: Incomplete
