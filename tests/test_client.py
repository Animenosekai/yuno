import time

import pymongo
import yuno

from . import init


def create_db(client: yuno.YunoClient):
    client.test_database.test_collection.test = {"hello": "world"}


@init.use_client
def test_attributes(mongo, client: yuno.YunoClient):
    init.log("client ~ Testing attributes")
    assert client.host == mongo.host or client.host in ("localhost", "127.0.0.1")
    # assert client.port == mongo.port
    init.log(f"client ~ Testing attributes ~ client.port = {client.port}")
    init.log(f"client ~ Testing attributes ~ mongo.port = {mongo.port}")
    assert client.__realtime__ == False
    assert isinstance(client.__client__, pymongo.MongoClient)
    assert isinstance(client.server_info(), yuno.client.BuildInfo)


@init.use_client
def test_methods(client: yuno.YunoClient):
    init.log("client ~ Testing methods")
    assert isinstance(client.database_names(), list)
    assert len(client.database_names()) == 3

    create_db(client)
    assert len(client.database_names()) == 4
    assert "test_database" in client.database_names()
    assert client.get_database("test_database").__name__ == client.test_database.__name__
    assert client.get_database("test_database").__name__ == client["test_database"].__name__
    client.drop_database("test_database")
    assert len(client.database_names()) == 3

    assert isinstance(client.watch(), yuno.watch.Watch)


@init.use_client
def test_pythonic(client: yuno.YunoClient):
    init.log("client ~ Testing pythonic behavior")
    assert len(client.database_names()) == 3
    create_db(client)
    assert len(client.database_names()) == 4

    del client.test_database
    assert len(client.database_names()) == 3
    create_db(client)
    assert len(client.database_names()) == 4

    del client["test_database"]
    assert len(client.database_names()) == 3


@init.use_client
def test_realtime(client: yuno.YunoClient):
    init.log("client ~ Testing realtime")
    assert client.__realtime__ == False
    client.__realtime__ = True
    assert client.__realtime__ == True
    client.__realtime__ = False
    assert client.__realtime__ == False
    registry = []

    def callback(event, client):
        registry.append({
            "event": event,
            "client": client
        })
        init.log(f"client ~ Testing realtime ~ Received Event: {event}")

    for operation in (yuno.Operation.DELETE, yuno.Operation.DROP, yuno.Operation.DROP_DATABASE, yuno.Operation.INSERT, yuno.Operation.INVALIDATE, yuno.Operation.RENAME, yuno.Operation.REPLACE, yuno.Operation.UPDATE):
        client.on(operation, callback)

    create_db(client)
    del client.test_database

    start = time.time()

    while len(registry) <= 0 and time.time() - start < init.REALTIME_TIMEOUT:
        time.sleep(0.1)

    assert len(registry) > 0
    init.log(f"client ~ Testing realtime ~ Realtime Registry: {registry}")
    assert registry[0]["client"] == client
