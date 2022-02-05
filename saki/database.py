import typing
import threading
import inspect

import pymongo
import pymongo.collection
import pymongo.database

from saki import client, collection as saki_collection
from saki.watch import OperationType, Watch

ProfilingLevelType = typing.Literal[0, 1, 2]


class ProfilingLevel:
    OFF = pymongo.OFF
    SLOW_ONLY = pymongo.SLOW_ONLY
    ALL = pymongo.ALL


class SakiDatabase(object):
    __overwritten__ = {"__init__", "aggregate", "command", "create_collection", "drop_collection", "get_collection", "list_collection_names", "list_collections", "profiling_info",
                       "profiling_level", "set_profiling_level", "validate_collection", "watch", "on", "_watch_loop", "__setattr__", "__getitem__", "__getattribute__", "__delattr__", "__repr__", "__name__", "__client__", "__database__", "__realtime__", "__callbacks__", "__annotations__"}

    __name__: str
    __client__: "client.SakiClient"
    __database__: pymongo.database.Database

    __realtime__: bool = False
    __callbacks__: dict[OperationType, list[typing.Callable]] = {}

    def __init__(self, client: "client.SakiClient", name: str = "__sakit_test__") -> None:
        super().__setattr__("__name__", str(name))
        super().__setattr__("__annotations__", self.__annotations__ if hasattr(self, "__annotations__") else {})
        super().__setattr__("__database__", client.__client__.get_database(name))
        super().__setattr__("__client__", client)
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def aggregate(self, pipeline: list[dict], **kwargs) -> pymongo.cursor.Cursor:
        """
        Perform an aggregation on the database
        """
        return self.__database__.aggregate(pipeline, **kwargs)

    def command(self, command: dict, *args, **kwargs) -> dict:
        """
        Execute a command on the database
        """
        return self.__database__.command(command, *args, **kwargs)

    def create_collection(self, name: str, **kwargs) -> "saki_collection.SakiCollection":
        """
        Create a new collection
        """
        self.__database__.create_collection(name, **kwargs)
        return saki_collection.SakiCollection(self, name)

    def drop_collection(self, collection: typing.Union[str, "saki_collection.SakiCollection", pymongo.collection.Collection]) -> None:
        """
        Drops a collection
        """
        if isinstance(collection, saki_collection.SakiCollection):
            collection = collection.__collection__
        self.__database__.drop_collection(collection)

    def get_collection(self, name: str) -> "saki_collection.SakiCollection":
        """
        Get a collection by name
        """
        cast = self.__annotations__.get(name, saki_collection.SakiCollection)
        return cast(self, name)

    def list_collection_names(self, filter: dict[str, str] = None, **kwargs) -> list[str]:
        """
        List all of the collections in this database
        """
        kwargs["filter"] = filter
        return self.__database__.list_collection_names(**kwargs)

    def list_collections(self, filter: dict[str, str] = None, **kwargs) -> list["saki_collection.SakiCollection"]:
        """
        List all of the collections in this database
        """
        return [saki_collection.SakiCollection(self, name) for name in self.list_collection_names(filter, **kwargs)]

    def profiling_info(self, **kwargs):
        """
        Get the profiling information for this database
        """
        return self.__database__.profiling_info(**kwargs)

    def profiling_level(self, **kwargs) -> ProfilingLevelType:
        """
        Get the profiling level for this database
        """
        return self.__database__.profiling_level(**kwargs)

    def set_profiling_level(self, level: ProfilingLevelType, **kwargs) -> None:
        """
        Set the profiling level for this database
        """
        self.__database__.set_profiling_level(level, **kwargs)

    def validate_collection(self, collection: typing.Union[str, "saki_collection.SakiCollection", pymongo.collection.Collection], structure: bool = False, full: bool = False, background: bool = False, *args, **kwargs) -> dict:
        """
        Validate a collection
        """
        if isinstance(collection, saki_collection.SakiCollection):
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
                if "collection" in specs:
                    kwargs["collection"] = self
                if blocking:
                    callback(**kwargs)
                else:
                    threading.Thread(target=callback, kwargs=kwargs, daemon=True).start()

        watch.close()

    def watch(self, operations: list[OperationType] = None, pipeline: list[dict] = None, full_document: str = None, error_limit: int = 3, error_expiration: float = 60, **kwargs) -> Watch:
        """
        Returns an iterator (Watch) to watch the database for changes.
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
        if name == "__name__":
            return self.__init__(client=self.__client__, name=value)  # reinitializing the database because it's a different one
        if name == "__realtime__" and not self.__realtime__ and value:
            super().__setattr__(name, value)
            return threading.Thread(target=self._watch_loop, daemon=True).start()
        super().__setattr__(name, value)

    def __getitem__(self, name: str) -> "saki_collection.SakiCollection":
        return self.get_collection(name)

    def __getattribute__(self, name: str) -> typing.Union["saki_collection.SakiCollection", typing.Any]:
        if name in super().__getattribute__("__overwritten__"):
            return super().__getattribute__(name)
        return self.__getitem__(name)

    def __delattr__(self, name: str) -> None:
        self.drop_collection(name)

    def __repr__(self):
        return "SakiDatabase('{}')".format(self.__name__)
