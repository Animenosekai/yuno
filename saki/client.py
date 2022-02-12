import inspect
import threading
import typing
import pymongo
import pymongo.database

from saki.launcher import MongoDB
from saki import database as saki_database
from saki.watch import OperationType, Watch


class BuildInfo():
    """An object holding information about the MongoDB build."""

    def __init__(self, data: dict) -> None:
        """
        Initialize the object.

        Parameters
        ----------
        data : dict
            The data to initialize the object with.
        """
        self.data = dict(data)

        self.git_version = str(self.data.get("gitVersion"))
        self.version_array = [int(v) for v in self.data.get("versionArray", [])]
        self.version = str(self.data.get("version"))

        self.openssl = self.data.get("openssl")
        self.javascript_engine = str(self.data.get("javascriptEngine"))
        self.bits = int(self.data.get("bits"))
        self.debug = bool(self.data.get("debug"))
        self.max_bson_object_size = int(self.data.get("maxBsonObjectSize"))  # float or int?
        self.storage_engines = [str(e) for e in self.data.get("storageEngines", [])]
        self.modules = [str(m) for m in self.data.get("modules", [])]

        # these got removed because deprecated and unstable
        # self.sys_info = self.data.get("sysInfo")
        # self.allocator = str(self.data.get("allocator"))
        # self.build_environment = dict(self.data.get("buildEnvironment"))

    def __repr__(self) -> str:
        """A string representation of the object."""
        return "BuildInfo(version={}, javascript_engine='{}', bits={}, debug={})".format(self.version, self.javascript_engine, self.bits, self.debug)


class SakiClient():
    """
    The client to communicate with the MongoDB server.
    """
    __overwritten__ = {"__overwritten__", "host", "port", "__annotations__", "__client__", "__options__", "__realtime__", "__callbacks__", "__init__", "address", "close", "database_names",
                       "drop_database", "get_database", "server_info", "_watch_loop", "watch", "on", "__getitem__", "__getattribute__", "__repr__", "__setattr__", "__delattr__"}

    host: str
    """The host the client is connected to."""
    port: int
    """The port the client is connected to."""
    __annotations__: dict[str, type]
    """
    A dictionary of the different database's types.

    This automatically set when you annotate attributes like this:

    >>> class AccountDatabase(SakiDatabase):
    >>>     ...

    >>> class MyClient(SakiClient):
    >>>     account_db: AccountDatabase # this is added to __annotations__ automatically
    """
    __client__: pymongo.MongoClient
    """The PyMongo client"""
    __options__: dict[str, typing.Any] = {}
    """Options defined on object instantiation"""

    __realtime__: bool = False
    """Wether to look for cluster events in realtime or not."""
    __callbacks__: dict[OperationType, list[typing.Callable]] = {}
    """Callbacks on certain events"""

    def __init__(self, host: typing.Union[str, list[str], MongoDB], port: int = None, tz_aware: bool = True, connect: bool = True, **kwargs) -> None:
        """
        Initialize the client.

        Parameters
        ----------
        host : str, list[str], MongoDB
            The host or list of hostnames to connect to. You can use `host` to pass in a URI string or a MongoDB object (in which case you won't need to use `port`).
        port : int
            The port to connect to.
        tz_aware : bool
            Whether to use timezone aware datetimes or not.
        connect : bool
            Whether to connect before making any operation to the server or not.
        kwargs : dict
            Options to pass to the PyMongo client.
        """
        if isinstance(host, MongoDB):
            host = host.host
        kwargs.update({
            "host": host,
            "port": port,
            "tz_aware": tz_aware,
            "connect": connect
        })
        super().__setattr__("__client__", pymongo.MongoClient(**kwargs))
        address = self.__client__.address
        if address is not None:
            super().__setattr__("host", address[0])
            super().__setattr__("port", address[1])
        else:
            super().__setattr__("host", host)
            super().__setattr__("port", port)
        super().__setattr__("__options__", kwargs)
        super().__setattr__("__annotations__", self.__annotations__ if hasattr(self, "__annotations__") else {})

    @property
    def address(self):
        """
        The address of the server.

        Returns
        -------
        tuple[str, int]
            A (host, port) tuple of the server the client is connected to.
        """
        return self.__client__.address

    def close(self):
        """
        Close the client.
        """
        self.__client__.close()

    def database_names(self):
        """
        Returns a list of the names of all the databases on the server.

        Returns
        -------
        list[str]
            A list of the names of all the databases on the server.
        """
        return self.__client__.list_database_names()

    def drop_database(self, database: typing.Union[str, "saki_database.SakiDatabase", pymongo.database.Database]) -> None:
        """
        Drops a database.

        Parameters
        ----------
        database : str, SakiDatabase, pymongo.database.Database
            The database to drop.
        """
        if isinstance(database, saki_database.SakiDatabase):
            database = database.__database__
        return self.__client__.drop_database(database)

    def get_database(self, name: str) -> "saki_database.SakiDatabase":
        """
        Get a database by name.

        Parameters
        ----------
        name : str
            The name of the database to get.

        Returns
        -------
        SakiDatabase
            The database.
        """
        cast = self.__annotations__.get(name, saki_database.SakiDatabase)
        return cast(self, name)

    def server_info(self) -> BuildInfo:
        """
        Get information about the server.

        Returns
        -------
        BuildInfo
            The server's build information.
        """
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
        Returns an iterator (Watch) to watch the cluster for changes.

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
        >>> watch = client.watch()
        >>> for event in watch:
        >>>     print(event)
        """
        final_pipeline = []
        if operations:
            final_pipeline.append({"$match": {"operationType": {"$in": operations}}})
        final_pipeline.extend(pipeline if pipeline else [])
        return Watch(self.__client__, pipeline=final_pipeline, full_document=full_document, error_limit=error_limit, error_expiration=error_expiration, **kwargs)

    def on(self, operation: OperationType, callback: typing.Callable, blocking: bool = False) -> None:
        """
        Registers a callback to be called when a certain operation is performed on the current cluster.

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
        """
        Get a database by name.

        Example
        --------
        >>> db = client["test"]
        """
        return self.get_database(name)

    def __getattribute__(self, name: str) -> typing.Union["saki_database.SakiDatabase", typing.Any]:
        """
        Get a database by name.

        Example
        --------
        >>> db = client.test
        """
        if name in super().__getattribute__("__overwritten__"):
            return super().__getattribute__(name)
        return self.__getitem__(name)

    def __repr__(self):
        """A string representation of the object."""
        return "SakiClient(host='{}', port={})".format(self.host, self.port)

    def __setattr__(self, name, value):
        """
        Set an attribute on the object.

        Some values will take actions on the object.

        Example
        --------
        >>> client.host = "127.0.0.1" # will reinstantiate the client
        """
        if name == "host":
            return self.__init__(host=value, **self.__options__)  # reinitializing the client because it's a different one
        if name == "port":
            return self.__init__(port=value, **self.__options__)  # reinitializing the client because it's a different one
        if name == "__realtime__" and not self.__realtime__ and value:
            super().__setattr__(name, value)
            return threading.Thread(target=self._watch_loop, daemon=True).start()
        super().__setattr__(name, value)

    def __delattr__(self, name):
        """
        Drops a database by name.
        """
        self.drop_database(name)
