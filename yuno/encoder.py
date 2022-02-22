

import datetime
import io
import re
import typing

import bson
from yuno import utils

# from yuno.objects.dict import YunoDict


class LazyObject():
    """
    An object representing a lazy loaded value in an object.
    """

    def __init__(self, field: str) -> None:
        self.field = str(field).strip(".")

    def __repr__(self) -> str:
        return "LazyObject({})".format(self.field)


BSON_ENCODABLE = (bool, int, bson.Int64, float, str, bytes, datetime.datetime, bson.Regex,
                  re.Pattern, bson.Binary, bson.ObjectId, bson.DBRef, bson.Code)


def get_annotations(o: object):
    """
    Internal function to get the annotations of an object.

    Parameters
    ----------
    o : object
        The object to get the annotations of.

    Returns
    -------
    dict[str, Any]
        The annotations of the object.
    """
    return o.__annotations__ if hasattr(o, "__annotations__") else {}


class YunoBSONEncoder():
    """
    The custom BSON encoder
    """

    def __init__(self) -> None:
        """To initialize the encoder."""
        from yuno import object  # noqa
        self.object = object.YunoObject

    def encode_dict(self, o: typing.Dict[typing.Any, typing.Any]):
        """Correctly encoding an unpackable value"""
        return {str(k): self.default(v) for k, v in o.items()}

    def encode_iterable(self, i: typing.Iterable[typing.Any]):
        """Encoding an iterable value"""
        return [self.default(x) for x in i]

    def encode_file(self, f: io.BytesIO):
        """Correctly encoding a file."""
        position = f.tell()  # storing the current position
        content = f.read()  # read it (place the cursor at the end)
        f.seek(position)  # go back to the original position
        if "b" in f.mode:  # if binary mode
            return content
        return str(content)

    def default(self, o: typing.Any) -> typing.Any:
        """Encodes any value"""
        if o is None:
            return None
        if isinstance(o, self.object):
            o = o.__storage__
        # https://pymongo.readthedocs.io/en/stable/api/bson/index.html
        elif isinstance(o, BSON_ENCODABLE):
            return o
        elif hasattr(o, "read") and hasattr(o, "tell") and hasattr(o, "seek"):
            return self.encode_file(o)
        elif utils.unpack.is_unpackable(o):
            return self.encode_dict(o)
        elif isinstance(o, typing.Iterable):
            return self.encode_iterable(o)
        else:
            utils.logging.log("Object of type <{_type}> will be converted to str while encoding to JSON".format(_type=o.__class__.__name__))
            return str(o)


T = typing.TypeVar("T")

IMMUTABLES = (bool, int, bson.Int64, float, str, bson.Binary, bson.ObjectId, bson.DBRef, bson.Code)


class YunoTypeEncoder():
    """
    The custom type encoder
    """

    def __init__(self) -> None:
        """To initialize the encoder."""
        from yuno import objects
        self.dict = objects.YunoDict
        self.list = objects.YunoList
        self.bson_encoder = YunoBSONEncoder()

    def encode_dict(self, o: typing.Dict[typing.Any, typing.Any], _type: T, field: str = "", collection=None, _id: str = None) -> T:
        """Correctly encoding an unpackable value"""
        types = typing.get_args(_type)
        length = len(types)
        CAST = self.dict if not issubclass(_type, self.dict) else _type
        if length <= 0:
            return CAST(_id=_id, collection=collection, field=field, data={key: self.default(o=val, _type=get_annotations(CAST).get(key, None), field="{}.{}".format(field, key), collection=collection, _id=_id) for key, val in dict(o).items()})
        elif length <= 2:
            key__type, value__type = (str, types[0]) if length == 1 else (types[0], types[1])
            return CAST(_id=_id, collection=collection, field=field, data={self.default(k, key__type): self.default(v, value__type, field="{}.{}".format(field, k), collection=collection, _id=_id) for k, v in dict(o).items()})
            # return self.DICT(field=field, yuno_document=document, values={self.default(k, key__type): self.default(v, value__type, field="{}.{}".format(field, k)) for k, v in o.items()})
        length -= 1
        for index, (key, value) in enumerate(o.items()):
            if length > index:
                o[str(key)] = self.default(o=value, _type=types[index], field="{}.{}".format(field, key), collection=collection, _id=_id)
            else:
                o[str(key)] = self.default(o=value, _type=types[length], field="{}.{}".format(field, key), collection=collection, _id=_id)
        return CAST(_id=_id, collection=collection, field=field, data=o)

    def encode_iterable(self, i: typing.Iterable[typing.Any], _type: T, field: str = "", collection=None, _id: str = None) -> T:
        """Encoding an iterable value"""
        _types = typing.get_args(_type)
        length = len(_types)
        CAST = self.list if not issubclass(_type, self.list) else _type
        if length <= 0:
            return CAST(_id=_id, collection=collection, field=field, data=[self.default(o=val, _type=get_annotations(CAST).get(index, None), field="{}.{}".format(field, index), collection=collection, _id=_id) for index, val in enumerate(i)])
        length -= 1
        for index, value in enumerate(i):
            if length > index:
                i[index] = self.default(value, _types[index], field="{}.{}".format(field, index), collection=collection, _id=_id)
            else:
                i[index] = self.default(value, _types[length], field="{}.{}".format(field, index), collection=collection, _id=_id)
        return CAST(_id=_id, collection=collection, field=field, data=i)

    def default(self, o: typing.Any, _type: T = None, field: str = "", collection=None, _id: str = None) -> T:
        """Encodes any value"""
        if isinstance(o, LazyObject):
            return LazyObject(field.split(".")[-1])

        given_type = _type

        if _type is None:
            _type = type(o)

        # IMMUTABLES = (str, int, float, bool, bytes)
        if isinstance(_type, IMMUTABLES):
            _type = _type.__class__

        if issubclass(_type, IMMUTABLES):
            return _type(o)

        origin = typing.get_origin(_type)
        if origin is not None:
            if issubclass(origin, dict) or isinstance(origin, dict):
                return self.encode_dict(o=o, _type=_type, field=field, collection=collection, _id=_id)
            elif issubclass(origin, typing.Iterable) or isinstance(origin, typing.Iterable):
                return self.encode_iterable(i=o, _type=_type, field=field, collection=collection, _id=_id)
            return _type(o)

        if issubclass(_type, dict) or isinstance(_type, dict):
            return self.encode_dict(o=o, _type=_type, field=field, collection=collection, _id=_id)
        elif issubclass(_type, typing.Iterable) or isinstance(_type, typing.Iterable):
            return self.encode_iterable(i=o, _type=_type, field=field, collection=collection, _id=_id)

        if given_type is None:
            return o

        return _type(o)


# BSONEncoder = YunoBSONEncoder()
# TypeEncoder = YunoTypeEncoder()
