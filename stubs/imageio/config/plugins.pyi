from ..core.legacy_plugin_wrapper import LegacyPlugin as LegacyPlugin
from _typeshed import Incomplete

class PluginConfig:
    name: Incomplete
    class_name: Incomplete
    module_name: Incomplete
    package_name: Incomplete
    is_legacy: Incomplete
    install_name: Incomplete
    legacy_args: Incomplete
    def __init__(self, name, class_name, module_name, *, is_legacy: bool = False, package_name=None, install_name=None, legacy_args=None) -> None: ...
    @property
    def format(self): ...
    @property
    def plugin_class(self): ...

known_plugins: Incomplete
PILLOW_FORMATS: Incomplete
config: Incomplete
lytro_formats: Incomplete
FREEIMAGE_FORMATS: Incomplete
