from nasse.timer import Timer
from saki.document import SakiDocument
from pymongo import MongoClient

client = MongoClient()
database = client["test"]
collection = database["account"]

with Timer() as timer:
    class Account(SakiDocument):
        username: str = "default_username"
        password: str = "default_password"
        list_test: list[int] = []
        dict_test: dict

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