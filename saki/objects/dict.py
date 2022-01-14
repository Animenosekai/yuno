import typing

from nasse.utils.annotations import Default
from saki import encoder

from saki import object as _object


class SakiDict(_object.SakiObject, dict):
    """
    An object behaving like a Python dict which is linked to the database.
    """
    __storage__: dict
    __overwritten__ = _object.SakiObject.__overwritten__.union(
        {"__fetch_from_db__", "__lazy_fetch__", "clear", "pop", "popitem", "setdefault", "update"})

    def __lazy_fetch__(self, lazy_obj: encoder.LazyObject) -> typing.Any:
        data = list(self.__collection__.__collection__.aggregate([
            {"$match": {"_id": encoder.BSONEncoder.default(self.__id__)}},
            {"$replaceRoot": {"newRoot": "${}".format(self.__field__)}},
            {"$project": {"_id": False, lazy_obj.field: True}}
        ]))
        if len(data) <= 0:
            raise ValueError("The field '{}.{}' does not exist in the document '{}' on collection {}.".format(
                self.__field__, lazy_obj.field, self.__id__, self.__collection__))
        return data[0][lazy_obj.field]

    def __fetch_from_db__(self) -> typing.Union[list, dict]:
        pipeline = [
            {'$match': {'_id': encoder.BSONEncoder.default(self.__id__)}},
            {'$replaceRoot': {'newRoot': '${}'.format(self.__field__)}}
        ]
        if len(self.__lazy__) > 0:
            pipeline.append({'$unset': [str(attribute) for attribute in self.__lazy__]})
        data = list(self.__collection__.__collection__.aggregate(pipeline))
        if len(data) <= 0:
            return {}
        annotations = self.__annotations__
        data = {k: encoder.TypeEncoder.default(
            v,
            _type=annotations.get(k, None),
            field="{}.{}".format(self.__field__, k),
            collection=self.__collection__,
            _id=self.__id__
        ) for k, v in data[0].items()}
        data.update({field: encoder.LazyObject(field) for field in self.__lazy__})
        return data

    def clear(self) -> None:
        """
        Clears the current object from the database.

        Example
        --------
        >>> document.name.clear()
        #    Initial Document
        #      {'name': {'first': 'John', 'last': 'Doe'}}
        #    Updated Document
        #      {'name': {}}
        """
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: {}}})
        self.__storage__.clear()

    def pop(self, key: typing.Any, default: typing.Any = Default(None)) -> typing.Any:
        """
        Removes the 'key' from the current object.

        Example
        --------
        >>> document.name.pop('first')
        'John'
        #    Initial Document
        #      {'name': {'first': 'John', 'last': 'Doe'}}
        #    Updated Document
        #      {'name': {'last': 'Doe'}}

        Note
        -----
            If 'key' is not in the current object, 'default' is returned if provided, else a KeyError is raised.
        """
        copied = self.__storage__.copy()
        value = copied.pop(key, default)
        if isinstance(value, Default):  # no value coming from the user should be a nasse.utils.annotations.Default instance
            raise KeyError(key)
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        super().__setattr__("__storage__", copied)
        return value

    def popitem(self) -> tuple[typing.Any, typing.Any]:
        """
        If python>=3.7
            Removes the item that was last inserted into the dictionary.
        else:
            Removes a random item from the dictionary.

        Example
        --------
        >>> document.name.popitem()
        ('first', 'John')
        #    Initial Document
        #      {'name': {'first': 'John', 'last': 'Doe'}}
        #    Updated Document
        #      {'name': {'last': 'Doe'}}
        """
        copied = self.__storage__.copy()
        key, value = copied.popitem()
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        super().__setattr__("__storage__", copied)
        return key, value

    def setdefault(self, key: typing.Any, default: _object.Any = None) -> typing.Union[_object.Any, typing.Any]:
        """
        If 'key' is in the current object, returns its value.
        If 'key' is not in the current object, inserts it with a value of 'default' and returns 'default'.

        Example
        --------

        ### When 'key' is in the current object
        >>> document.name.setdefault('first', 'Jane')
        'John'
        #    Initial Document
        #      {'name': {'first': 'John', 'last': 'Doe'}}
        #    Updated Document
        #      {'name': {'first': 'John', 'last': 'Doe'}}

        ### When 'key' is not in the current object
        >>> document.name.setdefault('middle', 'Jane')
        'Jane'
        #    Initial Document
        #      {'name': {'first': 'John', 'last': 'Doe'}}
        #    Updated Document
        #      {'name': {'first': 'John', 'last': 'Doe', 'middle': 'Jane'}}
        """
        copied = self.__storage__.copy()
        value = copied.setdefault(key, default)
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        super().__setattr__("__storage__", copied)
        return value

    def update(self, iterable: typing.Iterable = None, **kwargs) -> None:
        """
        Updates the current object with the provided dictionary.

        Parameters
        ----------
        iterable : typing.Iterable
            The dictionary or iterable of key/value pair to update the current object with.
        **kwargs : typing.Any
            Each keyword argument is a key=value in the dictionary to update the current object with.

        Example
        --------
        >>> document.name.update({'first': 'Jane', 'middle': 'Jane'})
        or
        >>> document.name.update(first='Jane', middle='Jane')
        #    Initial Document
        #      {'name': {'last': 'Doe'}}
        #    Updated Document
        #      {'name': {'last': 'Doe', 'first': 'Jane', 'middle': 'Jane'}}
        """
        copied = self.__storage__.copy()
        copied.update(iterable or [], **kwargs)
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: encoder.BSONEncoder.default(copied)}})
        super().__setattr__("__storage__", copied)
