"""
dict.py

Contains the YunoDict class.
"""

import typing
import collections.abc

from yuno import utils
from yuno.utils.annotations import Default
from yuno import encoder

from yuno import object as _object


class YunoDict(_object.YunoObject, dict):
    """
    An object behaving like a Python dict which is linked to the database.
    """
    __storage__: dict
    __overwritten__ = _object.YunoObject.__overwritten__.union(
        {"__fetch_from_db__", "__lazy_fetch__", "__post_verification__", "keys", "get", "clear", "pop", "popitem", "setdefault", "update", "to_dict"})

    def __lazy_fetch__(self, lazy_obj: encoder.LazyObject) -> typing.Any:
        pipeline = [{"$match": {"_id": encoder.YunoBSONEncoder().default(self.__id__)}}]
        if self.__field__:
            pipeline.append({"$replaceRoot": {"newRoot": "${}".format(self.__field__)}})
        pipeline.append({"$project": {"_id": False, lazy_obj.field: True}})

        data = list(self.__collection__.__collection__.aggregate(pipeline))
        if len(data) <= 0:
            raise ValueError("The field '{}.{}' does not exist in the document '{}' on collection {}.".format(
                self.__field__, lazy_obj.field, self.__id__, self.__collection__))
        return data[0][lazy_obj.field]

    def __fetch_from_db__(self) -> typing.Union[list, dict]:
        pipeline = [{'$match': {'_id': encoder.YunoBSONEncoder().default(self.__id__)}}]
        if self.__field__:
            pipeline.append({'$replaceRoot': {'newRoot': '${}'.format(self.__field__)}})
        if len(self.__lazy__) > 0:
            pipeline.append({'$unset': [str(attribute) for attribute in self.__lazy__]})
        data = list(self.__collection__.__collection__.aggregate(pipeline))
        if len(data) <= 0:
            return {}

        annotations = self.__annotations__
        data = {k: encoder.YunoTypeEncoder().default(
            v,
            _type=annotations.get(k, None),
            field="{}.{}".format(self.__field__, k) if self.__field__ else k,
            previous=self,
            _id=self.__id__
        ) for k, v in data[0].items()}

        # placing LazyObjects
        data.update({field: encoder.LazyObject(field) for field in self.__lazy__})
        return data

    def __post_verification__(self):
        # adding the defaults
        defaults = set(dir(self)).difference(set(dir(self.__storage__)).union(self.__overwritten__).union({"__dict__", "__weakref__", "__module__"}))
        for k in defaults:
            if k not in self.__storage__:
                self.__storage__[k] = encoder.YunoTypeEncoder().default(
                    self.__class__.__dict__[k],
                    _type=self.__annotations__.get(k, None),
                    field="{}.{}".format(self.__field__, k) if self.__field__ else k,
                    previous=self,
                    _id=self.__id__
                )

    def keys(self) -> collections.abc.KeysView:
        return self.__storage__.keys()

    def get(self, name: str, default: typing.Any = None) -> typing.Any:
        """
        Returns the value of the 'name' field.

        Parameters
        ----------
        name : str
            The name of the field to return.
        default : typing.Any, default=None
            The value to return if the field is not found.

        Example
        --------
        >>> document.name.get('first')
        'John'
        >>> document.name.get('first', 'Jane')
        'John'
        >>> document.name.get('last')
        None
        >>> document.name.get('last', 'Jane')
        'Jane'
        #    Initial Document
        #      {'name': {'first': 'John'}}
        """
        try:
            return self.__getitem__(name)
        except KeyError:
            return default

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
        if self.__field__ == "":
            self.__collection__.__collection__.delete_one({"_id": self.__id__})
        else:
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
        if isinstance(value, Default):  # no value coming from the user should be a utils.annotations.Default instance
            raise KeyError(key)
        if self.__field__ == "":
            self.__collection__.__collection__.replace_one({"_id": self.__id__}, encoder.YunoBSONEncoder().default(copied))
        else:
            self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: encoder.YunoBSONEncoder().default(copied)}})
        super().__setattr__("__storage__", copied)
        return value

    def popitem(self) -> typing.Tuple[typing.Any, typing.Any]:
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
        if self.__field__ == "":
            self.__collection__.__collection__.replace_one({"_id": self.__id__}, encoder.YunoBSONEncoder().default(copied), upsert=True)
        else:
            self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: encoder.YunoBSONEncoder().default(copied)}})
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
        if self.__field__ == "":
            self.__collection__.__collection__.replace_one({"_id": self.__id__}, encoder.YunoBSONEncoder().default(copied))
        else:
            self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: encoder.YunoBSONEncoder().default(copied)}})
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
        if self.__field__ == "":
            self.__collection__.__collection__.replace_one({"_id": self.__id__}, encoder.YunoBSONEncoder().default(copied), upsert=True)
        else:
            self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: encoder.YunoBSONEncoder().default(copied)}})
        super().__setattr__("__storage__", copied)

    def to_dict(self, exclude: typing.Union[str, typing.List[str]] = None, camelCase: bool = False) -> dict:
        """
        Returns the current object as a dictionary.

        Parameters
        ----------
        exclude : str or list[str], default=None
            The field(s) to exclude from the dictionary.
        camelCase : bool, default=False
            If True, the keys of the dictionary will be camelCased.

        Example
        --------
        >>> document.name.to_dict()
        {'first': 'John', 'last': 'Doe'}
        """
        data = self.__storage__
        if exclude is None:
            exclude = []
        elif isinstance(exclude, str):
            exclude = [exclude]
        for e in exclude:
            data.pop(e, None)
        if camelCase:
            return {utils.string.toCamelCase(k): v for k, v in data.items()}
        return data
