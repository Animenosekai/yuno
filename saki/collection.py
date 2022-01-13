import typing
import pymongo.database

from saki import encoder, document

IndexDirection = typing.TypeVar("IndexDirection")


class SakiCollection(object):
    __type__ = document.SakiDocument

    def __init__(self, database: pymongo.database.Database, name: str = "__saki_test__") -> None:
        self.__database__ = database
        self.__collection__ = database[name]
        self.__name__ = str(name)
        self.__annotations__ = self.__annotations__ if hasattr(self, "__annotations__") else {}

    def find(self, filter: dict = None, include: list[str] = None, exclude: list[str] = None, limit: int = 0, **kwargs) -> list[document.SakiDocument]:
        """
        Find documents in the collection

        Parameters
        ----------
        **kwargs:
            Keyword arguments to pass to the find method
            You can use the function like so:
            >>> collection.find(name="John", age={"$gt": 18})
            [SakiDocument(_id="000000", collection='accounts'), SakiDocument(_id="000001", collection='accounts')]

        Returns
        -------
         list[SakiDocument]
            A list of documents
        """
        filter = filter if filter is not None else {}
        filter.update(kwargs)
        filter = {str(k): encoder.BSONEncoder.default(v) for k, v in filter.items()}
        projection = {str(field): True for field in include}
        projection.update({str(field): False for field in exclude})
        results = []
        for doc in self.__collection__.find(filter=filter, projection=projection, limit=limit):
            name = doc.get("_id")
            collection = super().__getattribute__("__collection__")
            if name in self.__annotations__:
                results.append(self.__annotations__[name](collection, name, doc))
            else:
                results.append(document.SakiDocument(collection, name, doc))
        return results

    def index(self, keys: typing.Union[str, list[tuple[str, IndexDirection]]], name: str = None, unique: bool = True, background: bool = True, sparse: bool = True, **kwargs) -> None:
        """
        Creates an index for this collection
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

    def __delattr__(self, name: str) -> None:
        self.__delitem__(name)

    def __delitem__(self, name: str) -> None:
        self.__collection__.delete_one({"_id": name})

    def __setitem__(self, name: str, value: document.SakiDocument) -> None:
        value.__collection__.update_one({"_id": name}, {"$set": encoder.BSONEncoder.default(value.__dict__)}, upsert=True)

    def __getattr__(self, name: str) -> document.SakiDocument:
        return self.__getitem__(name)

    def __getitem__(self, name: str) -> document.SakiDocument:
        return self.__annotations__[name](self.__collection__, name) if name in self.__annotations__ else document.SakiDocument(self.__collection__, name)
