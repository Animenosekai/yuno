import pymongo
import typing

IndexDirectionType = typing.Literal[1, -1, "2d", "geoHaystack", "2dsphere", "hashed", "text"]
"""
Index direction type.
This is the type of direction to use when creating an index.

Example
-------
>>> from saki.direction import IndexDirectionType
>>> IndexDirectionType.ASCENDING
1
>>> collection.index("username", IndexDirectionType.ASCENDING)
"""
SortDirectionType = typing.Literal[1, -1]
"""
Sort direction type.
This is the type of direction to use when sorting.

Example
-------
>>> from saki.direction import SortDirectionType
>>> SortDirectionType.ASCENDING
1
>>> collection.find(username="Anise", sort=[("age", SortDirectionType.ASCENDING)])
"""


class IndexDirection:
    """
    An enum for index directions

    Example
    -------
    >>> from saki.direction import IndexDirection
    >>> IndexDirection.ASCENDING
    1
    """
    ASCENDING = pymongo.ASCENDING
    DESCENDING = pymongo.DESCENDING
    GEO2D = pymongo.GEO2D
    GEOHAYSTACK = pymongo.GEOHAYSTACK
    GEOSPHERE = pymongo.GEOSPHERE
    HASHED = pymongo.HASHED
    TEXT = pymongo.TEXT


class SortDirection:
    """
    An enum for sort directions

    Example
    -------
    >>> from saki.direction import SortDirection
    >>> SortDirection.ASCENDING
    1
    """
    ASCENDING = pymongo.ASCENDING
    DESCENDING = pymongo.DESCENDING
