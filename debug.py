from nasse.timer import Timer
from pymongo import MongoClient
from mongo_secret import URI
from saki.client import SakiClient

from saki.objects import SakiDict
from saki.database import SakiDatabase
from saki.collection import SakiCollection


class CustomObject(SakiDict):
    def __init__(self, _id, collection, field, data=None) -> None:
        print("Initializing CustomObject")
        super().__init__(_id, collection, field, data)

    hello: str = "world"
    do_not_exist: str = "this does not exist"


class CustomDocument(SakiDict):
    def __init__(self, _id, collection, field, data=None) -> None:
        print("Initializing CustomDocument")
        super().__init__(_id, collection, field, data)

    __lazy__ = ["hello"]

    hello: str
    world: str = "heyhey"
    a: CustomObject


class CustomCollection(SakiCollection):
    a: CustomDocument

    def __init__(self, database, name: str = "__saki_test__") -> None:
        print("Initializing CustomCollection")
        super().__init__(database, name)


class CustomDatabase(SakiDatabase):
    __saki_test__: CustomCollection

    def __init__(self, client: MongoClient, name: str = "__sakit_test__") -> None:
        print("Initializing CustomDatabase")
        super().__init__(client, name)


class CustomClient(SakiClient):
    test_database: CustomDatabase

    def __init__(self, uri: str):
        print("Initializing CustomClient")
        super().__init__(uri)


with Timer() as t:
    test_client = CustomClient(URI)
    print(test_client)
    test_database = test_client.test_database
    test_collection = test_database.__saki_test__
    test_document = test_collection.a
    test_object = test_document.a
    print("test_collection.count():", test_collection.count())
    print('"a" in test_collection:', "a" in test_collection)
    print('"n/a" in test_collection:', "n/a" in test_collection)
    print("test_collection.find():", test_collection.find())
    print("test_collection.find(defered=True):", test_collection.find(defered=True))
    print("list(test_collection.find(defered=True))", list(test_collection.find(defered=True)))
    print("test_document:", test_document)
    print("test_document.hello:", test_document.hello)
    print("test_document.world:", test_document.world)
    print("test_document.a:", test_document.a)
    print("test_document.a.hello:", test_document.a.hello)
    print("test_document.a.do_not_exist:", test_document.a.do_not_exist)

print("It took", t.time, "sec. to execute")
# print(CustomDatabase(client, "test_database").__saki_test__.a.world)

# test_collection = CustomDatabase(client, "test_database").__saki_test__
# test_collection = database.__saki_test__
# print(test_collection.find())


"""
with Timer() as timer:
    class Account(SakiDocument):
        username: str = "default_username"
        password: str = "default_password"
        list_test: list[int] = []
        dict_test: dict

    class TestCollection(SakiCollection):
        a: Account

    test_collection = TestCollection(database, "account")

    print(test_collection.find())
    print(test_collection.find(username="test"))
    print(test_collection.find(username="hello"))

    a = Account(collection, _id="a")
    # print(a.username)
    a.username = "hello"
    # print(a)
    # print(a.username)
    # print(a.list_test)
    a.list_test.extend([1, 2, 3, 4, 5, 6])
    # print(a.list_test)
    a.list_test.pop(2)
    # print(a.list_test)
    a.list_test.remove(1)
    # print(a.list_test)
    a.list_test.reverse()
    # print(a.list_test)
    a.list_test.sort()
    # print(a.list_test)
    a.list_test[2] = 4
    # print(a.list_test)
    a.list_test.clear()
    # print(a.list_test)
    # print(a.dict_test)
    a.dict_test.update({"a": 1, "b": 2, "c": 3})
    # print(a.dict_test)
    a.dict_test.pop("a")
    # print(a.dict_test)
    a.dict_test.popitem()
    # print(a.dict_test)
    # print(a.dict_test.b)
    # print(a.dict_test["b"])
    a.dict_test.a = 1
    # print(a.dict_test)
    a.dict_test["c"] = 3
    # print(a.dict_test)
    # print(a.dict_test.items())
    # print(a.dict_test.keys())
    # print("c" in a.dict_test)
    # print(a.dict_test.__contains__("c"))

print(timer.time)
"""
