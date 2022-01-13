import typing

import bson
from nasse.utils.annotations import Default

from saki import collection, encoder

Any = typing.TypeVar("Any")

# TODO: Update some functions to avoid using dict.copy() and list.copy() and take up less memory.


class SakiObject(object):
    """
    An object behaving like a Python object which is linked to the database to update stuff on the fly.
    """
    __overwritten__: set[str] = {"__fetch_from_db__", "__lazy_fetch__", "__overwritten__", "__storage_attributes__", "__storage__", "__id__", "__field__", "__master__", "__collection__",
                                 "__init__", "__getitem__", "__getattribute__", "__setitem__", "__setattr__", "__delitem__", "__delattr__", "__repr__", "__contains__", "delete"}

    __lazy__: list[str] = []
    """
    This is a list of attributes that are lazy loaded.

    A "lazy loaded" attribute is an attribute that is not loaded until needed. It won't be fetched on the document instantiation.

    This should be used for attributes which are expensive to load or not needed in normal circumstances.
    """
    __storage__: typing.Union[dict, list]
    __storage_attributes__: set[str] = set()

    __id__: typing.Union[bson.ObjectId, str, int, typing.Any]
    __field__: str = ""
    __master__: bool = False
    __collection__: collection.SakiCollection

    def __fetch_from_db__(self) -> typing.Union[list, dict]:
        raise NotImplementedError("This method should be implemented by the child class.")

    def __lazy_fetch__(self, lazy_obj: encoder.LazyObject) -> typing.Any:
        raise NotImplementedError("This method should be implemented by the child class.")

    def __init__(self, _id: typing.Union[bson.ObjectId, str, int, typing.Any], collection: collection.SakiCollection, field: str = "", data: typing.Union[dict, list] = None) -> None:
        """
        Initializes the object by fetching the data from the database and intializing it.

        Parameters
        ----------
        _id: bson.ObjectId | str | int | Any
            The _id of the master document.
        collection: SakiCollection
            The collection the object belongs to.
        field: str, default=""
            The field the object belongs to.
        data: dict | list, default=None
            The data to initialize the object with. If None, the data will be fetched from the database.
        """
        super().__setattr__("__id__", _id)
        super().__setattr__("__collection__", collection)
        super().__setattr__("__field__", str(field))

        super().__setattr__("__storage__", data if data is not None else self.__fetch_from_db__())

        if not hasattr(self, "__annotations__"):
            super().__setattr__("__annotations__", {})

        super().__setattr__("__storage_attributes__", set(dir(self.__storage__)).difference(self.__overwritten__))

    def __getitem__(self, name: typing.Union[str, int, slice]) -> None:
        """Gets the attribute 'name' from the database. Example: value = document['name']"""
        data = self.__storage__[name]
        if isinstance(data, encoder.LazyObject):
            data = self.__lazy_fetch__(data)
            encoder.TypeEncoder.default(data, _type=self.__annotations__.get(name, None), field="{}.{}".format(
                self.__field__, name), collection=self.__collection__, _id=self.__id__)
            self.__storage__.__setitem__(name, data)
        return data

    def __getattribute__(self, name: str) -> Any:
        """Gets the attribute 'name' from the object if available (methods, etc.) or from the database. Example: value = document.name"""
        if name in super().__getattribute__("__overwritten__"):
            return super().__getattribute__(name)
        if name in self.__storage_attributes__:
            return super().__getattribute__("__storage__").__getattribute__(name)
        return self.__getitem__(name)

    # def __getattr__(self, name: str) -> None:
    #     """Gets the attribute 'name' from the database. Example: value = document.name"""
    #     if name in self.__storage_attributes__:
    #         return super().__getattribute__("__storage__").__getattribute__(name)
    #     return self.__getitem__(name)

    def __setitem__(self, name: str, value: str) -> None:
        """Sets the attribute 'name' to 'value' in the database. Example: document['name'] = value"""
        self.__collection__.__collection__.update_one(
            {"_id": self.__id__}, {"$set": {"{}.{}".format(self.__field__, name): encoder.BSONEncoder.default(value)}})
        self.__storage__.__setitem__(name, value)

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """Sets the attribute 'name' to 'value' in the database. Example: document.name = value"""
        self.__setitem__(name, value)

    def __delitem__(self, name: str) -> None:
        """Deletes the attribute 'name' from the database. Example: del document['name']"""
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$unset": {"{}.{}".format(self.__field__, name): True}})
        self.__storage__.__delitem__(name)

    def __delattr__(self, name: str) -> None:
        """Deletes the attribute 'name' from the database. Example: del document.name"""
        self.__delitem__(name)

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__, self.__storage__)

    def __contains__(self, obj: typing.Any) -> bool:
        """If 'obj' is in the current object. Example: if 'obj' in document: ..."""
        return obj in self.__storage__

    def delete(self) -> None:
        """
        Deletes the current object from the database

        Example
        --------
        >>> document.name.delete()
        #    Initial Document
        #      {'username': 'something', 'name': {'first': 'John', 'last': 'Doe'}}
        #    Updated Document
        #      {'username': 'something'}
        """
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$unset": {self.__field__: True}})


class SakiDict(SakiObject):
    """
    An object behaving like a Python dict which is linked to the database.
    """
    __storage__: dict
    __overwritten__ = SakiObject.__overwritten__.union({"__fetch_from_db__", "__lazy_fetch__", "clear", "pop", "popitem", "setdefault", "update"})

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
        data = list(self.__collection__.__collection__.aggregate([
            {'$match': {'_id': encoder.BSONEncoder.default(self.__id__)}},
            {'$replaceRoot': {'newRoot': '${}'.format(self.__field__)}},
            {'$unset': [str(attribute) for attribute in self.__lazy__]}
        ]))
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

    def setdefault(self, key: typing.Any, default: Any = None) -> typing.Union[Any, typing.Any]:
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


class SakiList(SakiObject):
    """
    An object behaving like a Python list which is linked to the database.
    """
    __storage__: list
    __overwritten__ = SakiObject.__overwritten__.union(
        {"__fetch_from_db__", "__lazy_fetch__", "append", "clear", "extend", "pop", "remove", "reverse", "sort", "__iadd__", "__imul__", "__setitem__", "__delitem__"})

    def __lazy_fetch__(self, lazy_obj: encoder.LazyObject) -> typing.Any:
        data = list(self.__collection__.__collection__.aggregate([
            {'$match': {'_id': encoder.BSONEncoder.default(self.__id__)}},
            {
                '$replaceRoot': {
                    'newRoot': {
                        '$arrayToObject': {
                            '$map': {
                                'input': {
                                    '$range': [0, {'$size': '${}'.format(self.__field__)}]
                                },
                                'in': {
                                    'k': {'$toString': '$$this'},
                                    'v': {'$arrayElemAt': ['${}'.format(self.__field__), '$$this']}
                                }
                            }
                        }
                    }
                }
            },
            {"$project": {"_id": False, lazy_obj.field: True}}
        ]))
        if len(data) <= 0:
            raise ValueError("The field '{}.{}' does not exist in the document '{}' on collection {}.".format(
                self.__field__, lazy_obj.field, self.__id__, self.__collection__))
        return data[0][lazy_obj.field]

    def __fetch_from_db__(self) -> typing.Union[list, dict]:
        # list() loads everything
        data = list(self.__collection__.__collection__.aggregate([
            {'$match': {'_id': encoder.BSONEncoder.default(self.__id__)}},
            {
                '$replaceRoot': {
                    'newRoot': {
                        '$mergeObjects': [
                            {'__saki_length__': {'$size': '${}'.format(self.__field__)}},
                            {
                                '$arrayToObject': {
                                    '$map': {
                                        'input': {
                                            '$range': [0, {'$size': '${}'.format(self.__field__)}]
                                        },
                                        'in': {
                                            'k': {'$toString': '$$this'},
                                            'v': {'$arrayElemAt': ['${}'.format(self.__field__), '$$this']}
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            },
            {'$unset': [str(attribute) for attribute in self.__lazy__]}
        ]))
        if len(data) <= 0:
            return []
        data = data[0]
        iterating_list = [str(n) for n in range(data["__saki_length__"])]
        annotations = self.__annotations__
        return [
            encoder.TypeEncoder.default(
                data.get(i, encoder.LazyObject(i)),
                _type=annotations.get(i, None),
                field="{}.{}".format(self.__field__, i),
                collection=self.__collection__,
                _id=self.__id__
            )
            for i in iterating_list]

    def append(self, o: typing.Any) -> None:
        """
        Appends the given object to the end of the list.

        Parameters
        ----------
        o : typing.Any
            The object to append to the list.

        Example
        --------
        >>> document.fruits.append('Strawberry')
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': ["Apple", "Orange", "Strawberry"]}
        """
        o = encoder.TypeEncoder.default(o, field="{}.{}".format(self.__field__, len(self.__storage__)),
                                        collection=self.__collection__, _id=self.__id__)
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$push": {self.__field__: encoder.BSONEncoder.default(o)}})
        self.__storage__.append(o)

    def clear(self) -> None:
        """
        Removes all elements from the list.

        Example
        --------
        >>> document.fruits.clear()
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': []}
        """
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: []}})
        self.__storage__.clear()

    def extend(self, iterable: typing.Iterable[typing.Any]) -> None:
        """
        Extends the list by appending all the items in the given iterable.

        Parameters
        ----------
        iterable : typing.Iterable[typing.Any]
            The iterable of objects to append to the list.

        Example
        --------
        >>> document.fruits.extend(['Strawberry', 'Kiwi'])
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': ["Apple", "Orange", "Strawberry", "Kiwi"]}
        """
        length = len(self.__storage__)
        iterable = [encoder.TypeEncoder.default(element, field="{}.{}".format(self.__field__, length + index), collection=self.__collection__, _id=self.__id__)
                    for index, element in enumerate(iterable)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {
            "$push": {self.__field__: {"$each": encoder.BSONEncoder.default(iterable)}}})
        self.__storage__.extend(iterable)

    def pop(self, index: typing.SupportsIndex = ...) -> typing.Any:
        """
        Removes and returns the object at the given index.

        Parameters
        ----------
        index : typing.SupportsIndex
            The index of the object to remove.

        Example
        --------
        >>> document.fruits.pop(1)
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': ["Apple"]}
        """
        copied = self.__storage__.copy()
        value = copied.pop(index)
        bson = encoder.BSONEncoder.default(copied)
        copied = [encoder.TypeEncoder.default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                  for index, element in enumerate(bson)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: bson}})
        self.__storage__ = copied
        return value

    def remove(self, value: typing.Any) -> None:
        """
        Removes the first occurrence of the given value from the list.

        Parameters
        ----------
        value : typing.Any
            The object to remove from the list.

        Example
        --------
        >>> document.fruits.remove('Orange')
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': ["Apple"]}
        """
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$pull": {self.__field__: encoder.BSONEncoder.default(value)}})
        try:
            self.__storage__.remove(value)
            bson = encoder.BSONEncoder.default(self.__storage__)
            copied = [encoder.TypeEncoder.default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                      for index, element in enumerate(bson)]
            self.__storage__ = copied
        except ValueError:  # they are not raised by MongoDB
            pass

    def reverse(self) -> None:
        """
        Reverses the order of the list.

        Example
        --------
        >>> document.fruits.reverse()
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': ["Orange", "Apple"]}
        """
        copied = self.__storage__.copy()
        copied.reverse()
        bson = encoder.BSONEncoder.default(copied)
        copied = [encoder.TypeEncoder.default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                  for index, element in enumerate(bson)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: bson}})
        self.__storage__ = copied

    def sort(self, key: typing.Callable[[typing.Any], typing.Any] = None, reverse: bool = False) -> None:
        """
        Sorts the list in place.

        Parameters
        ----------
        key : typing.Callable[[typing.Any], typing.Any]
            The key function to sort by.
        reverse : bool
            Whether to reverse the list. (switching for example from ascending to descending order)

        Example
        --------
        ### Basic Example
        >>> document.fruits.sort()
        #    Initial Document
        #      {'numbers': [1, 4, 3, 2]}
        #    Updated Document
        #      {'numbers': [1, 2, 3, 4]}
        ### Nested Documents
        >>> document.profiles.sort(key=lambda profile: profile.get("rank"))
        #    Initial Document
        #      {'profiles': [{"name": "John", "rank": 2}, {"name": "Doe", "rank": 1}]}
        #    Updated Document
        #      {'profiles': [{"name": "Doe", "rank": 1}, {"name": "John", "rank": 2}]}
        ### Using Reverse
        >>> document.fruits.sort(reverse=True)
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': ["Orange", "Apple"]}
        """
        copied = self.__storage__.copy()
        copied.sort(key=key, reverse=reverse)
        bson = encoder.BSONEncoder.default(copied)
        copied = [encoder.TypeEncoder.default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                  for index, element in enumerate(bson)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: bson}})
        self.__storage__ = copied

    def __iadd__(self, x: list[typing.Any]) -> list[typing.Any]:
        """Extends the list by appending all the items in the given list. Example: ``document.fruits += ['Apple', 'Orange']``"""
        self.extend(x)
        return self

    def __imul__(self, x: int) -> list[typing.Any]:
        """Multiplies the list by the given number. Example: ``document.fruits *= 2``"""
        copied = self.__storage__ * x
        bson = encoder.BSONEncoder.default(copied)
        copied = [encoder.TypeEncoder.default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                  for index, element in enumerate(bson)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: bson}})
        self.__storage__ = copied
        return self

    def __setitem__(self, key: typing.Union[int, slice], value: typing.Any) -> None:
        """Sets the item at index key to the given value. Example: document[1] = value"""
        if isinstance(key, slice):
            copied = self.__storage__.__setitem__(key, value)
            bson = encoder.BSONEncoder.default(copied)
            copied = [encoder.TypeEncoder.default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                      for index, element in enumerate(bson)]
            self.__collection__.__collection__.update_one({"_id": self.__id__}, {
                "$set": {self.__field__: bson}})
            self.__storage__ = copied
        else:
            try:
                key = int(key)
                self.__collection__.__collection__.update_one({"_id": self.__id__}, {
                    "$set": {"{}.{}".format(self.__field__, key): encoder.BSONEncoder.default(value)}})
                self.__storage__.__setitem__(key, value)
                bson = encoder.BSONEncoder.default(self.__storage__)
                self.__storage__ = [encoder.TypeEncoder.default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                                    for index, element in enumerate(bson)]
            except ValueError as err:
                raise TypeError("list indices must be integers or slices, not str") from err

    def __delitem__(self, key: typing.Union[int, slice]) -> None:
        """Deletes the item at index key. Example: del document[1]"""
        self.pop(key)
