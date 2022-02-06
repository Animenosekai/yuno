import typing

import pymongo.cursor

from saki import collection
from saki.direction import SortDirectionType, SortDirection


class Cursor():
    def __init__(self, cursor: pymongo.cursor.Cursor, verification: typing.Callable = None) -> None:
        self.cursor = cursor
        self.id = self.cursor.cursor_id
        self.verification = verification if verification is not None else lambda x: x

    def __next__(self):
        return self.next()

    def next(self):
        return self.verification(self.cursor.next())

    def try_next(self):
        """
        Try to get the next object without raising an exception.
        """
        try:
            return self.cursor.next()
        except StopIteration:
            return None

    def __iter__(self) -> typing.Iterator:
        """
        Returns the iterator.
        """
        return self

    def __repr__(self) -> str:
        return "Cursor({})".format(self.id)

    @property
    def collection(self) -> "collection.SakiCollection":
        _collection = self.cursor.collection
        return collection.SakiCollection(_collection.database, _collection.name)

    def close(self) -> None:
        self.cursor.close()

    @property
    def disk_use(self) -> bool:
        return self.cursor.__allow_disk_use

    @disk_use.setter
    def disk_use(self, allow: bool) -> bool:
        return self.cursor.allow_disk_use(allow)

    def explain(self) -> typing.Any:
        return self.cursor.explain()

    def hint(self, index: str):
        self.cursor.hint(index)
        return self

    def limit(self, limit: int):
        self.cursor.limit(limit)
        return self

    def skip(self, number: int):
        self.cursor.skip(number)
        return self

    def sort(self, field: typing.Union[str, list[tuple[str, SortDirectionType]]], direction: SortDirectionType = SortDirection.ASCENDING):
        if not isinstance(field, str) and isinstance(field, typing.Iterable):
            for index, element in enumerate(field):
                if isinstance(element, str) or not isinstance(element, typing.Iterable):
                    field[index] = (str(element), direction)
            direction = None
        self.cursor.sort(field, direction)
        return self

    def where(self, code: str):
        self.cursor.where(code)
        return self

    @property
    def alive(self):
        """Does this cursor have the potential to return more data?"""
        return self._cursor.alive

    def __enter__(self):
        """
        Enter the context manager.

        Example
        -------
        >>> with db.watch() as stream: # <-- this line calls __enter__
        ...     for event in stream:
        ...         print(event)
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager.

        Example
        -------
        >>> with db.watch() as stream:
        ...     for event in stream:
        ...         print(event)
        ... # <-- this line calls __exit__
        """
        self.close()
