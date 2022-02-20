def is_unpackable(obj: typing.Any):
    """
    Checks if the given object is unpackable or not (if you can use **obj or not)
    """
    return all(hasattr(obj, attr) for attr in ('keys', '__getitem__'))
