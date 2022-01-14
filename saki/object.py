import typing

import bson

from saki import collection, encoder

Any = typing.TypeVar("Any")

# TODO: Update some functions to avoid using dict.copy() and list.copy() and take up less memory.


class SakiObject(object):
    """
    An object behaving like a Python object which is linked to the database to update stuff on the fly.
    """
    __overwritten__: set[str] = {"__fetch_from_db__", "__lazy_fetch__", "__lazy__", "__overwritten__", "__storage_attributes__", "__storage__", "__id__", "__field__", "__master__", "__collection__", "__annotations__", "__class__",  # __class__ needs to be added to return the current class from __getattribute__
                                 "__init__", "__getitem__", "__getattribute__", "__setitem__", "__setattr__", "__delitem__", "__delattr__", "__repr__", "__contains__", "delete", "reload"}

    __lazy__: list[str] = []
    """
    This is a list of attributes that are lazy loaded.

    A "lazy loaded" attribute is an attribute that is not loaded until needed. It won't be fetched on the document instantiation.

    This should be used for attributes which are expensive to load or not needed in normal circumstances.
    """
    __storage__: typing.Union[dict, list]
    __storage_attributes__: set[str] = set()

    __id__: typing.Union[bson.ObjectId, str, int, typing.Any]
    __field__: str = ""
    __master__: bool = False
    if typing.TYPE_CHECKING:
        __collection__: collection.SakiCollection

    def __fetch_from_db__(self) -> typing.Union[list, dict]:
        raise NotImplementedError("This method should be implemented by the child class.")

    def __lazy_fetch__(self, lazy_obj: encoder.LazyObject) -> typing.Any:
        raise NotImplementedError("This method should be implemented by the child class.")

    def __init__(self, _id: typing.Union[bson.ObjectId, str, int, typing.Any], collection: "collection.SakiCollection", field: str = "", data: typing.Union[dict, list] = None) -> None:
        """
        Initializes the object by fetching the data from the database and intializing it.

        Parameters
        ----------
        _id: bson.ObjectId | str | int | Any
            The _id of the master document.
        collection: SakiCollection
            The collection the object belongs to.
        field: str, default=""
            The field the object belongs to.
        data: dict | list, default=None
            The data to initialize the object with. If None, the data will be fetched from the database.
        """
        super().__setattr__("__id__", _id)
        super().__setattr__("__collection__", collection)
        super().__setattr__("__field__", str(field).strip("."))  # strip is useful for the root path

        super().__setattr__("__storage__", data if data is not None else self.__fetch_from_db__())

        super().__setattr__("__annotations__", self.__annotations__ if hasattr(self, "__annotations__") else {})

        super().__setattr__("__storage_attributes__", set(dir(self.__storage__)).difference(self.__overwritten__))

    def __getitem__(self, name: typing.Union[str, int, slice]) -> None:
        """Gets the attribute 'name' from the database. Example: value = document['name']"""
        data = self.__storage__[name]
        if isinstance(data, encoder.LazyObject):
            data = self.__lazy_fetch__(data)
            data = encoder.TypeEncoder.default(data, _type=self.__annotations__.get(name, None), field="{}.{}".format(
                self.__field__, name), collection=self.__collection__, _id=self.__id__)
            self.__storage__.__setitem__(name, data)
        return data

    def __getattribute__(self, name: str) -> Any:
        """Gets the attribute 'name' from the object if available (methods, etc.) or from the database. Example: value = document.name"""
        if name in super().__getattribute__("__overwritten__"):
            return super().__getattribute__(name)
        if name in super().__getattribute__("__storage_attributes__"):
            return super().__getattribute__("__storage__").__getattribute__(name)
        return self.__getitem__(name)

    # def __getattr__(self, name: str) -> None:
    #     """Gets the attribute 'name' from the database. Example: value = document.name"""
    #     if name in self.__storage_attributes__:
    #         return super().__getattribute__("__storage__").__getattribute__(name)
    #     return self.__getitem__(name)

    def __setitem__(self, name: str, value: typing.Any) -> None:
        """Sets the attribute 'name' to 'value' in the database. Example: document['name'] = value"""
        value = encoder.TypeEncoder.default(value, _type=self.__annotations__.get(name, None), field="{}.{}".format(
            self.__field__, name), collection=self.__collection__, _id=self.__id__)
        self.__collection__.__collection__.update_one(
            {"_id": self.__id__}, {"$set": {"{}.{}".format(self.__field__, name): encoder.BSONEncoder.default(value)}})
        self.__storage__.__setitem__(name, value)

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """Sets the attribute 'name' to 'value' in the database. Example: document.name = value"""
        self.__setitem__(name, value)

    def __delitem__(self, name: str) -> None:
        """Deletes the attribute 'name' from the database. Example: del document['name']"""
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$unset": {"{}.{}".format(self.__field__, name): True}})
        self.__storage__.__delitem__(name)

    def __delattr__(self, name: str) -> None:
        """Deletes the attribute 'name' from the database. Example: del document.name"""
        self.__delitem__(name)

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self.__storage__)

    def __contains__(self, obj: typing.Any) -> bool:
        """If 'obj' is in the current object. Example: if 'obj' in document: ..."""
        return obj in self.__storage__

    def delete(self) -> None:
        """
        Deletes the current object from the database

        Example
        --------
        >>> document.name.delete()
        #    Initial Document
        #      {'username': 'something', 'name': {'first': 'John', 'last': 'Doe'}}
        #    Updated Document
        #      {'username': 'something'}
        """
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$unset": {self.__field__: True}})

    def reload(self) -> None:
        """
        Reloads the current object from the database

        It will refetch everything from the database and update the object.

        Example
        --------
        >>> document.name.reload()
        """
        self.__init__(self.__id__, self.__collection__, self.__field__)
