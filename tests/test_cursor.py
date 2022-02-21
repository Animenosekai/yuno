import yuno

from . import init


def verification_callback(obj):
    init.log(f"cursor ~ Verifying object {obj}")


@init.use_collection
def test_arguments(collection: yuno.YunoCollection):
    collection.hello = {'_id': "hello", 'hello': "world"}
    cursor = collection.__collection__.find({"_id": "hello"})
