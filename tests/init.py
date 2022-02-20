import inspect
import sys

import yuno

# CONSTANTS

TEST_OBJECT = {
    "a": 1,
    "b": 2,
    "c": 3,
    "test_dict": {
        "a": 1,
        "b": 2,
        "c": 3
    },
    "float": 1.1,
    "int": 1,
    "test_list": [1, 2, 3],
    "null": None,
    "string": "test",
    "boolean": True
}

TEST_LIST = [
    "string",
    1,
    1.1,
    None,
    [1, 2, 3],
    TEST_OBJECT,
    True
]

TEST_DOCUMENT = {"_id": "test", "hello": "world", "test_list": TEST_LIST, "test_dict": TEST_OBJECT,
                 "boolean": True, "float": 1.1, "int": 1, "null": None, "string": "test"}


KEPT_DATABASES = {'admin', 'local', 'config'}

REALTIME_TIMEOUT = 5

# UTILITY FUNCTIONS


def get_args(func):
    return inspect.signature(func).parameters.keys()


STEP = f"CI/Testing - v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def log(message):
    yuno.utils.logging.log(message, yuno.utils.logging.LogLevels.INFO, step=STEP)


def close(mongo: yuno.MongoDB, client: yuno.YunoClient):
    log("Closing the client connection")
    client.close()
    log("Stop MongoDB")
    mongo.close()

# INITIALIZATION FUNCTIONS


def init_mongo():
    log("Initializing MongoDB")
    mongo = yuno.MongoDB()
    log("Starting MongoDB")
    mongo.start()
    return mongo


def init_client():
    mongo = init_mongo()
    client = yuno.YunoClient(mongo)
    for database in set(client.database_names()).difference({'admin', 'local', 'config'}):
        log(f"Dropping database: {database}")
        del client[database]

    return mongo, client


def init_database():
    mongo, client = init_client()
    log("Initializing Database")
    database = yuno.YunoDatabase(client, "test")
    log("Cleaning up the database")
    for collection in database.collection_names():
        log(f"Dropping collection: {collection}")
        del database[collection]

    return mongo, client, database


def init_collection():
    mongo, client, database = init_database()
    log("Initializing collection")
    collection = yuno.YunoCollection(database, "test")
    log("Cleaning up the collection")
    for document in collection.find(include=["_id"]):
        log(f"Deleting document: {document.__id__}")
        del collection[document.__id__]
    return mongo, client, database, collection


def init_document():
    mongo, client, database, collection = init_collection()
    log("Initializing Document")
    collection.test_document = TEST_DOCUMENT
    return mongo, client, database, collection, collection.test

# DECORATORS


def use_mongo(func):
    def wrapper(*args, **kwargs):
        mongo = init_mongo()
        avail = get_args(func)
        if "mongo" in avail:
            kwargs["mongo"] = mongo
        result = func(*args, **kwargs)
        log("Stopping MongoDB")
        mongo.close()
        return result
    return wrapper


def use_client(func):
    def wrapper(*args, **kwargs):
        mongo, client = init_client()
        avail = get_args(func)
        for arg, value in [("mongo", mongo), ("client", client)]:
            if arg in avail:
                kwargs[arg] = value
        result = func(*args, **kwargs)
        close(mongo, client)
        return result
    return wrapper


def use_database(func):
    def wrapper(*args, **kwargs):
        mongo, client, database = init_database()

        avail = get_args(func)
        for arg, value in [("mongo", mongo), ("client", client), ("database", database)]:
            if arg in avail:
                kwargs[arg] = value
        result = func(*args, **kwargs)
        close(mongo, client)
        return result
    return wrapper


def use_collection(func):
    def wrapper(*args, **kwargs):
        mongo, client, database, collection = init_collection()

        avail = get_args(func)
        for arg, value in [("mongo", mongo), ("client", client), ("database", database), ("collection", collection)]:
            if arg in avail:
                kwargs[arg] = value
        result = func(*args, **kwargs)
        close(mongo, client)
        return result
    return wrapper


def use_document(func):
    def wrapper(*args, **kwargs):
        mongo, client, database, collection, document = init_document()

        avail = get_args(func)
        for arg, value in [("mongo", mongo), ("client", client), ("database", database), ("collection", collection), ("document", document)]:
            if arg in avail:
                kwargs[arg] = value

        result = func(*args, **kwargs)
        close(mongo, client)
        return result
    return wrapper
