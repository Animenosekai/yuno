import pymongo
import typing

IndexDirectionType = typing.Literal[1, -1, "2d", "geoHaystack", "2dsphere", "hashed", "text"]


class IndexDirection:
    ASCENDING = pymongo.ASCENDING
    DESCENDING = pymongo.DESCENDING
    GEO2D = pymongo.GEO2D
    GEOHAYSTACK = pymongo.GEOHAYSTACK
    GEOSPHERE = pymongo.GEOSPHERE
    HASHED = pymongo.HASHED
    TEXT = pymongo.TEXT
