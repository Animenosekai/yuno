import typing
from yuno import encoder
from yuno.object import YunoObject


class YunoList(YunoObject, list):
    """
    An object behaving like a Python list which is linked to the database.
    """
    __storage__: list
    __overwritten__ = YunoObject.__overwritten__.union({"__fetch_from_db__", "__lazy_fetch__", "__post_verification__",
                                                       "append", "clear", "extend", "pop", "remove", "reverse", "sort", "__iadd__", "__imul__", "__setitem__", "__delitem__"})

    def __post_verification__(self) -> None:
        return

    def __lazy_fetch__(self, lazy_obj: encoder.LazyObject) -> typing.Any:
        data = list(self.__collection__.__collection__.aggregate([
            {'$match': {'_id': encoder.YunoBSONEncoder().default(self.__id__)}},
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
        pipeline = [
            {'$match': {'_id': encoder.YunoBSONEncoder().default(self.__id__)}},
            {
                '$replaceRoot': {
                    'newRoot': {
                        '$mergeObjects': [
                            {'__yuno_length__': {'$size': '${}'.format(self.__field__)}},
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
            }
        ]
        if len(self.__lazy__) > 0:
            pipeline.append({'$unset': [str(attribute) for attribute in self.__lazy__]})
        data = list(self.__collection__.__collection__.aggregate(pipeline))
        if len(data) <= 0:
            return []
        data = data[0]
        iterating_list = [str(n) for n in range(data["__yuno_length__"])]
        annotations = self.__annotations__
        return [
            encoder.YunoTypeEncoder().default(
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
        o = encoder.YunoTypeEncoder().default(o, field="{}.{}".format(self.__field__, len(self.__storage__)),
                                              collection=self.__collection__, _id=self.__id__)
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$push": {self.__field__: encoder.YunoBSONEncoder().default(o)}})
        self.__storage__.append(o)

    def insert(self, index: int, o: typing.Any) -> None:
        """
        Inserts the object before the specified index.

        Parameters
        ----------
        index : int
            The index to insert the object before.
        o : typing.Any
            The object to insert.

        Example
        --------
        >>> document.fruits.insert(1, 'Strawberry')
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': ["Apple", "Strawberry", "Orange"]}
        """
        copied = self.__storage__.copy()
        copied.insert(index, o)
        bson = encoder.YunoBSONEncoder().default(copied)
        copied = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, i),
                                                    collection=self.__collection__, _id=self.__id__) for i, element in enumerate(bson)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: bson}})
        self.__storage__ = copied

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
        iterable = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, length + index), collection=self.__collection__, _id=self.__id__)
                    for index, element in enumerate(iterable)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {
            "$push": {self.__field__: {"$each": encoder.YunoBSONEncoder().default(iterable)}}})
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
        bson = encoder.YunoBSONEncoder().default(copied)
        copied = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                  for index, element in enumerate(bson)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: bson}})
        self.__storage__ = copied
        return value

    def remove(self, value: typing.Any) -> None:
        """
        Removes the first occurrence of the given value from the list.

        Parameters
        ----------
        value : Any
            The object to remove from the list.

        Example
        --------
        >>> document.fruits.remove('Orange')
        #    Initial Document
        #      {'fruits': ["Apple", "Orange"]}
        #    Updated Document
        #      {'fruits': ["Apple"]}
        """
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$pull": {self.__field__: encoder.YunoBSONEncoder().default(value)}})
        try:
            self.__storage__.remove(value)
            bson = encoder.YunoBSONEncoder().default(self.__storage__)
            copied = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
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
        bson = encoder.YunoBSONEncoder().default(copied)
        copied = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
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
        bson = encoder.YunoBSONEncoder().default(copied)
        copied = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                  for index, element in enumerate(bson)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: bson}})
        self.__storage__ = copied

    def __iadd__(self, x: typing.List[typing.Any]) -> typing.List[typing.Any]:
        """Extends the list by appending all the items in the given list. Example: ``document.fruits += ['Apple', 'Orange']``"""
        self.extend(x)
        return self

    def __imul__(self, x: int) -> typing.List[typing.Any]:
        """Multiplies the list by the given number. Example: ``document.fruits *= 2``"""
        copied = self.__storage__ * x
        bson = encoder.YunoBSONEncoder().default(copied)
        copied = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                  for index, element in enumerate(bson)]
        self.__collection__.__collection__.update_one({"_id": self.__id__}, {"$set": {self.__field__: bson}})
        self.__storage__ = copied
        return self

    def __setitem__(self, key: typing.Union[int, slice], value: typing.Any) -> None:
        """Sets the item at index key to the given value. Example: document[1] = value"""
        if isinstance(key, slice):
            copied = self.__storage__.__setitem__(key, value)
            bson = encoder.YunoBSONEncoder().default(copied)
            copied = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                      for index, element in enumerate(bson)]
            self.__collection__.__collection__.update_one({"_id": self.__id__}, {
                "$set": {self.__field__: bson}})
            self.__storage__ = copied
        else:
            try:
                key = int(key)
                self.__collection__.__collection__.update_one({"_id": self.__id__}, {
                    "$set": {"{}.{}".format(self.__field__, key): encoder.YunoBSONEncoder().default(value)}})
                self.__storage__.__setitem__(key, value)
                bson = encoder.YunoBSONEncoder().default(self.__storage__)
                self.__storage__ = [encoder.YunoTypeEncoder().default(element, field="{}.{}".format(self.__field__, index), collection=self.__collection__, _id=self.__id__)
                                    for index, element in enumerate(bson)]
            except ValueError as err:
                raise TypeError("list indices must be integers or slices, not str") from err

    def __delitem__(self, key: typing.Union[int, slice]) -> None:
        """Deletes the item at index key. Example: del document[1]"""
        self.pop(key)
