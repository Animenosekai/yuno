from mongo_secret import URI
from saki.client import SakiClient

from saki.objects import SakiDict
from saki.database import SakiDatabase
from saki.collection import SakiCollection


class CustomObject(SakiDict):
    hello: str = "world"
    do_not_exist: str = "this does not exist"  # its default value if not found in db


class CustomDocument(SakiDict):
    __lazy__ = ["hello"]  # lazy loaded attribute

    hello: str
    world: str = "heyhey"
    a: CustomObject  # nested object ^^


class SpecialDocument(SakiDict):
    __lazy__ = ["specialAttributes"]

    specialAttributes: list[str]
    version: str


class CustomCollection(SakiCollection):
    __type__ = CustomDocument  # the default type of document in the collection

    special: SpecialDocument  # a special document type


class CustomDatabase(SakiDatabase):
    __saki_test__: CustomCollection


class CustomClient(SakiClient):
    test_database: CustomDatabase


test_document = CustomClient(URI).test_database.__saki_test__.a
print(test_document)
print(test_document.hello)
print(test_document.world)
print(test_document.a)
print(test_document.a.hello)
print(test_document.a.do_not_exist)
