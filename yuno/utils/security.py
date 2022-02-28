import typing

import yuno


def check_key_type(key: typing.Union[str, bytes]):
    """
    Enforce the type of the key to bytes.

    Parameters
    ----------
    key: str | bytes
        The key to check

    Returns
    -------
    str
        The key as bytes
    """
    if isinstance(key, bytes):
        return key
    return str(key).encode("utf-8")


def get_security_collection(obj: typing.Union["yuno.YunoClient", "yuno.YunoDatabase", "yuno.YunoCollection"]):
    """
    Get the security collection of the given object.

    Parameters
    ----------
    obj: yuno.YunoClient | yuno.YunoDatabase | yuno.YunoCollection
        The object to get the security collection from
    """
    if isinstance(obj, yuno.YunoClient):
        return obj["__yuno__"]["__security__"]
    if isinstance(obj, yuno.YunoDatabase):
        return obj["__security__"]
    return obj
