import os
from redbot.core.utils.dataIO import fileIO as _fileIO


module_path = os.path.dirname(os.path.abspath(__file__))


def munge_path(*paths):
    return os.path.join(module_path, "data", *paths)


def fileIO(path, *args):
    return _fileIO(munge_path(path), *args)
