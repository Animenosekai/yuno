import inspect
import threading
import typing
import pymongo.database
import pymongo.collection

from saki import encoder, objects, database
from saki.direction import IndexDirectionType
from saki.watch import OperationType, Watch

BSONEncoder = encoder.SakiBSONEncoder()
TypeEncoder = encoder.SakiTypeEncoder()


class SakiCollection(object):
    __type__: "objects.SakiDict" = None
    __overwritten__ = {"__type__", "__overwritten__", "__name__", "__annotations__", "__database__", "__collection__", "__class__",  # we need to overwrite this to avoid getting the super class
                       "__init__", "find", "index", "watch", "on", "_watch_loop", "__realtime__", "callbacks", "__delitem__", "__delattr__", "__setitem__", "__setattr__", "__getitem__", "__getattr__", "__repr__"}

    __name__: str
    __annotations__: dict[str, type]
    __database__: "database.SakiDatabase"
    __collection__: pymongo.collection.Collection

    __realtime__: bool = False
    __callbacks__: dict[OperationType, list[typing.Callable]] = {}

    def __init__(self, database: "database.SakiDatabase", name: str = "__saki_test__") -> None:
        if self.__type__ is None:
            super().__setattr__("__type__", objects.SakiDict)
        super().__setattr__("__name__", str(name))
        super().__setattr__("__annotations__", self.__annotations__ if hasattr(self, "__annotations__") else {})
        super().__setattr__("__database__", database)
        super().__setattr__("__collection__", database.__database__.get_collection(name))
        threading.Thread(target=self._watch_loop, daemon=True).start()

    def find(self, filter: dict = None, include: list[str] = None, exclude: list[str] = None, limit: int = 0, defered: bool = False, **kwargs) -> typing.Iterable["objects.SakiDict"]:
        """
        Find documents in the collection

        Parameters
        ----------
        filter:
            A dictionary of filters to apply to the query.
        include:
            A list of attributes to include in the result.
        exclude:
            A list of attributes to exclude from the result.
        limit:
            The maximum number of documents to return.
        defered:
            If True, a generator will be returned and results will be yielded when necessary.
            If False, the results will be returned immediately and everything will be in memory.
        **kwargs:
            Keyword arguments to pass to the find method
            You can therefore use the function like so:
            >>> collection.find(name="John", age={"$gt": 18})
            [SakiDict({"username": "Animenosekai", "rank": 1}), SakiDict({"username": "Anise", "rank": 2})]

        Returns
        -------
         list[SakiDict]
            A list of documents
        """
        filter = filter if filter is not None else {}
        filter.update(kwargs)
        filter = {str(k): BSONEncoder.default(v) for k, v in filter.items()}
        projection = {str(field): True for field in (include or [])}
        projection.update({str(field): False for field in (exclude or [])})
        if len(projection) > 0:
            projection["_id"] = True  # Always include _id
        else:  # If there are no fields to include or exclude, we don't need any projection
            projection = None

        if defered:
            def _generator():
                for doc in self.__collection__.find(filter=filter, projection=projection, limit=limit):
                    name = doc.get("_id")
                    yield TypeEncoder.default(doc, _type=self.__annotations__.get(name, self.__type__), field="", collection=self, _id=name)
            return _generator

        results: list[objects.SakiDict] = []
        for doc in self.__collection__.find(filter=filter, projection=projection, limit=limit):
            name = doc.get("_id")
            cast = self.__annotations__.get(name, self.__type__)

            annotations = encoder.get_annotations(cast)

            data = {k: encoder.SakiTypeEncoder().default(
                v,
                _type=annotations.get(k, None),
                field=k,
                collection=self,
                _id=name
            ) for k, v in doc.items()}

            # results.append(TypeEncoder.default(doc, _type=cast, field="", collection=self, _id=name))
            results.append(cast(_id=name, collection=self, field="", data=data))
        return results

    def index(self, keys: typing.Union[str, list[tuple[str, IndexDirectionType]]], name: str = None, unique: bool = True, background: bool = True, sparse: bool = True, **kwargs) -> None:
        """
        Creates an index for this collection

        Parameters
        ----------
        keys: str or list[tuple[str, IndexDirectionType]]
            The keys to index.
        name: str
            The name of the index.
        unique: bool
            Whether the index should be unique.
        background: bool
            Whether the index should be created in the background.
        sparse: bool
            Whether documents without the field should be ignored or not.
        **kwargs:
            Keyword arguments to pass to pymongo's create_index method.
        """
        default = {
            "background": background,
            "unique": unique,
            "sparse": sparse
        }
        if name is not None:
            default["name"] = name
        default.update(kwargs)
        self.__collection__.create_index(keys, **default)

    # TODO: Implement update() and aggregate()

    def update(self, *args, **kwargs):
        return self.__collection__.update_one(*args, **kwargs)

    def aggregate(self, pipeline, *args, **kwargs):
        return self.__collection__.aggregate(pipeline, *args, **kwargs)

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
        return Watch(self.__collection__, pipeline=final_pipeline, full_document=full_document, error_limit=error_limit, error_expiration=error_expiration, **kwargs)

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

    def __delitem__(self, name: str) -> None:
        self.__collection__.delete_one({"_id": name})

    def __delattr__(self, name: str) -> None:
        self.__delitem__(name)

    def __setitem__(self, name: str, value: dict) -> None:
        self.__collection__.replace_one({"_id": name}, BSONEncoder.default(value), upsert=True)

    def __setattr__(self, name: str, value: dict) -> None:
        if name == "__name__":
            return self.__init__(database=self.__database__, name=value)  # reinitializing the collection because it's a different one
        if name == "__realtime__":
            if not self.__realtime__ and value:
                super().__setattr__(name, value)
                threading.Thread(target=self._watch_loop, daemon=True).start()
                return
            return super().__setattr__(name, value)
        self.__setitem__(name, value)

    def __getitem__(self, name: str) -> "objects.SakiDict":
        data = self.find(_id=name, limit=1)
        if len(data) <= 0:
            raise KeyError("No document with name '{}' found".format(name))
        return data[0]

    def __getattribute__(self, name: str) -> typing.Union["objects.SakiDict", typing.Any]:
        if name in super().__getattribute__("__overwritten__"):
            return super().__getattribute__(name)
        return self.__getitem__(name)

    def __repr__(self):
        return "SakiCollection('{}')".format(self.__name__)
