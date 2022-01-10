from saki.document import SakiDocument
from pymongo import MongoClient

client = MongoClient()
database = client["test"]
collection = database["account"]


class Account(SakiDocument):
    username: str = "default_username"
    password: str = "default_password"
    list_test: list = []


a = Account(collection, _id="a")
print(a.list_test)
a.list_test.extend([1, 2, 3, 4, 5, 6])
print(a.list_test)
a.list_test.pop(2)
print(a.list_test)
a.list_test.remove(1)
print(a.list_test)
a.list_test.reverse()
print(a.list_test)
a.list_test.sort()
print(a.list_test)
a.list_test[2] = 4
print(a.list_test)
a.list_test.clear()
print(a.list_test)
