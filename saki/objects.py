import typing

from saki import encoder


class SakiList(list):
    def __init__(self, field: str, saki_document, values: typing.Iterable[typing.Any] = None) -> None:
        self.__document__ = saki_document
        self.__field__ = str(field)

        if values is None:
            data = saki_document.__collection__.find({"_id": saki_document._id}, {field: 1})
            if data is None:
                self.__storage__ = []
            else:
                self.__storage__ = data[field]
        else:
            self.__storage__ = values

    def append(self, o: typing.Any) -> None:
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$push": {self.__field__: encoder.BSONEncoder.default(o)}})
        self.__storage__.append(o)

    def clear(self) -> None:
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: []}})
        self.__storage__.clear()

    def extend(self, iterable: typing.Iterable[typing.Any]) -> None:
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {
                                                    "$push": {self.__field__: {"$each": encoder.BSONEncoder.default(iterable)}}})
        self.__storage__.extend(iterable)

    def pop(self, index: typing.SupportsIndex = ...) -> typing.Any:
        copied = self.__storage__.copy()
        value = copied.pop(index)
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: copied}})
        self.__storage__ = copied
        return value

    def remove(self, value: typing.Any) -> None:
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$pull": {self.__field__: encoder.BSONEncoder.default(value)}})
        try:
            self.__storage__.remove(value)
        except ValueError:  # they are not raised by MongoDB
            pass

    def reverse(self) -> None:
        copied = self.__storage__.copy()
        copied.reverse()
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: copied}})
        self.__storage__ = copied

    def sort(self, key: typing.Callable[[typing.Any], typing.Any] = None, reverse: bool = False) -> None:
        copied = self.__storage__.copy()
        copied.sort(key=key, reverse=reverse)
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: copied}})
        self.__storage__ = copied

    def __repr__(self) -> str:
        return "SakiList({})".format(self.__storage__.__repr__())

    def __iadd__(self, x: list[typing.Any]) -> list[typing.Any]:
        self.append(x)
        return self

    def __imul__(self, x: int) -> list[typing.Any]:
        copied = self.__storage__ * x
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: copied}})
        self.__storage__ = copied
        return self

    def __setitem__(self, key: typing.Union[int, slice], value: typing.Any) -> None:
        if isinstance(key, slice):
            copied = self.__storage__.__setitem__(key, value)
            self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: copied}})
            self.__storage__ = copied
        else:
            try:
                key = int(key)
                self.__document__.__collection__.update_one({"_id": self.__document__._id}, {
                                                            "$set": {"{}.{}".format(self.__field__, key): encoder.BSONEncoder.default(value)}})
                self.__storage__.__setitem__(key, value)
            except ValueError as err:
                raise TypeError("list indices must be integers or slices, not str") from err

    def __delitem__(self, key: typing.Union[int, slice]) -> None:
        self.pop(key)

    def __getattr__(self, name: str) -> typing.Any:
        return self.__storage__.__getattribute__(name)


class SakiDict(dict):
    pass
