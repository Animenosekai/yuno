import time

import pymongo.collection
import yuno

from . import init


@init.use_collection
def test_arguments(database, collection: yuno.YunoCollection):
    init.log("collection ~ Testing arguments")
    assert isinstance(database, yuno.YunoDatabase)
    assert collection.__name__ == "test"
    assert collection.__database__ == database
    assert isinstance(collection, yuno.YunoCollection)
    assert isinstance(collection.__collection__, pymongo.collection.Collection)
    assert collection.__collection__.name == "test"
    assert collection.__realtime__ == False
    assert collection.__type__ == yuno.YunoDict


@init.use_collection
def test_methods(collection: yuno.YunoCollection):
    init.log("collection ~ Testing methods")
    assert len(collection.find()) <= 0
    assert collection.count() == 0
    collection.hello = {'_id': "hello", 'hello': "world"}
    assert len(collection.find()) == 1
    assert collection.count() == 1
    assert len(collection.find(_id="hello")) == 1
    assert len(collection.find(hello="hello")) == 0
    assert len(collection.find(hello="world")) == 1
    assert len(collection.find({"_id": "hello"})) == 1
    assert len(collection.find({"do_not_exist": True})) == 0
    k = list(collection.hello.keys())
    assert "_id" in k and "hello" in k
    v = list(collection.hello.values())
    assert "hello" in v and "world" in v
    assert len(list(collection.aggregate([{"$match": {"hello": "world"}}]))) == 1
    assert len(list(collection.aggregate([{"$match": {"do_not_exist": "hey"}}]))) == 0
    collection.index("hello")
    assert isinstance(collection.watch(), yuno.watch.Watch)


@init.use_collection
def test_pythonic(collection: yuno.YunoCollection):
    init.log("collection ~ Testing pythonic behavior")
    assert collection.count() == 0
    collection.special_document = {"_id": "special_document", "name": "Special document"}
    assert collection.count() == 1
    assert collection.special_document.name == "Special document"
    assert collection.special_document.name == collection["special_document"].name
    assert collection.special_document.name == collection.special_document["name"]
    assert collection.special_document.name == collection["special_document"]["name"]
    del collection.special_document

    assert collection.count() == 0
    collection["special_document"] = {"_id": "special_document", "name": "Special document"}
    assert collection.count() == 1
    assert collection.special_document.name == "Special document"

    assert "special_document" in collection

    collection.special_document = {"_id": "special_document", "name": "Changed Special document"}
    assert collection.special_document.name == "Changed Special document"
    del collection["special_document"]


@init.use_collection
def test_realtime(collection: yuno.YunoCollection):
    init.log("collection ~ Testing realtime")
    assert collection.__realtime__ == False
    collection.__realtime__ = True
    assert collection.__realtime__ == True
    collection.__realtime__ = False
    assert collection.__realtime__ == False
    registry = []

    def callback(event, client, database, collection):
        registry.append({
            "event": event,
            "client": client,
            "database": database,
            "collection": collection
        })
        init.log(f"collection ~ Testing realtime ~ Received Event: {event}")

    for operation in (yuno.Operation.DELETE, yuno.Operation.DROP, yuno.Operation.DROP_DATABASE, yuno.Operation.INSERT, yuno.Operation.INVALIDATE, yuno.Operation.RENAME, yuno.Operation.REPLACE, yuno.Operation.UPDATE):
        collection.on(operation, callback)

    collection.hello = {"_id": "hello", "hello": "world"}
    del collection.hello

    start = time.time()

    while len(registry) <= 0 and time.time() - start < init.REALTIME_TIMEOUT:
        time.sleep(0.1)

    assert len(registry) > 0
    init.log(f"collection ~ Testing realtime ~ Realtime Registry: {registry}")
    assert registry[0]["client"] == collection.__database__.__client__
    assert registry[0]["database"] == collection.__database__
    assert registry[0]["collection"] == collection
