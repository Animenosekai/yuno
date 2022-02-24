from . import init

import yuno


@init.use_document
def test_dict(document: yuno.YunoDict):
    init.log("objects ~ Testing YunoDict")
    native = document.__storage__.copy()
    assert native == document

    for attr in dir(native):
        if attr.startswith("__"):
            continue
        if attr == "get":
            assert document.get("test_dict") == native.get("test_dict")
        elif attr == "pop":
            assert document.pop("test_dict") == native.pop("test_dict")
        elif attr == "setdefault":
            assert document.setdefault("test_dict") == native.setdefault("test_dict")
        elif attr == "update":
            assert document.update({"test_dict": 1}) == native.update({"test_dict": 1})
        elif attr == "fromkeys":
            # assert document.fromkeys(["test_dict"]) == native.fromkeys(["test_dict"])
            init.log("objects ~ 'fromkeys' not implemented")
        else:
            if callable(getattr(document, attr)):
                if attr == "values":
                    assert list(document.values()) == list(native.values())
                elif attr == "items":
                    assert list(document.items()) == list(native.items())
                elif attr == "keys":
                    assert list(document.keys()) == list(native.keys())
                else:
                    assert getattr(document, attr)() == getattr(native, attr)()
            else:
                assert getattr(document, attr) == getattr(native, attr)
        assert native == document
        document.clear()
        document.update(init.TEST_DOCUMENT)
        native = document.__storage__.copy()


class TestDocument(yuno.YunoDict):
    test_list: yuno.YunoList


@init.use_document
def test_list(document: TestDocument):
    init.log("objects ~ Testing YunoList")
    document_list = document.test_list
    native = document_list.__storage__.copy()
    assert native == document_list

    for attr in dir(native):
        if attr.startswith("__"):
            continue
        if attr == "append":
            assert document_list.append("appended") == native.append("appended")
        elif attr == "extend":
            assert document_list.extend([1, 2, 3]) == native.extend([1, 2, 3])
        elif attr == "pop":
            assert document_list.pop(0) == native.pop(0)
        elif attr == "remove":
            assert document_list.remove("string") == native.remove("string")
        elif attr == "sort":
            assert document_list.sort(key=str) == native.sort(key=str)
        elif attr == "count":
            assert document_list.count(1) == native.count(1)
        elif attr == "index":
            assert document_list.index(1) == native.index(1)
        elif attr == "insert":
            assert document_list.insert(0, "inserted") == native.insert(0, "inserted")
        else:
            if callable(getattr(document_list, attr)):
                assert getattr(document_list, attr)() == getattr(native, attr)()
            else:
                assert getattr(document_list, attr) == getattr(native, attr)
        assert native == document_list
        document_list.clear()
        document_list.extend(init.TEST_LIST)
        native = document_list.__storage__.copy()
