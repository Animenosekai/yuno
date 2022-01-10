import typing
import inspect

import bson
import pymongo.collection

from saki import encoder


class SakiDocument(object):
    __lazy__attributes__ = {}
    __collection__: pymongo.collection.Collection
    _id: typing.Union[bson.ObjectId, typing.Any]

    def __init__(self, collection: pymongo.collection.Collection, _id: typing.Union[bson.ObjectId, typing.Any] = None, data: dict[str, typing.Any] = None, ) -> None:
        if _id is None and data is None:
            raise ValueError("Either _id or data must be provided.")

        if not hasattr(self, "__annotations__"):
            super().__setattr__("__annotations__", {})

        super().__setattr__("__collection__", collection,)
        super().__setattr__("__attributes__", [attribute for attribute in set(
            ["_id"] + list(dir(self)) + list(self.__annotations__.keys())) if not attribute.startswith("__")])

        # we also need if attribute is inspect.isfunction

        if data is None:
            projection = {attribute: True for attribute in self.__attributes__ if not attribute in self.__lazy__attributes__}
            projection["_id"] = False  # _id should not be None at this stage

            data = collection.find_one({"_id": _id}, projection=projection)

        data = dict(data)

        super().__setattr__("_id", data.get("_id", _id))

        variables = dir(self)

        for attribute in self.__annotations__.keys():  # ways for attributes to be declared without actually being defined
            if attribute not in variables and attribute not in data:
                raise ValueError(
                    "We could not find the attribute '{}' in the document. Either give a default value to the attribute or set a value in the database.".format(attribute))

        for key, value in data.items():
            self.__setattr__(key, value, update=False)

    @property
    def __lazy__(self) -> typing.Iterable[str]:
        """
        This is a list of attributes that are lazy loaded.

        A "lazy loaded" attribute is an attribute that is not loaded until needed. It won't be fetched on the document instantiation.

        This should be used for attributes that are expensive to load or that are not needed in normal circumstances.
        """
        return self.__lazy__attributes__

    @__lazy__.setter
    def __lazy__(self, value: typing.Iterable[str]) -> None:
        self.__lazy__attributes__ = {key: False for key in value if key != "_id"}

    def __getattribute__(self, __name: str) -> typing.Any:
        __name = str(__name)

        if not super().__getattribute__("__lazy__attributes__").get(__name, True):
            value = self.__collection__.find_one({"_id": self._id}, projection={__name: True, "_id": False})[__name]
            self.__setattr__(__name, value)
            self.__lazy__attributes__[__name] = True
            return value

        return super().__getattribute__(__name)

    def __setattr__(self, __name: str, __value: typing.Any, update: bool = True) -> None:
        __name = str(__name)

        cast = self.__annotations__.get(__name, None)
        if cast is not None:
            __value = encoder.TypeEncoder.default(__value, cast, field=str(__name), document=self)

        if update and __value != super().__getattribute__(__name):
            self.__collection__.update_one({"_id": self._id}, {"$set": {__name: encoder.BSONEncoder.default(__value)}})
        super().__setattr__(__name, __value)

    @property
    def __dict__(self, remove: typing.List[str] = None, builtins: bool = False) -> typing.Dict[str, typing.Any]:
        """
        This is a dictionary representation of the document.

        Parameters
        ----------
            remove : list of str, optional, default=None
                A list of attributes to remove from the dictionary.
            builtins : bool, optional, default=False
                Whether to include builtin attributes in the dictionary.
        """
        data = {}
        if remove is not None:
            for key in remove:
                data.pop(key, None)
        if not builtins:
            for key in data:
                if key.startswith("__"):
                    data.pop(key, None)
        return data

    def __repr__(self) -> str:
        return "SakiDocument(_id={}, collection={})".format(self._id, self.__collection__.name)
