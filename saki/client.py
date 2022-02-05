import inspect
import threading
import typing
import pymongo
import pymongo.database

from saki import database as saki_database
from saki.watch import OperationType, Watch


class BuildInfo():
    def __init__(self, data: dict) -> None:
        self.data = dict(data)

        self.version = str(self.data.get("version"))
        self.version_array = [int(v) for v in self.data.get("versionArray", [])]
        self.git_version = str(self.data.get("gitVersion"))

        self.loader_flags = str(self.data.get("loaderFlags"))
        self.compiler_flags = str(self.data.get("compilerFlags"))

        self.openssl = self.data.get("openssl")
        self.javascript_engine = str(self.data.get("javascriptEngine"))
        self.bits = int(self.data.get("bits"))
        self.debug = bool(self.data.get("debug"))
        self.max_bson_object_size = float(self.data.get("maxBsonObjectSize"))  # float or int?
        self.storage_engines = [str(e) for e in self.data.get("storageEngines", [])]
        self.modules = [str(m) for m in self.data.get("modules", [])]
        self.ok = int(self.data.get("ok"))

        # these got removed because deprecated and unstable
        # self.sys_info = self.data.get("sysInfo")
        # self.allocator = str(self.data.get("allocator"))


class SakiClient():
    __overwritten__ = {"__overwritten__", "URI", "__annotations__", "__client__", "__realtime__", "__callbacks__", "__init__", "address", "close", "database_names",
                       "drop_database", "get_database", "server_info", "_watch_loop", "watch", "on", "__getitem__", "__getattribute__", "__repr__", "__setattr__", "__delattr__"}

    URI: str
    __annotations__: dict[str, type]
    __client__: pymongo.MongoClient

    __realtime__: bool = False
    __callbacks__: dict[OperationType, list[typing.Callable]] = {}

    def __init__(self, uri: str):
        super().__setattr__("URI", str(uri))
        super().__setattr__("__annotations__", self.__annotations__ if hasattr(self, "__annotations__") else {})
        super().__setattr__("__client__", pymongo.MongoClient(uri))

    @property
    def address(self):
        return self.__client__.address

    def close(self):
        self.__client__.close()

    def database_names(self):
        """
        Returns a list of the names of all the databases on the server.
        """
        return self.__client__.list_database_names()

    def drop_database(self, database: typing.Union[str, "saki_database.SakiDatabase", pymongo.database.Database]) -> None:
        """
        Drops a database.
        """
        if isinstance(database, saki_database.SakiDatabase):
            database = database.__database__
        return self.__client__.drop_database(database)

    def get_database(self, name: str) -> "saki_database.SakiDatabase":
        """
        Get a database by name.
        """
        cast = self.__annotations__.get(name, saki_database.SakiDatabase)
        return cast(self, name)

    def server_info(self) -> BuildInfo:
        return BuildInfo(self.__client__.server_info())

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

    def __getitem__(self, name: str) -> "saki_database.SakiDatabase":
        return self.get_database(name)

    def __getattribute__(self, name: str) -> typing.Union["saki_database.SakiDatabase", typing.Any]:
        if name in super().__getattribute__("__overwritten__"):
            return super().__getattribute__(name)
        return self.__getitem__(name)

    def __repr__(self):
        return "SakiClient('{}')".format(self.URI)

    def __setattr__(self, name, value):
        if name == "URI":
            return self.__init__(uri=value)  # reinitializing the client because it's a different one
        if name == "__realtime__" and not self.__realtime__ and value:
            super().__setattr__(name, value)
            return threading.Thread(target=self._watch_loop, daemon=True).start()
        super().__setattr__(name, value)

    def __delattr__(self, name):
        self.drop_database(name)
