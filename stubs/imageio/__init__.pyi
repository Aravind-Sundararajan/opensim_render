from . import config as config, plugins as plugins, v2 as v2, v3 as v3
from .v2 import get_reader as get_reader, get_reader as read, get_writer as get_writer, get_writer as save, help as help, imwrite as imsave, imwrite as imwrite, mimread as mimread, mimwrite as mimsave, mimwrite as mimwrite, mvolread as mvolread, mvolwrite as mvolsave, mvolwrite as mvolwrite, volread as volread, volwrite as volsave, volwrite as volwrite
from .v3 import imiter as imiter, imopen as imopen
from _typeshed import Incomplete

__all__ = ['v2', 'v3', 'config', 'plugins', 'imopen', 'imread', 'imwrite', 'imiter', 'mimread', 'volread', 'mvolread', 'imwrite', 'mimwrite', 'volwrite', 'mvolwrite', 'read', 'save', 'imsave', 'mimsave', 'volsave', 'mvolsave', 'help', 'get_reader', 'get_writer', 'formats', 'show_formats']

formats: Incomplete
show_formats: Incomplete

def imread(uri, format=None, **kwargs): ...
