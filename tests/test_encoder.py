import pathlib
import sys
import uuid
from typing import List, Dict

import yuno

from . import init


class Test:
    def __init__(self, value) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


def test_type():
    encoder = yuno.encoder.YunoTypeEncoder()
    assert encoder.default("1", _type=int) == 1
    assert encoder.default("1", _type=str) == "1"
    assert encoder.default(1, _type=str) == "1"
    assert isinstance(encoder.default("hello", _type=Test), Test)
    assert encoder.default("hello", _type=Test).value == "hello"
    assert isinstance(encoder.default({"hello": "world"}, _type=yuno.YunoDict), yuno.YunoDict)

    if sys.version_info.minor > 8:  # not available for py3.8
        assert all((isinstance(key, str) for key in encoder.default(["hello", 1, None, True], _type=List[str])))
        assert all(isinstance(val, str) for val in encoder.default({"hello": "world", "number": 1}, _type=Dict[str, str]).values())


def test_bson():
    file = f"BSON_TEST_{uuid.uuid4()}"
    with open(file, 'w') as f:
        f.write("Hello World")

    encoder = yuno.encoder.YunoBSONEncoder()

    with open(file, 'r') as f:
        f.seek(1)
        a = f.tell()
        encoder.default(f)
        assert a == f.tell()
        assert encoder.default(f) == f.read()

    pathlib.Path(file).unlink(missing_ok=True)

    assert encoder.default({"a": 1, "b": 2, "c": 3}) == {"a": 1, "b": 2, "c": 3}
    assert encoder.default([1, 2, 3]) == [1, 2, 3]
    assert encoder.default(1) == 1
    assert encoder.default(1.0) == 1.0
    assert encoder.default(True) == True
    assert encoder.default(b"a") == b"a"
    assert encoder.default("a") == "a"
    assert encoder.default(None) == None
    assert encoder.default(Test("a")) == "a"
    assert encoder.default(Test(1)) == "1"
    assert encoder.default(Test(1.0)) == "1.0"
    assert encoder.default(init.TEST_DOCUMENT) == init.TEST_DOCUMENT
    assert encoder.default(init.TEST_OBJECT) == init.TEST_OBJECT
    assert encoder.default(init.TEST_LIST) == init.TEST_LIST
