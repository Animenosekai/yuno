import typing
import pymongo.database

from saki import encoder, document

MongoDBIndexDirection = typing.TypeVar("MongoDBIndexDirection")


class SakiCollection(object):
    def __init__(self, database: pymongo.database.Database, name: str = "__saki_test__") -> None:
        self.__database__ = database
        self.__collection__ = database[name]
        self.__name__ = str(name)
        super().__setattr__("__attributes__", [attribute for attribute in set(
            ["_id"] + list(dir(self)) + list(self.__annotations__.keys())) if not attribute.startswith("__")])

    def find(self, **kwargs) -> list[document.SakiDocument]:
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
        annotations = self.__annotations__ if hasattr(self, "__annotations__") else {}
        results = []
        for doc in self.__collection__.find({str(k): encoder.BSONEncoder.default(v) for k, v in kwargs.items()}):
            name = doc.get("_id")
            if name in annotations:
                results.append(annotations[name](self.__collection__, name, doc))
            else:
                results.append(document.SakiDocument(self.__collection__, name, doc))
        return results

    def index(self, keys: typing.Union[str, list[tuple[str, MongoDBIndexDirection]]], name: str = None, unique: bool = True, background: bool = True, sparse: bool = True, **kwargs) -> None:
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
        annotations = self.__annotations__ if hasattr(self, "__annotations__") else {}
        return annotations[name](self.__collection__, name) if name in annotations else document.SakiDocument(self.__collection__, name)
