"""
Yuno  
A database and account management framework to complete Nasse.

> Manipulate your databases as if you never leaved Python!

© Anime no Sekai, 2022
"""

from .objects.dict import YunoDict
from .objects.list import YunoList
# from yuno.objects import YunoDict, YunoList


from .client import YunoClient
from .collection import YunoCollection
from .database import YunoDatabase
from .direction import SortDirection, IndexDirection
from .watch import Operation
from .launcher import MongoDB, LogConfig


__author__ = 'Anime no Sekai'
__copyright__ = 'Copyright 2022, yuno'
__credits__ = ['animenosekai']
__license__ = 'MIT License'
__version_tuple__ = (1, 0, 0)


def __version_string__():
    if isinstance(__version_tuple__[-1], str):
        return '.'.join(map(str, __version_tuple__[:-1])) + __version_tuple__[-1]
    return '.'.join(str(i) for i in __version_tuple__)


__version__ = 'yuno v{version}'.format(version=__version_string__())
__maintainer__ = 'Anime no Sekai'
__email__ = 'niichannomail@gmail.com'
__status__ = 'Beta'
