import typing

from saki import encoder
from nasse.utils.annotations import Default

Any = typing.TypeVar("Any")

# TODO: Update some functions to avoid using dict.copy() and list.copy() and take up less memory.


class SakiList(list):
    __overwritten__ = ("__init__", "append", "clear", "extend", "pop", "remove", "reverse", "sort", "__repr__", "__iadd__", "__imul__",
                       "__setitem__", "__delitem__", "__document__", "__field__", "__storage__", "__overwritten__", "__contains__")  # the last ones are more of added attributes

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

        storage = super().__getattribute__("__storage__")
        overwritten = super().__getattribute__("__overwritten__")
        for attribute in dir(list):
            if attribute not in overwritten and attribute != "__class__":  # __class__ cannot be overwritten
                super().__setattr__(attribute, storage.__getattribute__(attribute))  # if this fails, __storage__ is not a list, which should not happen

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
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
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
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        self.__storage__ = copied

    def sort(self, key: typing.Callable[[typing.Any], typing.Any] = None, reverse: bool = False) -> None:
        copied = self.__storage__.copy()
        copied.sort(key=key, reverse=reverse)
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        self.__storage__ = copied

    def __repr__(self) -> str:
        return "SakiList({})".format(self.__storage__.__repr__())

    def __iadd__(self, x: list[typing.Any]) -> list[typing.Any]:
        self.append(x)
        return self

    def __imul__(self, x: int) -> list[typing.Any]:
        copied = self.__storage__ * x
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        self.__storage__ = copied
        return self

    def __setitem__(self, key: typing.Union[int, slice], value: typing.Any) -> None:
        if isinstance(key, slice):
            copied = self.__storage__.__setitem__(key, value)
            self.__document__.__collection__.update_one({"_id": self.__document__._id}, {
                                                        "$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
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

    def __contains__(self, o: object) -> bool:
        return o in self.__storage__


class SakiDict(dict):
    __overwritten__ = ("__init__", "clear", "pop", "popitem", "setdefault", "update", "__setitem__", "__delitem__",
                       "__document__", "__field__", "__storage__", "__overwritten__", "__getattr__", "__contains__")  # the last ones are more of added attributes

    def __init__(self, field: str, saki_document, values: typing.Iterable[typing.Any] = None) -> None:
        super().__setattr__("__document__", saki_document)
        super().__setattr__("__field__", str(field))

        if values is None:
            data = saki_document.__collection__.find({"_id": saki_document._id}, {field: 1})
            if data is None:
                super().__setattr__("__storage__", {})
            else:
                super().__setattr__("__storage__", data[field])
        else:
            super().__setattr__("__storage__", values)

        storage = super().__getattribute__("__storage__")
        overwritten = super().__getattribute__("__overwritten__")
        for attribute in dir(dict):
            if attribute not in overwritten and attribute != "__class__":  # __class__ cannot be overwritten
                super().__setattr__(attribute, storage.__getattribute__(attribute))  # if this fails, __storage__ is not a dict, which should not happen

    def clear(self) -> None:
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: {}}})
        self.__storage__.clear()

    def pop(self, key: typing.Any, default: typing.Any = Default(None)) -> typing.Any:
        copied = self.__storage__.copy()
        value = copied.pop(key, default)
        if isinstance(value, Default):  # no value coming from the user should be a nasse.utils.annotations.Default instance
            raise KeyError(key)
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        super().__setattr__("__storage__", copied)
        return value

    def popitem(self) -> tuple[typing.Any, typing.Any]:
        copied = self.__storage__.copy()
        key, value = copied.popitem()
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        super().__setattr__("__storage__", copied)
        return key, value

    def setdefault(self, key: typing.Any, default: Any = None) -> typing.Union[Any, typing.Any]:
        copied = self.__storage__.copy()
        value = copied.setdefault(key, default)
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        super().__setattr__("__storage__", copied)
        return value

    def update(self, *args, **kwargs) -> None:
        # TODO: update to replicate dict.update
        copied = self.__storage__.copy()
        copied.update(*args, **kwargs)
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        super().__setattr__("__storage__", copied)

    def __setitem__(self, key: typing.Any, value: typing.Any, update: bool = True) -> None:
        if update:
            self.__document__.__collection__.update_one({"_id": self.__document__._id}, {
                                                        "$set": {"{}.{}".format(self.__field__, key): encoder.BSONEncoder.default(value)}})
        self.__storage__.__setitem__(key, value)

    def __delitem__(self, key: typing.Any) -> None:
        self.__document__.__collection__.update_one({"_id": self.__document__._id}, {"$unset": {"{}.{}".format(self.__field__, key): ""}})
        self.__storage__.__delitem__(key)

    def __getattr__(self, name: str) -> Any:
        storage_value = super().__getattribute__("__storage__").get(name, Default(None))
        if not isinstance(storage_value, Default):
            return storage_value
        raise AttributeError("'{}' object has no attribute '{}'".format(self.__class__.__name__, name))

    def __getitem__(self, key: str) -> typing.Any:
        return super().__getattribute__("__storage__").__getitem__(key)

    def __repr__(self) -> str:
        return "SakiDict({})".format(self.__storage__.__repr__())

    def __setattr__(self, name: str, value: typing.Any, update: bool = True) -> None:
        self.__setitem__(name, value, update=update)

    def __delattr__(self, name: str) -> None:
        self.__delitem__(name)

    def __contains__(self, o: object) -> bool:  # it seems that 'a in x' was not calling __storage__.__contains__ for some reason if I don't overwrite it
        return super().__getattribute__("__storage__").__contains__(o)
