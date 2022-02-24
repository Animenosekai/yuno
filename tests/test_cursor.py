import yuno

from . import init


@init.use_cursor
def test_arguments(cursor: yuno.cursor.Cursor):
    init.log("cursor ~ Testing arguments")
    assert cursor.verification == init.verification_callback
    cursor.disk_use = False
    assert cursor.disk_use == False
    cursor.disk_use = True
    assert cursor.disk_use == True


@init.use_cursor
def test_methods(collection: yuno.YunoCollection, cursor: yuno.cursor.Cursor):
    init.log("cursor ~ Testing methods")
    assert cursor.alive == True

    cursor.explain()

    collection.index("_id", background=False)
    assert cursor.hint("_id") == cursor
    assert cursor.limit(10) == cursor
    assert cursor.sort("_id") == cursor
    assert cursor.skip(0) == cursor
    assert cursor.next() is not None
    assert cursor.try_next() is None
    try:
        cursor.next()
    except Exception as err:
        assert isinstance(err, StopIteration)

    cursor.close()
    assert cursor.alive == False


@init.use_cursor
def test_pythonic(cursor: yuno.cursor.Cursor):
    init.log("cursor ~ Testing pythonic behavior")
    for i in cursor:
        init.log(f"cursor ~ Element from cursor: {i}")
