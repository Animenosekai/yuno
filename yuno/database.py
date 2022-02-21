import typing
import threading
import inspect

import pymongo
import pymongo.collection
import pymongo.database

from yuno import client, collection as yuno_collection
from yuno.watch import OperationType, Watch

ProfilingLevelType = typing.Literal[0, 1, 2]


class ProfilingLevel:
    try:
        OFF = pymongo.OFF
    except AttributeError:  # according to CI
        OFF = 0
    try:
        SLOW_ONLY = pymongo.SLOW_ONLY
    except AttributeError:  # according to CI
        SLOW_ONLY = 1
    try:
        ALL = pymongo.ALL
    except AttributeError:  # according to CI
        ALL = 2


class YunoDatabase(object):
    __overwritten__ = {"__init__", "aggregate", "command", "create_collection", "drop_collection", "get_collection", "list_collection_names", "list_collections", "profiling_info",
                       "profiling_level", "set_profiling_level", "validate_collection", "watch", "on", "_watch_loop", "__setattr__", "__getitem__", "__getattribute__", "__delattr__", "__delitem__", "__repr__", "__name__", "__client__", "__database__", "__realtime__", "__callbacks__", "__annotations__"}

    __name__: str
    """The name of the database"""
    __client__: "client.YunoClient"
    """The client that this database is connected to"""
    __database__: pymongo.database.Database
    """The PyMongo database object"""

    __realtime__: bool = False
    """Whether the database updates in realtime or not"""
    __callbacks__: typing.Dict[OperationType, typing.List[typing.Callable]] = {}
    """The callbacks registered for realtime updates"""

    def __init__(self, client: "client.YunoClient", name: str = "__yunot_test__") -> None:
        """
        Instantiate the database object

        Parameters
        ----------
        client : YunoClient
            The client that this database is connected to
        name : str, default="__yunot_test__"
            The name of the database
        """
        super().__setattr__("__name__", str(name))
        super().__setattr__("__annotations__", self.__annotations__ if hasattr(self, "__annotations__") else {})
        super().__setattr__("__database__", client.__client__.get_database(name))
        super().__setattr__("__client__", client)
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def aggregate(self, pipeline: typing.List[dict], **kwargs) -> pymongo.cursor.Cursor:
        """
        Perform an aggregation on the database

        Parameters
        ----------
        pipeline : list[dict]
            The pipeline to perform
        kwargs : dict
            Additional arguments to pass to the aggregation
        """
        return self.__database__.aggregate(pipeline, **kwargs)

    def command(self, command: dict, *args, **kwargs) -> dict:
        """
        Execute a command on the database

        Parameters
        ----------
        command : dict
            The command to execute
        args : list
            Additional arguments to pass to the command
        kwargs : dict
            Additional keyword arguments to pass to the command

        Returns
        -------
        dict
            The result of the command
        """
        return self.__database__.command(command, *args, **kwargs)

    def create_collection(self, name: str, **kwargs) -> "yuno_collection.YunoCollection":
        """
        Create a new collection

        Parameters
        ----------
        name : str
            The name of the collection to create
        kwargs : dict
            Additional keyword arguments to pass to the collection creation

        Returns
        -------
        YunoCollection
            The created collection
        """
        self.__database__.create_collection(name, **kwargs)
        return yuno_collection.YunoCollection(self, name)  # this should be tested against __annotations__

    def drop_collection(self, collection: typing.Union[str, "yuno_collection.YunoCollection", pymongo.collection.Collection]) -> None:
        """
        Drops a collection

        Parameters
        ----------
        collection : str, YunoCollection, or pymongo.collection.Collection
            The collection to drop
        """
        if isinstance(collection, yuno_collection.YunoCollection):
            collection = collection.__collection__
        self.__database__.drop_collection(collection)

    def get_collection(self, name: str) -> "yuno_collection.YunoCollection":
        """
        Get a collection by name

        Parameters
        ----------
        name : str
            The name of the collection to get

        Returns
        -------
        YunoCollection
            The collection
        """
        cast = self.__annotations__.get(name, yuno_collection.YunoCollection)
        return cast(self, name)

    def list_collection_names(self, filter: typing.Dict[str, str] = None, **kwargs) -> typing.List[str]:
        """
        List all of the collections in this database

        Parameters
        ----------
        filter : dict[str, str], default=None
            The filter to apply to the list of collections
        kwargs : dict
            Additional keyword arguments to pass to the list_collection_names method

        Returns
        -------
        list[str]
            The list of collection names
        """
        kwargs["filter"] = filter
        return self.__database__.list_collection_names(**kwargs)

    def list_collections(self, filter: typing.Dict[str, str] = None, **kwargs) -> typing.List["yuno_collection.YunoCollection"]:
        """
        List all of the collections in this database

        Parameters
        ----------
        filter : dict[str, str], default=None
            The filter to apply to the list of collections
        kwargs : dict
            Additional keyword arguments to pass to the list_collection_names method

        Returns
        -------
        list[YunoCollection]
            The list of collections
        """
        return [yuno_collection.YunoCollection(self, name) for name in self.list_collection_names(filter, **kwargs)]

    def profiling_info(self, **kwargs):
        """
        Get the profiling information for this database

        Parameters
        ----------
        kwargs : dict
            Additional keyword arguments to pass to the profiling_info method

        Returns
        -------
        dict
            The profiling information
        """
        return self.__database__.profiling_info(**kwargs)

    def profiling_level(self, **kwargs) -> ProfilingLevelType:
        """
        Get the profiling level for this database

        Parameters
        ----------
        kwargs : dict
            Additional keyword arguments to pass to the profiling_level method

        Returns
        -------
        ProfilingLevelType
            The profiling level
        """
        return self.__database__.profiling_level(**kwargs)

    def set_profiling_level(self, level: ProfilingLevelType, **kwargs) -> None:
        """
        Set the profiling level for this database

        Parameters
        ----------
        level : ProfilingLevelType
            The profiling level to set
        kwargs : dict
            Additional keyword arguments to pass to the set_profiling_level method
        """
        self.__database__.set_profiling_level(level, **kwargs)

    def validate_collection(self, collection: typing.Union[str, "yuno_collection.YunoCollection", pymongo.collection.Collection], structure: bool = False, full: bool = False, background: bool = False, *args, **kwargs) -> dict:
        """
        Validate a collection

        Parameters
        ----------
        collection : str, YunoCollection, or pymongo.collection.Collection
            The collection to validate
        structure : bool, default=False
            Whether to validate the structure of the collection
        full : bool, default=False
            Whether to validate the collection's data
        background : bool, default=False
            Whether to validate the collection in the background
        args : list
            Additional arguments to pass to the validate_collection method
        kwargs : dict
            Additional keyword arguments to pass to the validate_collection method

        Returns
        -------
        dict
            The validation information
        """
        if isinstance(collection, yuno_collection.YunoCollection):
            collection = collection.__collection__
        return self.__database__.validate_collection(name_or_collection=collection, scandata=structure, full=full, background=background, *args, **kwargs)

    def _watch_loop(self):
        """
        Internal method that watches the database for changes.

        Also calls all of the callbacks that are registered to the object on the specific operations.
        """
        if not self.__realtime__:
            return
        watch = self.watch(error_limit=10)  # we raise the limit a little bit to be sure we don't miss any changes
        for event in watch:
            if not self.__realtime__:
                break
            for callback, blocking in self.__callbacks__.get(event.operation, []):
                specs = inspect.getfullargspec(callback).args
                kwargs = {}
                if "event" in specs:
                    kwargs["event"] = event
                if "client" in specs:
                    kwargs["client"] = self.__client__
                if "database" in specs:
                    kwargs["database"] = self
                if blocking:
                    callback(**kwargs)
                else:
                    threading.Thread(target=callback, kwargs=kwargs, daemon=True).start()

        watch.close()

    def watch(self, operations: typing.List[OperationType] = None, pipeline: typing.List[dict] = None, full_document: str = None, error_limit: int = 3, error_expiration: float = 60, **kwargs) -> Watch:
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
        >>> watch = database.watch()
        >>> for event in watch:
        >>>     print(event)
        """
        final_pipeline = []
        if operations:
            final_pipeline.append({"$match": {"operationType": {"$in": operations}}})
        final_pipeline.extend(pipeline if pipeline else [])
        return Watch(self.__database__, pipeline=final_pipeline, full_document=full_document, error_limit=error_limit, error_expiration=error_expiration, **kwargs)

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

    def __setattr__(self, name: str, value: dict) -> None:
        """
        Sets an attribute on the object.

        Some objects might affect the object

        Example
        --------
        >>> database.__name__ = "New Database" # this will reinitialize the database with the new name
        """
        if name == "__name__":
            return self.__init__(client=self.__client__, name=value)  # reinitializing the database because it's a different one
        if name == "__realtime__" and not self.__realtime__ and value:
            super().__setattr__(name, value)
            return threading.Thread(target=self._watch_loop, daemon=True).start()
        super().__setattr__(name, value)

    def __getitem__(self, name: str) -> "yuno_collection.YunoCollection":
        """Get a collection from the database. Example: database["collection"]"""
        return self.get_collection(name)

    def __getattribute__(self, name: str) -> typing.Union["yuno_collection.YunoCollection", typing.Any]:
        """
        Get an attribute from the object or a database from the database

        Example
        --------
        >>> database.collection # this will return a collection
        >>> database.__name__ # this will return the name of the database
        """
        if name in super().__getattribute__("__overwritten__"):
            return super().__getattribute__(name)
        return self.__getitem__(name)

    def __delitem__(self, name: str) -> None:
        """Drops a collection. Example: del database["collection"]"""
        self.drop_collection(name)

    def __delattr__(self, name: str) -> None:
        """Drops a collection. Example: del database.collection"""
        self.drop_collection(name)

    def __repr__(self):
        """String representation of the database"""
        return "YunoDatabase('{}')".format(self.__name__)
