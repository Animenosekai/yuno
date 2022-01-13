import datetime
import io
import re
import typing

import bson
from nasse import logging, utils

from saki import objects


class LazyObject():
    def __init__(self, field: str) -> None:
        self.field = str(field)

    def __repr__(self) -> str:
        return "LazyObject({})".format(self.field)


BSON_ENCODABLE = (bool, int, bson.Int64, float, str, datetime.datetime, bson.Regex, re.Pattern, bson.Binary, bson.ObjectId, bson.DBRef, bson.Code)


class SakiBSONEncoder():
    def encode_dict(self, o: dict[typing.Any, typing.Any]):
        return {str(k): self.default(v) for k, v in o.items()}

    def encode_iterable(self, i: typing.Iterable[typing.Any]):
        return [self.default(x) for x in i]

    def encode_file(self, f: io.BytesIO):
        position = f.tell()  # storing the current position
        content = f.read()  # read it (place the cursor at the end)
        f.seek(position)  # go back to the original position
        if "b" in f.mode:  # if binary mode
            return content
        return str(content)

    def default(self, o: typing.Any) -> typing.Any:
        if o is None:
            return None
        # https://pymongo.readthedocs.io/en/stable/api/bson/index.html
        elif isinstance(o, BSON_ENCODABLE):
            return o
        elif hasattr(o, "read") and hasattr(o, "tell") and hasattr(o, "seek"):
            return self.encode_file(o)
        elif utils.annotations.is_unpackable(o):
            return self.encode_dict(o)
        elif isinstance(o, typing.Iterable):
            return self.encode_iterable(o)
        else:
            logging.log("Object of type <{_type}> will be converted to str while encoding to JSON".format(
                _type=o.__class__.__name__))
            return str(o)


T = typing.TypeVar("T")

IMMUTABLES = (bool, int, bson.Int64, float, str, bson.Binary, bson.ObjectId, bson.DBRef, bson.Code)


class SakiTypeEncoder():
    BSON_SAFE_ENCODER = SakiBSONEncoder()
    DICT = objects.SakiDict
    LIST = objects.SakiList

    def encode_dict(self, o: dict[typing.Any, typing.Any], _type: T, field: str = "", collection=None, _id: str = None) -> T:
        types = typing.get_args(_type)
        length = len(types)
        if length <= 0:
            return objects.SakiDict(_id=_id, collection=collection, field=field, data={key: self.default(o=val, _type=None, field="{}.{}".format(field, key), collection=collection, _id=_id) for key, val in dict(o).items()})
        elif length <= 2:
            key__type, value__type = (str, types[0]) if length == 1 else (types[0], types[1])
            return objects.SakiDict(_id=_id, collection=collection, field=field, data={self.default(k, key__type): self.default(v, value__type, field="{}.{}".format(field, k), collection=collection, _id=_id) for k, v in dict(o).items()})
            # return self.DICT(field=field, saki_document=document, values={self.default(k, key__type): self.default(v, value__type, field="{}.{}".format(field, k)) for k, v in o.items()})
        length -= 1
        for index, (key, value) in enumerate(o.items()):
            if length > index:
                o[str(key)] = self.default(o=value, _type=types[index], field="{}.{}".format(field, key), collection=collection, _id=_id)
            else:
                o[str(key)] = self.default(o=value, _type=types[length], field="{}.{}".format(field, key), collection=collection, _id=_id)
        return objects.SakiDict(_id=_id, collection=collection, field=field, data=o)

    def encode_iterable(self, i: typing.Iterable[typing.Any], _type: T, field: str = "", collection=None, _id: str = None) -> T:
        _types = typing.get_args(_type)
        length = len(_types)
        if length <= 0:
            return objects.SakiList(_id=_id, collection=collection, field=field, data=[self.default(val, None, field="{}.{}".format(field, index), collection=collection, _id=_id) for index, val in enumerate(i)])
        length -= 1
        for index, value in enumerate(i):
            if length > index:
                i[index] = self.default(value, _types[index], field="{}.{}".format(field, index), collection=collection, _id=_id)
            else:
                i[index] = self.default(value, _types[length], field="{}.{}".format(field, index), collection=collection, _id=_id)
        return objects.SakiList(_id=_id, collection=collection, field=field, data=i)

    def default(self, o: typing.Any, _type: T = None, field: str = "", collection=None, _id: str = None) -> T:
        if isinstance(o, LazyObject):
            return LazyObject(field.split(".")[-1])

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

        return _type(o)


BSONEncoder = SakiBSONEncoder()
TypeEncoder = SakiTypeEncoder()
