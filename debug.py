from nasse.timer import Timer
from pymongo import MongoClient
from mongo_secret import URI

from saki.objects import SakiDict
from saki.database import SakiDatabase
from saki.collection import SakiCollection

client = MongoClient(URI)


class CustomDocument(SakiDict):
    hello: str
    world: str = "heyhey"


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


print(CustomDatabase(client, "test_database").__saki_test__.a.world)

test_collection = CustomDatabase(client, "test_database").__saki_test__
# test_collection = database.__saki_test__
print(test_collection.find())

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
