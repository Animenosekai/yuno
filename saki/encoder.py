import io
import typing

from nasse import logging, utils

from saki import objects


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
        if isinstance(o, (str, int, float, bool, bytes)):
            return o
        elif o is None:
            return None
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


class SakiTypeEncoder():
    BSON_SAFE_ENCODER = SakiBSONEncoder()
    DICT = objects.SakiDict
    LIST = objects.SakiList

    def encode_dict(self, o: dict[typing.Any, typing.Any], _type: T, field: str = "", document=None) -> T:
        _types = typing.get_args(_type)
        length = len(_types)
        if length <= 0:
            return self.DICT(field=field, saki_document=document, values={key: self.default(val, None, field="{}.{}".format(field, key), document=document) for key, val in dict(o).items()})
        elif length <= 2:
            key__type, value__type = (str, _types[0]) if length == 1 else (_types[0], _types[1])
            return self.DICT(field=field, saki_document=document, values={self.default(k, key__type): self.default(v, value__type, field="{}.{}".format(field, k)) for k, v in o.items()})
        length -= 1
        for index, (key, value) in enumerate(o.items()):
            if length > index:
                o[str(key)] = self.default(value, _types[index], field="{}.{}".format(field, key), document=document)
            else:
                o[str(key)] = self.default(value, _types[length], field="{}.{}".format(field, key), document=document)
        return self.DICT(field=field, saki_document=document, values=o)

    def encode_iterable(self, i: typing.Iterable[typing.Any], _type: T, field: str = "", document=None) -> T:
        _types = typing.get_args(_type)
        length = len(_types)
        if length <= 0:
            return self.LIST(field, document, [self.default(val, None, field="{}.{}".format(field, index), document=document) for index, val in enumerate(i)])
        length -= 1
        for index, value in enumerate(i):
            if length > index:
                i[index] = self.default(value, _types[index], field="{}.{}".format(field, index), document=document)
            else:
                i[index] = self.default(value, _types[length], field="{}.{}".format(field, index), document=document)
        return self.LIST(field, document, i)

    def encode_file(self, f: io.BytesIO, _type: T) -> T:
        position = f.tell()  # storing the current position
        content = f.read()  # read it (place the cursor at the end)
        f.seek(position)  # go back to the original position
        return self.default(content, _type)

    def default(self, o: typing.Any, _type: T = None, field: str = "", document=None) -> T:
        if _type is None:
            _type = type(o)

        IMMUTABLES = (str, int, float, bool, bytes)
        if issubclass(_type, IMMUTABLES) or isinstance(_type, IMMUTABLES):
            return _type(o)

        origin = typing.get_origin(_type)
        if origin is not None:
            if issubclass(origin, dict) or isinstance(origin, dict):
                return self.encode_dict(o, _type, field, document)
            elif issubclass(origin, typing.Iterable) or isinstance(origin, typing.Iterable):
                return self.encode_iterable(o, _type, field, document)
            return _type(o)

        if issubclass(_type, dict) or isinstance(_type, dict):
            return self.encode_dict(o, _type, field, document)
        elif issubclass(_type, typing.Iterable) or isinstance(_type, typing.Iterable):
            return self.encode_iterable(o, _type, field, document)

        if hasattr(o, "read") and hasattr(o, "tell") and hasattr(o, "seek"):
            return self.encode_file(o, _type)

        return _type(o)


BSONEncoder = SakiBSONEncoder()
TypeEncoder = SakiTypeEncoder()
