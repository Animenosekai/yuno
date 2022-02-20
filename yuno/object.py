import typing
import inspect
import threading

import bson

if typing.TYPE_CHECKING:
    from yuno import collection

from yuno import encoder
from yuno.watch import DropDatabaseEvent, DropEvent, OperationType, RenameEvent, UpdateEvent, Watch

Any = typing.TypeVar("Any")

# TODO: Update some functions to avoid using dict.copy() and list.copy() and take up less memory.


class YunoObject(object):
    """
    An object behaving like a Python object which is linked to the database to update stuff on the fly.
    """
    __overwritten__: set[str] = {"__fetch_from_db__", "__lazy_fetch__", "__lazy__", "__overwritten__", "__defaults__", "__storage_attributes__", "__storage__", "__id__", "__field__", "__realtime__", "__callbacks__", "_watch_loop", "__collection__", "__annotations__", "__class__",  # __class__ needs to be added to return the current class from __getattribute__
                                 "__init__", "__getitem__", "__getattribute__", "__setitem__", "__setattr__", "__delitem__", "__delattr__", "__repr__", "__contains__", "delete", "reload", "watch", "on"}
    """All of the attributes defined by Yuno"""

    __lazy__: list[str] = []
    """
    This is a list of attributes that are lazy loaded.

    A "lazy loaded" attribute is an attribute that is not loaded until needed. It won't be fetched on the document instantiation.

    This should be used for attributes which are expensive to load or not needed in normal circumstances.
    """
    __storage__: typing.Union[dict, list]
    """Where the data is stored"""
    __storage_attributes__: set[str] = set()
    """Attributes for the data storage object"""
    __defaults__: set[str] = set()
    """The default defaults values defined by the user"""

    __id__: typing.Union[bson.ObjectId, str, int, typing.Any]
    """The _id of the document the object is in"""
    __field__: str = ""
    """The field of the object in the document"""
    __realtime__: bool = False
    """Wether or not to enable real-time object updating"""
    __callbacks__: dict[OperationType, list[typing.Callable]] = {}
    """Callbacks for real-time updating"""
    __collection__: "collection.YunoCollection"
    """The collection the document belongs to"""

    def __fetch_from_db__(self) -> typing.Union[list, dict]:
        """
        Fetches the data from the database.

        Returns
        -------
        dict | list
            The data from the database.
        """
        raise NotImplementedError("This method should be implemented by the child class.")

    def __lazy_fetch__(self, lazy_obj: encoder.LazyObject) -> typing.Any:
        """
        Fetches the lazy loaded data from the database.

        Parameters
        ----------
        lazy_obj: encoder.LazyObject
            The lazy loaded object to fetch.

        Returns
        -------
        typing.Any
            The data from the database.
        """
        raise NotImplementedError("This method should be implemented by the child class.")

    def __post_verification__(self) -> None:
        """
        This method is called after the object has been initialized.
        """
        raise NotImplementedError("This method should be implemented by the child class.")

    def __init__(self, _id: typing.Union[bson.ObjectId, str, int, typing.Any], collection: "collection.YunoCollection", field: str = "", data: typing.Union[dict, list] = None) -> None:
        """
        Initializes the object by fetching the data from the database and intializing it.

        Parameters
        ----------
        _id: bson.ObjectId | str | int | Any
            The _id of the master document.
        collection: YunoCollection
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
        self.__post_verification__()
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def __getitem__(self, name: typing.Union[str, int, slice]) -> typing.Any:
        """Gets the attribute 'name' from the database. Example: value = document['name']"""
        data = self.__storage__[name]
        if isinstance(data, encoder.LazyObject):
            data = self.__lazy_fetch__(data)
            data = encoder.YunoTypeEncoder().default(data, _type=self.__annotations__.get(name, None), field="{}.{}".format(
                self.__field__, name), collection=self.__collection__, _id=self.__id__)
            self.__storage__.__setitem__(name, data)
        return data

    def __getattribute__(self, name: str) -> Any:
        """Gets the attribute 'name' from the object if available (methods, etc.) or from the database. Example: value = document.name"""
        if name in super().__getattribute__("__overwritten__"):
            return super().__getattribute__(name)
        if name in super().__getattribute__("__storage_attributes__"):
            return super().__getattribute__("__storage__").__getattribute__(name)
        try:
            return self.__getitem__(name)
        except KeyError as err:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'") from err

    def __setitem__(self, name: str, value: typing.Any, update: bool = True) -> None:
        """Sets the attribute 'name' to 'value' in the database. Example: document['name'] = value"""
        value = encoder.YunoTypeEncoder().default(value, _type=self.__annotations__.get(name, None), field="{}.{}".format(
            self.__field__, name), collection=self.__collection__, _id=self.__id__)
        if update:
            self.__collection__.__collection__.update_one(
                {"_id": self.__id__}, {"$set": {"{}.{}".format(self.__field__, name): encoder.YunoBSONEncoder().default(value)}})
        self.__storage__.__setitem__(name, value)

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """Sets the attribute 'name' to 'value' in the database. Example: document.name = value"""
        if name == "__realtime__":
            if not self.__realtime__ and value:
                super().__setattr__(name, value)
                threading.Thread(target=self._watch_loop, daemon=True).start()
                return
            return super().__setattr__(name, value)
        self.__setitem__(name, value)

    def __delitem__(self, name: str, update: bool = True) -> None:
        """Deletes the attribute 'name' from the database. Example: del document['name']"""
        if update:
            self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$unset": {"{}.{}".format(self.__field__, name): True}})
        self.__storage__.__delitem__(name)

    def __delattr__(self, name: str) -> None:
        """Deletes the attribute 'name' from the database. Example: del document.name"""
        self.__delitem__(name)

    def __repr__(self) -> str:
        """Returns a string representation of the object."""
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
        if self.__field__ == "":
            self.__collection__.__collection__.delete_one({"_id": self.__id__})
        else:
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

    def _watch_loop(self):
        """
        Internal method that watches the database for changes and updates the object.

        Also calls all of the callbacks that are registered to the object on the specific operations.
        """
        if not self.__realtime__:
            return
        watch = self.watch(error_limit=10)  # we raise the limit a little bit to be sure we don't miss any changes
        for event in watch:
            if not self.__realtime__:
                break
            if isinstance(event, UpdateEvent):
                for key, value in event.update_description.updated_fields.items():
                    if not key.startswith(self.__field__) or key.removeprefix(self.__field__).count(".") > 1:
                        continue
                    key = key.split(".")[-1]
                    try:
                        needed = value != self.__getitem__(key)
                    except KeyError:
                        needed = True
                    if needed:
                        self.__setitem__(key, value, update=False)  # already updated in the database

                for key in event.update_description.removed_fields:
                    if not key.startswith(self.__field__):
                        continue
                    try:
                        self.__delitem__(key, update=False)  # already updated in the database
                    except KeyError:
                        continue

                # TODO: truncated arrays

            if isinstance(event, RenameEvent):
                self.__collection__.__name__ = event.to.collection

            if isinstance(event, (DropEvent, DropDatabaseEvent)):
                raise ValueError("The document got deleted from the database")

            for callback, blocking in self.__callbacks__.get(event.operation, []):
                specs = inspect.getfullargspec(callback).args
                kwargs = {}
                if "event" in specs:
                    kwargs["event"] = event
                if "collection" in specs:
                    kwargs["collection"] = self.__collection__
                if "object" in specs:
                    kwargs["object"] = self
                if blocking:
                    callback(**kwargs)
                else:
                    threading.Thread(target=callback, kwargs=kwargs, daemon=True).start()

        watch.close()

    def watch(self, operations: list[OperationType] = None, pipeline: list[dict] = None, full_document: str = None, error_limit: int = 3, error_expiration: float = 60, **kwargs) -> Watch:
        """
        Returns an iterator (Watch) to watch the database for changes.

        Parameters
        ----------
        operations: list[OperationType]
            The operations to watch for.
        pipeline: list[dict]
            The pipeline to watch for.
        full_document: str
            The full_document to watch for.
        error_limit: int
            The number of errors to allow before raising an exception.
        error_expiration: float
            The number of seconds to wait before raising an exception.
        kwargs:
            The kwargs to pass to the watch.

        Returns
        -------
        Watch
            The watch object.

        Example
        --------
        >>> watch = document.watch()
        >>> for event in watch:
        >>>     print(event)
        """
        final_pipeline = []
        # matches the current document and the drop/rename/dropDatabase events
        # final_pipeline.append({"$match": {"$or": [
        #     {"_id": self.__id__},
        #     {"operationType": {"$in": ["drop", "rename", "dropDatabase", "invalidate"]}}
        # ]}})
        if operations:
            final_pipeline.append({"$match": {"operationType": {"$in": operations}}})
            # we could match the beginning of the fields if the operation is an update
        final_pipeline.extend(pipeline if pipeline else [])
        return Watch(self.__collection__.__collection__, pipeline=final_pipeline, full_document=full_document, error_limit=error_limit, error_expiration=error_expiration, **kwargs)

    def on(self, operation: OperationType, callback: typing.Callable, blocking: bool = False) -> None:
        """
        Registers a callback to be called when a certain operation is performed on the current object.

        This implies that __realtime__ is set to True.

        The callback will be called upon the update of the object.

        Parameters
        ----------
        operation: OperationType
            The operation to watch for.
        callback: typing.Callable
            The callback to be called.
        """
        try:
            self.__callbacks__[operation].append((callback, blocking))
        except Exception:
            self.__callbacks__[operation] = [(callback, blocking)]

        self.__realtime__ = True
