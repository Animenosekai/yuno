import typing

import pymongo.cursor

from yuno import collection
from yuno.direction import SortDirectionType, SortDirection


class Cursor():
    """
    A cursor is a lazy iterator.

    Example
    -------
    >>> for document in collection.find(defered=True):
    ...     print(document) # documents are loaded as they are used
    """

    def __init__(self, cursor: pymongo.cursor.Cursor, verification: typing.Callable = None) -> None:
        """
        Initialize the cursor.

        Parameters
        ----------
        cursor : pymongo.cursor.Cursor
            The cursor to wrap.
        verification : typing.Callable
            A function to verify each object.
        """
        self.cursor = cursor
        self.id = self.cursor.cursor_id
        self.verification = verification if verification is not None else lambda x: x

    def __next__(self):
        """Returns the next object."""
        return self.next()

    def next(self):
        """Returns the next object."""
        return self.verification(self.cursor.next())

    def try_next(self):
        """
        Try to get the next object without raising an exception.
        """
        try:
            return self.cursor.next()  # should change it to have the same behavior as Watch's __next__
        except StopIteration:
            return None

    def __iter__(self) -> typing.Iterator:
        """
        Returns the iterator.
        """
        return self

    def __repr__(self) -> str:
        """String representation of the cursor."""
        return "{}(id={})".format(self.__class__.__name__, self.id)

    @property
    def collection(self) -> "collection.YunoCollection":
        """Collection the cursor is iterating over."""
        _collection = self.cursor.collection
        return collection.YunoCollection(_collection.database, _collection.name)

    def close(self) -> None:
        """Closes the cursor."""
        self.cursor.close()

    @property
    def disk_use(self) -> bool:
        """Wether are not to allow disk use"""
        return self.cursor.__allow_disk_use

    @disk_use.setter
    def disk_use(self, allow: bool) -> bool:
        """
        Wether are not to allow disk use

        Parameters
        ----------
        allow : bool
            Wether are not to allow disk use
        """
        return self.cursor.allow_disk_use(allow)

    def explain(self) -> typing.Any:
        """Explain the query plan."""
        return self.cursor.explain()

    def hint(self, index: str):
        """Hint the query to use the given index and returns the cursor object to use chaining."""
        self.cursor.hint(index)
        return self

    def limit(self, limit: int):
        """Limit the number of objects to return and returns the cursor object to use chaining."""
        self.cursor.limit(limit)
        return self

    def skip(self, number: int):
        """Skip the first `number` objects and returns the cursor object to use chaining."""
        self.cursor.skip(number)
        return self

    def sort(self, field: typing.Union[str, typing.List[typing.Tuple[str, SortDirectionType]]], direction: SortDirectionType = SortDirection.ASCENDING):
        """
        Sort the objects by the given field.

        Parameters
        ----------
        field : str or list[tuple[str, SortDirectionType]]
            The field to sort by.
            If this is a list, each tuple is a field and the direction to sort by.
        direction : SortDirectionType
            The direction to sort by.

        Returns
        -------
        Cursor
            The current object to use chaining.
        """
        if not isinstance(field, str) and isinstance(field, typing.Iterable):
            for index, element in enumerate(field):
                if isinstance(element, str) or not isinstance(element, typing.Iterable):
                    field[index] = (str(element), direction)
            direction = None
        self.cursor.sort(field, direction)
        return self

    def where(self, code: str):
        """
        Add a where clause to the query.

        Parameters
        ----------
        code : str
            The code to add.

        Returns
        -------
        Cursor
            The current object to use chaining.
        """
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
