from _typeshed import Incomplete

class FileExtension:
    extension: Incomplete
    priority: Incomplete
    name: Incomplete
    description: Incomplete
    external_link: Incomplete
    default_priority: Incomplete
    volume_support: Incomplete
    def __init__(self, *, extension, priority, name=None, description=None, external_link=None, volume_support: bool = False) -> None: ...
    def reset(self) -> None: ...

extension_list: Incomplete
known_extensions: Incomplete
video_extensions: Incomplete
formats = known_extensions[ext_string]
