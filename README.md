# `saki`

 An account and database management framework, completing Nasse

***Manipulate your databases as if you never leaved Python***

[![PyPI version](https://badge.fury.io/py/saki.svg)](https://pypi.org/project/saki/)
[![Downloads](https://static.pepy.tech/personalized-badge/saki?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Total%20Downloads)](https://pepy.tech/project/saki)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/saki)](https://pypistats.org/packages/saki)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/saki)](https://pypi.org/project/saki/)
[![PyPI - Status](https://img.shields.io/pypi/status/saki)](https://pypi.org/project/saki/)
[![GitHub - License](https://img.shields.io/github/license/Animenosekai/saki)](https://github.com/Animenosekai/saki/blob/master/LICENSE)
[![GitHub top language](https://img.shields.io/github/languages/top/Animenosekai/saki)](https://github.com/Animenosekai/saki)
[![CodeQL Checks Badge](https://github.com/Animenosekai/saki/workflows/CodeQL%20Python%20Analysis/badge.svg)](https://github.com/Animenosekai/saki/actions?query=workflow%3ACodeQL)
[![Pytest](https://github.com/Animenosekai/saki/actions/workflows/pytest.yml/badge.svg)](https://github.com/Animenosekai/saki/actions/workflows/pytest.yml)
![Code Size](https://img.shields.io/github/languages/code-size/Animenosekai/saki)
![Repo Size](https://img.shields.io/github/repo-size/Animenosekai/saki)
![Issues](https://img.shields.io/github/issues/Animenosekai/saki)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

#### Python

You will need Python 3 to use this module

```bash
# vermin output
Minimum required versions: 3.8
Incompatible versions:     2
```

According to Vermin (`--backport typing`), Python 3.8 is needed for the backport of typing but Python 3.6 should be the minimum with typing correctly backported (with `typing.Literal`)

#### MongoDB

I haven't checked the minimum requirements for the MongoDB features used in this library yet but you should always use the latest versions for maximum security.

Also this framework has been tested on MongoDB `v4.4.5` (locally) and MongoDB `v4.4.12` (on Atlas).

Always check if your Python version works with `saki` before using it in production.

## Installing

### Option 1: From PyPI

```bash
pip install --upgrade saki
```

### Option 2: From Git

```bash
pip install --upgrade git+https://github.com/Animenosekai/saki
```

You can check if you successfully installed it by printing out its version:

```bash
$ python -c "import saki; print(saki.__version__)"
# output:
saki v1.0
```

## Purpose

This framework aims to bring effortless database management and database schemas in Python, in order to make everything predictable and easy to debug.

You will never need to learn and search for obscure MongoDB features again because everything is made to behave like normal Python objects.

## Usage

### Running a MongoDB (`mongod`) process from Python

If you have a MongoDB database already running (for example: using MongoDB Atlas, or on a separate server), you can skip this part.

#### Starting a process

To start a process you will need to create a new `MongoDB` object with the configurations (refer to [Configuration](#Configuration)) and start it from there.

> Example

```python
from saki import MongoDB

server = MongoDB()
server.start() # this will launch MongoDB and wait for it to run
...
server.kill() # this will kill the MongoDB process
```

The `start` method can get extra parameters that will modify the way MongoDB is launched:

- `executable`: The path to the MongoDB executable.
- `wait`: When you have set `fork` to `False`, this is the number of seconds to wait for the process to start. (I was planning to use the output from the process to determine when it is listening for connections but `mongod` doesn't seem to "flush" its output so it was just hanging waiting for new output to come until the process was killed)
- `keep_alive`: Whether to keep the process alive or not (fork will be enabled) after Python quits (it will not register `self.kill` at cleanup).

#### Configuration

MongoDB configuration is made easy with Saki!

You can just pass configuration values into `MongoDB` to configure it!

You can configure a lot of important values natively for now and you can add more obscure ones when launching the process.

##### List of supported configuration values

- `host`: The host of the MongoDB server (net.bindIp)
- `port`: The port of the MongoDB server (net.port)
- `db_path`: The path of the MongoDB database (storage.dbPath)
- `fork`: Whether to fork the MongoDB process or not (processManagement.fork)
- `log_config`: The MongoDB logging configuration (systemLog)
- `max_connections`: The maximum number of connections allowed (net.maxIncomingConnections)
- `json_validation`: Whether to enable the JSON validation or not (net.wireObjectCheck)
- `ipv6`: Whether to enable IPv6 or not (net.ipv6)
- `monitoring`: Whether to enable the free MongoDB monitoring or not (cloud.monitoring.free.state)

##### About LogConfig

The content of the `log_config` parameter should be a `LogConfig` object (or a dictionary containing data to instantiate a `LogConfig` class).

This parameter is a class on its own because of its complexity.

> Parameters

- `verbosity`: The verbosity level of the MongoDB logging system
- `path`: The path of the MongoDB log file. It can also be TERMINAL or SYSLOG (the systemLog.destination value will be set automatically according to this value)
- `append`: Whether to append to the log file or not
- `timezone`: The timezone of the timestamps format
- `debug`: Whether to enable the debug mode or not (this will enable max verbosity and `--traceExceptions`)

> Example

```python
from saki import MongoDB, LogConfig
from saki.launcher import Timezone

server = MongoDB(db_path="./db/test", fork=True, monitoring=False, log_config=LogConfig(verbosity=2, path="./logs/db/test.log", timezone=Timezone.UTC))

server.start()
```

#### Loading and Dumping the configuration

You can also load the config from a file or dump it into a file using the built in methods (available on `LogConfig` and `MongoDB`):

- `to_cli_args` will dump the configuration to a list of CLI arguments to give to the `MongoDB` (`mongod`) process
- `loads` will load the configuration from a YAML string or a dictionary of values
- `load` will load the configuration from a YAML file
- `dumps` will dump the configuration to a YAML string
- `dump` will dump the configuration to a YAML file
- `to_dict` (or `dict(configuration_object)`) will dump the configuration to a dictionary (you have a `camelCase` parameter to make the keys camelCased)

This is especially useful when you already have a configuration file or want to share the configuration to another user not using Saki.

> Example

```python
from saki import MongoDB

server = MongoDB() # will load all of the default configurations
server.load("./db/mongo.conf") # will reinitialize the object with the config file, keeping the default values for values that aren't specified
server.dump("./db/mongo_new.conf") # will dump the configurations to a new file (to share or use later)

# will show the configuration
print("MongoDB configuration")
print("-" * 10)
for key, val in server.to_dict(camelCase=True):
    print(key, "=", val)
```

### Connecting to a MongoDB process

Wether you use the built-in `MongoDB` object to launch a MongoDB process or just host it on the cloud/on another server, you will need to connect to it using `SakiClient`.

Here are the parameters used to connect to a server:

- `host`: The host or list of hostnames to connect to. You can use `host` to pass in a URI string or a MongoDB object (in which case you won't need to use `port`).
- `port`: The port to connect to.
- `tz_aware`: Whether to use timezone aware datetimes or not.
- `connect`: Whether to connect before making any operation to the server or not.
- `kwargs`: Options to pass to the PyMongo client. (you don't need to set `kwargs` manually, just pass the parameters as normal parameters)

> Example

```python
# Using the "MongoDB" object
from saki import MongoDB
from saki import SakiClient

server = MongoDB()
server.start()
client = SakiClient(server) # you are connecting to the server here
```

### Using the client

To access databases from the client, all you need to do is access its name as an attribute or an item:

```python
client.database_name
# or
client["database_name"]
```

In both case, this will return the same SakiDatabase object.

The `client["database_name"]` syntax is especially useful if you use a database with the name of a method overwritten by SakiClient (for example `watch`, `server_info`, `address`, `close`, etc.).

You can find a list of overwritten attributes under the `__overwritten__` attribute.

SakiClient can be used to establish the database schema.

This basically means that you can already type hint databases by creating your own clients.

```python
from saki import SakiClient
from saki import SakiDatabase

class MyClient(SakiClient):
    production: SakiDatabase # you can here use your custom databases (refer to the "Using databases" section)
    scores: SakiDatabase

client = MyClient("mongodb+srv://anise:password@sakitest.host.mongodb.net/production")
client.production # will return the `production` database
# SakiDatabase('production')
```

This helps with establishing a schema and helps your code editor guide you when writing code, resulting in less time searching for types, available databases and looking back at your code.

It has serveral other methods, which are picked and adapted from the original PyMongo `MongoClient`.

> Examples

- `close` is used to close the connection to the server
- `database_names` is used to retrieve the list of databases created.
- `server_info` will return some info about the current MongoDB server in a special object called `BuildInfo` (`saki.client.BuildInfo`).
- `watch` returns a cursor to watch the cluster for changes and events.
- `on` will register a callback function which will be called when the specified operation/event is performed on the server.

You can also use pythonic syntax to make some operations:

- Dropping a database

```python
del client.test
# or
del client["test"]
# will drop (delete) the "test" database
```

### Using databases

A "database" is what holds collections in MongoDB.

To access collections from the client, all you need to do is access its name as an attribute or an item:

```python
database.collection_name
# or
database["collection_name"]
```

In both case, this will return the same SakiCollection object.

The `database["collection_name"]` syntax is especially useful if you use a database with the name of a method overwritten by SakiDatabase (for example `watch`, `on`, `command`, `aggregate`, etc.).

You can find a list of overwritten attributes under the `__overwritten__` attribute.

`SakiCollection` is the class returned by `SakiDatabase` when querying for one.

```python
# using the client variable defined before

accounts = production_database.accounts
# this is SakiCollection object
```

You can define your own databases to type hint them (for the same reasons as before)

```python
from saki import SakiClient, SakiDatabase, SakiCollection

class MyDatabase(SakiDatabase):
    accounts: SakiCollection # you will also be able to create your own collections

class MyClient(SakiClient):
    production: MyDatabase

client = MyClient("mongodb+srv://anise:password@sakitest.host.mongodb.net/production")
production_database = client.production # will return the custom MyDatabase object and code editors will help you write code
# MyDatabase('production')
production_database.accounts # this is a SakiCollection object
```

It has serveral other methods, which are picked and adapted from the original PyMongo `MongoClient`.

> Examples

- `aggregate` is used to perform an aggregation on the database
- `create_collection` is used to create a new collection
- `list_collection_names` returns a list of collections available
- `watch` returns a cursor to watch the database for changes and events.
- `on` will register a callback function which will be called when the specified operation/event is performed on the database.

You can also use pythonic syntax to make some operations:

- Dropping a collection

```python
del database.account
# or
del database["account"]
# will drop (delete) the "account" collection
```

### Using collections

A "collection" is what holds documents in MongoDB.

To access documents from the collection, all you need to do is access its name as an attribute or an item:

```python
collection.document_id
# or
collection["document_id"]
```

In both case, this will return the same SakiCollection object.

The `collection["document_id"]` syntax is especially useful if you use a document with the _id of a method overwritten by SakiCollection (for example `watch`, `on`, `find`, `aggregate`, etc.).

You can find a list of overwritten attributes under the `__overwritten__` attribute.

`SakiCollection` is the class returned by `SakiDatabase` when querying for one.

```python
# using the client variable defined before

accounts = production_database.accounts
# this is SakiCollection object
```

You can define your own collections to type hint them (for the same reasons as before)

```python
from bson import ObjectId
from saki import SakiClient, SakiDatabase, SakiCollection, SakiDict

class MyCollection(SakiCollection):
    special_document: SakiDict # you will also be able to create your own documents

class MyDatabase(SakiDatabase):
    accounts: MyCollection

class MyClient(SakiClient):
    production: MyDatabase

client = MyClient("mongodb+srv://anise:password@sakitest.host.mongodb.net/production")
production_database = client.production
accounts = production_database.accounts
accounts.special_document # this is a SakiDict object
```

There is a special `__type__` attribute which is used to define the default type of the documents in the collection.

This is especially useful if all of the documents in the collection share the same schema.

You can use type hints to define the schema of special documents (a document which gives global information about the collection for example).

It has serveral other methods, which are picked and adapted from the original PyMongo `MongoClient`.

> Examples

- `count` is used to count the number of documents matching the given filter
- `find` is used to find documents matching the given filter
- `index` creates a new index on the collection
- `aggregate` returns an aggregation of documents following the given pipeline
- `watch` returns a cursor to watch the database for changes and events.
- `on` will register a callback function which will be called when the specified operation/event is performed on the database.

You can also use pythonic syntax to make some operations:

- Deleting a document

```python
del collection.special_document
# or
del collection["special_document"]
# will delete the "special_document" document
```

- Set a document (create or replace)

```python
collection.special_document = {"_id": "special_document", "name": "Special document"}
# or
collection["special_document"] = {"_id": "special_document", "name": "Special document"}
# will replace the "special_document" document with the one defined above
```

- Verify if the given document exists

```python
"special_document" in collection
# will return True if the document (with _id == "special_document") exists
```

### Using objects

An "object" is what represents any object in a document, or even the document itself.

To access objects from another object (the highest hierarchy parent object being the document), all you need to do is access its name as an attribute or an item:

```python
document.object_name
# or
document["object_name"]
```

In both case, this will return the same SakiObject object.

The `document["object_name"]` syntax is especially useful if you use an object with its name being of a method overwritten by SakiObject (for example `watch`, `on`, `reload`, `delete`, etc.).

You can find a list of overwritten attributes under the `__overwritten__` attribute.

`SakiObject` is the class returned by `SakiCollection` when querying for one.

```python
# using the client variable defined before

document = accounts.special_document
# this is SakiObject object
```

You can define your own objects to type hint them (for the same reasons as before)

```python
from saki import SakiClient, SakiDatabase, SakiCollection, SakiDict



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


client = CustomClient("mongodb+srv://anise:password@sakitest.host.mongodb.net/production")
test_database = client.test_database
test_collection = test_database.__saki_test__
special_doc = test_collection.special
special_doc # this is a SpecialDocument object
document = test_collection.any_document
document # this is a CustomDocument object
document.hello # this is a str object, but lazy loaded (not loaded until needed)
document.a # this is CustomObject object
document.a.hello # this is a str
document.a.do_not_exist # this is a str (and if it's not found in the db, it will be the value given by default "this does not exist")
```

There is a special `__lazy__` attribute which is used to define attributes which won't be loaded until needed.

This is especially useful for attributes which are expensive to load or not needed in normal circumstances.

You can use type hints to define the schema of some attributes.

Objects acts as regular python objects.

For example, a SakiDict object can be used as a regular python dict:

```python
object # this is a SakiDict object
object.get("key") # this is a str
object.pop("key") # remove the key from the object
object.items() # this is a list of tuples
object.keys() # this is a list of str
...
for key, value in object.items():
    print(key, value)
del object["key"]
```

and a SakiList object can be used as a regular python list:

```python
object # this is a SakiList object
object.append("value") # add a value to the list
object.pop() # remove the last value from the list
object.extend(["value1", "value2"]) # add multiple values to the list
object.index("value") # return the index of the value in the list
object.insert(0, "value") # insert a value at the beginning of the list
object.remove("value") # remove the first value from the list
object.reverse() # reverse the list
object.sort() # sort the list
...
for value in object:
    print(value)
```

Some methods don't come from regular Python data types, but are specific to SakiObjects:

> Examples

- `delete` deletes the current object from the database
- `reload` reloads the current object from the database (replaces the current object with the one from the database)
- `watch` returns a cursor to watch the database for changes and events.
- `on` will register a callback function which will be called when the specified operation/event is performed on the object.

Instead of the `reload` method, you also have a `__realtime__` attribute which you can set to `True` if you want the object to follow the updates on the database (you will have an object which is always up to date).

```python
document # this is a SakiObject (SakiDict, SakiList, etc.) object
document.__realtime__ = True
# this will make the object follow the updates on the database

class CustomObject(SakiDict):
    __realtime__ = True

    hello: str = "world"

class CustomCollection(SakiCollection):
    __type__ = CustomObject

# any object coming from the CustomCollection collection will be a CustomObject object and will be a "realtime" object, following the updates on the database
```

You can also use pythonic syntax to make some operations:

- Deleting a document

```python
del object.key
# or
del object["key"]
# will delete the "key" attribute from the object
```

- Set an attribute (create or replace)

```python
object.key = {"hello": "world"}
# or
object["key"] = {"hello": "world"}
# will replace the "key" attribute with the one defined above
```

- Verify if the given document exists

```python
"key" in object
# will return True if the attribute exists
```

## How it works

Saki works on top of PyMongo to make all of the operations to MongoDB.

## Deployment

This module is currently in development and might contain bugs.

Feel free to use it in production if you feel like it is suitable for your production even if you may encounter issues.

## Contributing

Pull requests are welcome. For major changes, please open a discussion first to discuss what you would like to change.

Please make sure to update the tests as appropriate.

## Built With

- [pymongo](https://docs.mongodb.com/drivers/pymongo/) - To connect to MongoDB databases and make operations
- [psutil](https://github.com/giampaolo/psutil) - For cross-platform process management
- [PyYAML](https://github.com/yaml/pyyaml) - To parse YAML files (MongoDB configuration files)

## Authors

- **Anime no Sekai** - *Initial work* - [Animenosekai](https://github.com/Animenosekai)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
