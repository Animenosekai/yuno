import pymongo

class IndexDirection:
    ASCENDING = pymongo.ASCENDING
    DESCENDING = pymongo.DESCENDING
    GEO2D = pymongo.GEO2D
    GEOHAYSTACK = pymongo.GEOHAYSTACK
    GEOSPHERE = pymongo.GEOSPHERE
    HASHED = pymongo.HASHED
    TEXT = pymongo.TEXT
