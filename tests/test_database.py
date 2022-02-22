import time

import pymongo.database
import yuno

from . import init


@init.use_database
def test_attributes(database: yuno.YunoDatabase):
    init.log("database ~ Testing attributes")
    assert database.__realtime__ == False
    assert database.__name__ == "test"
    assert database.__database__.name == "test"
    assert isinstance(database.__database__, pymongo.database.Database)
    assert isinstance(database.__client__, yuno.YunoClient)


@init.use_database
def test_methods(database: yuno.YunoDatabase):
    init.log("database ~ Testing methods")
    assert isinstance(database.list_collection_names(), list)
    assert len(database.list_collection_names()) == 0
    database.create_collection("test_collection")
    assert database.get_collection("test_collection").__name__ == database.test_collection.__name__
    assert len(database.list_collection_names()) == 1
    assert all((isinstance(i, str) for i in database.list_collection_names()))
    assert all((isinstance(i, yuno.YunoCollection) for i in database.list_collections()))
    database.drop_collection("test_collection")
    assert len(database.list_collection_names()) == 0

    assert isinstance(database.watch(), yuno.watch.Watch)


@init.use_database
def test_pythonic(database: yuno.YunoDatabase):
    init.log("database ~ Testing pythonic behavior")
    assert len(database.list_collection_names()) == 0
    database.create_collection("test_collection")
    assert len(database.list_collection_names()) == 1

    assert isinstance(database.test_collection, yuno.YunoCollection)
    assert isinstance(database["test_collection"], yuno.YunoCollection)

    del database.test_collection
    assert len(database.list_collection_names()) == 0
    database.create_collection("test_collection")
    assert len(database.list_collection_names()) == 1

    del database["test_collection"]
    assert len(database.list_collection_names()) == 0


@init.use_database
def test_realtime(database: yuno.YunoDatabase):
    init.log("database ~ Testing realtime")
    assert database.__realtime__ == False
    database.__realtime__ = True
    assert database.__realtime__ == True
    database.__realtime__ = False
    assert database.__realtime__ == False
    registry = []

    def callback(event, client, database):
        registry.append({
            "event": event,
            "client": client,
            "database": database
        })
        init.log(f"database ~ Testing realtime ~ Received Event: {event}")

    for operation in (yuno.Operation.DELETE, yuno.Operation.DROP, yuno.Operation.DROP_DATABASE, yuno.Operation.INSERT, yuno.Operation.INVALIDATE, yuno.Operation.RENAME, yuno.Operation.REPLACE, yuno.Operation.UPDATE):
        database.on(operation, callback)

    database.create_collection("test_collection")
    del database.test_collection

    start = time.time()

    while len(registry) <= 0 and time.time() - start < init.REALTIME_TIMEOUT:
        time.sleep(0.1)

    assert len(registry) > 0
    init.log(f"database ~ Testing realtime ~ Realtime Registry: {registry}")
    assert registry[0]["database"] == database
