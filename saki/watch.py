import typing
import time
import pymongo.change_stream
import pymongo.collection


OperationType = typing.Literal["insert", "update", "delete", "replace", "drop", "rename", "dropDatabase", "invalidate"]


class Operation():
    UPDATE: OperationType = "update"
    INSERT: OperationType = "insert"
    DELETE: OperationType = "delete"
    REPLACE: OperationType = "replace"
    DROP: OperationType = "drop"
    RENAME: OperationType = "rename"
    DROP_DATABASE: OperationType = "dropDatabase"
    INVALIDATE: OperationType = "invalidate"


def create_match_filter(_id: str, field: str, operation: OperationType) -> dict:
    match = {
        "operationType": operation,
        "$or": [
            {"fullDocument._id": _id},
            {"documentKey._id": _id}
        ]
    }
    if operation == Operation.UPDATE:
        pass


class WatchEvent():
    class Namespace:
        def __init__(self, data: dict) -> None:
            self.database = data.get("db")
            self.collection = data.get("coll")

        def __getitem__(self, key: str) -> str:
            return self.__getattribute__(key)

    class LSID:
        def __init__(self, data: dict) -> None:
            self.id = data.get("id", None)
            self.uid = data.get("uid", None)

    def __init__(self, data: dict) -> None:
        self.id = self._id = data.get("_id")
        self.operation: OperationType = data.get("operationType")
        self.document = data.get("fullDocument", None)
        self.namespace = self.Namespace(data.get("ns", {}))
        self.timestamp = data.get("clusterTime", None)
        self.transaction = data.get("txnNumber", None)
        self.session_id = self.LSID(data.get("lsid", {}))


class CRUDEvent(WatchEvent):
    class DocumentKey:
        def __init__(self, data: dict) -> None:
            self.id = self._id = data.get("_id")
            self.__data__ = dict(data)

        def __getattribute__(self, name: str):
            if name in ("__data__", "__getitem__", "__getattribute__"):
                return super().__getattribute__(name)
            return self.__getitem__(name)

        def __getitem__(self, name: str):
            return self.data[name]

    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.document_key = self.DocumentKey(data.get("documentKey", {}))  # insert, replace, delete, update


class UpdateEvent(CRUDEvent):
    class Description:
        class Truncated:
            def __init__(self, data: dict) -> None:
                self.field = data.get("field", None)
                self.new_size = data.get("newSize", None)

        def __init__(self, data: dict) -> None:
            self.updated_fields: dict[str, typing.Any] = data.get("updatedFields", {})
            self.removed_fields: list[str] = data.get("removedFields", [])
            self.truncated_arrays = [self.Truncated(e) for e in data.get("truncatedArrays", [])]

    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.update_description = self.Description(data.get("updateDescription", {}))


class InsertEvent(CRUDEvent):
    pass


class DeleteEvent(CRUDEvent):
    pass


class ReplaceEvent(CRUDEvent):
    pass


class DropEvent(WatchEvent):
    pass


class RenameEvent(WatchEvent):
    def __init__(self, data: dict) -> None:
        super().__init__(data)
        self.to = self.Namespace(data.get("to", {}))  # rename


class DropDatabaseEvent(WatchEvent):
    pass


class InvalidateEvent(WatchEvent):
    pass


class Watch():
    """
    A db.watch(), db.collection.watch(), db.collection.object.watch() stream to get the different events.
    """
    __stream__: pymongo.change_stream.ChangeStream
    __watching_object__: pymongo.collection.Collection
    __state__: dict = {
        "token": None,  # the resume token
        "time": 0,  # time of the last error
        "count": 0  # number of errors in the period
    }

    # pipeline=pipeline, full_document=None, resume_after=resume_state["token"], max_await_time_ms=None,
    #    batch_size=None, collation=None, start_at_operation_time=None, session=None, start_after=None

    def __init__(self, watching_object: pymongo.collection.Collection, pipeline: list[dict] = None, full_document: str = None, error_limit: int = 3, error_expiration: float = 60, **kwargs) -> None:
        """
        Initializes the stream.
        """
        self.pipeline = pipeline
        self.full_document = full_document
        self.kwargs = kwargs

        self.error_limit = int(error_limit)
        self.error_expiration = float(error_expiration)

        self.__watching_object__ = watching_object
        self.__stream__ = watching_object.watch(pipeline, full_document, **kwargs)
        self.__closed__ = False

    def __next__(self): # alias
        return self.next()

    def next(self) -> WatchEvent:
        """
        Get the next event (blocking operation)
        """
        if self.__closed__:
            raise StopIteration("Stream is closed")
        try:
            data = self.__stream__.next()
            self.__state__["token"] = self.resume_token
        except Exception as err:
            self.__state__["count"] += 1
            if time.time() - self.__state__["time"] > self.error_expiration:
                self.__state__["time"] = time.time()
                self.__state__["count"] = 1
            else:
                self.__state__["time"] = time.time()
                if self.__state__["count"] >= self.error_limit:
                    try:
                        self.__stream__.close()
                    except Exception:
                        pass
                    raise ValueError("More than {} errors have occured in {} seconds while watching for changes in {}".format(
                        self.error_limit, self.error_expiration, self.__watching_object__)) from err
            self.kwargs["resume_after"] = self.__state__["token"]
            self.__stream__ = self.__watching_object__.watch(self.pipeline, self.full_document, **self.kwargs)
            return self.__next__()

        operation = data.get("operationType", None)
        if operation == Operation.UPDATE:
            return UpdateEvent(data)
        elif operation == Operation.INSERT:
            return InsertEvent(data)
        elif operation == Operation.DELETE:
            return DeleteEvent(data)
        elif operation == Operation.REPLACE:
            return ReplaceEvent(data)
        elif operation == Operation.DROP:
            return DropEvent(data)
        elif operation == Operation.RENAME:
            return RenameEvent(data)
        elif operation == Operation.DROP_DATABASE:
            return DropDatabaseEvent(data)
        elif operation == Operation.INVALIDATE:
            return InvalidateEvent(data)
        return WatchEvent(data)

    def try_next(self):
        """
        Try to get the next event without raising an exception and without waiting.
        """
        try:
            return self.__stream__.try_next()
        except StopIteration:
            return None

    def close(self):
        """
        Closes the stream.
        """
        self.__closed__ = True
        self.__stream__.close()

    def resume(self):
        """
        Resume the stream from the last known state.
        """
        self.kwargs["resume_after"] = self.__state__["token"]
        self.__stream__ = self.__watching_object__.watch(self.pipeline, self.full_document, **self.kwargs)
        self.__closed__ = False

    @property
    def resume_token(self):
        """
        Get the resume token, which is used to resume the stream if failed.
        """
        return self.__stream__.resume_token

    @property
    def alive(self):
        """Does this cursor have the potential to return more data?

        .. note:: Even if :attr:`alive` is ``True``, :meth:`next` can raise
            :exc:`StopIteration` and :meth:`try_next` can return ``None``.

        .. versionadded:: 3.8
        """
        return self._cursor.alive

    def __enter__(self):
        """
        Enter the context manager.

        Example
        -------
        >>> with db.watch() as stream: # <-- this line calls __enter__
        ...     for event in stream:
        ...         print(event)
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager.

        Example
        -------
        >>> with db.watch() as stream:
        ...     for event in stream:
        ...         print(event)
        ... # <-- this line calls __exit__
        """
        self.close()

    def __iter__(self) -> typing.Iterator[WatchEvent]:
        """
        Returns the iterator.
        """
        return self
