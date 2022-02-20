from mongo_secret import URI
from yuno.client import YunoClient

from yuno.objects import YunoDict
from yuno.database import YunoDatabase
from yuno.collection import YunoCollection


class CustomObject(YunoDict):
    hello: str = "world"
    do_not_exist: str = "this does not exist"  # its default value if not found in db


class CustomDocument(YunoDict):
    __lazy__ = ["hello"]  # lazy loaded attribute

    hello: str
    world: str = "heyhey"
    a: CustomObject  # nested object ^^


class SpecialDocument(YunoDict):
    __lazy__ = ["specialAttributes"]

    specialAttributes: list[str]
    version: str


class CustomCollection(YunoCollection):
    __type__ = CustomDocument  # the default type of document in the collection

    special: SpecialDocument  # a special document type


class CustomDatabase(YunoDatabase):
    __yuno_test__: CustomCollection


class CustomClient(YunoClient):
    test_database: CustomDatabase


test_document = CustomClient(URI).test_database.__yuno_test__.a
print(test_document)
print(test_document.hello)
print(test_document.world)
print(test_document.a)
print(test_document.a.hello)
print(test_document.a.do_not_exist)
