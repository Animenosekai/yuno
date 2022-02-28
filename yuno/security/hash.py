"""
hash.py

A set of functions to hash data and passwords.
"""
import hashlib
import secrets
import typing

import argon2
import yuno
from yuno.utils.annotations import Default

RANDOMIZING_TYPES = (Default, yuno.YunoClient, yuno.YunoDatabase, yuno.YunoCollection)

class Hasher():
    """
    A set of tools to hash data with SHA-256.
    """

    def hash(self, content: typing.Union[str, bytes, typing.IO]):
        """
        Hash the given content.

        Parameters
        ----------
        content: str | bytes | typing.IO
            The content to hash
        """
        if isinstance(content, bytes):
            return self.hash_bytes(content)
        elif hasattr(content, "read"):
            return self.hash_buffer(content)
        return self.hash_string(str(content))

    def hash_bytes(self, content: bytes):
        """
        Hash the given bytes.

        Parameters
        ----------
        content: bytes
            The content to hash

        Returns
        -------
        str
            The hashed bytes as hexadecimal
        """
        return hashlib.sha256(content).hexdigest()

    def hash_string(self, content: str, encoding: str = "utf-8"):
        """
        Hash the given string.

        Parameters
        ----------
        content: str
            The content to hash
        encoding: str
            The encoding to use for the string

        Returns
        -------
        str
            The hashed string as hexadecimal
        """
        return self.hash_bytes(content.encode(encoding))

    def hash_buffer(self, content: typing.IO, start: int = 0, end: int = None):
        """
        Hash the given buffer and replaces the cursor at the current position.

        Parameters
        ----------
        content: typing.IO
            The content to hash
        start: int
            The start position of the buffer
        end: int
            The end position of the buffer

        Returns
        -------
        str
            The hashed buffer as hexadecimal
        """
        pos = content.tell()
        if start is not None:
            content.seek(start)
        if end is None:
            data = content.read()
        else:
            data = content.read(end)
        content.seek(pos)
        return self.hash_bytes(data)


class PasswordHasher():
    """
    A password hasher that uses Argon2id to securely hash passwords.
    """

    def __init__(self, pepper: typing.Union[str, bytes, yuno.YunoClient, yuno.YunoDatabase, yuno.YunoCollection] = Default("RANDOM")) -> None:
        """
        Initialize the password hasher.

        Parameters
        ----------
        pepper: str | bytes | yuno.YunoClient | yuno.YunoDatabase | yuno.YunoCollection
            The pepper to use for the hasher
            If the pepper is a YunoClient, YunoDatabase or YunoCollection, the pepper will be generated randomly and stored in the database.
            By default, a random pepper will be generated but the generated encryption will not be reusable (test purposes).
        """
        if isinstance(pepper, RANDOMIZING_TYPES):
            self.pepper = secrets.token_hex(16)
            if not isinstance(pepper, Default):
                collection = yuno.utils.security.get_security_collection(pepper)
                try:
                    self.pepper = collection["__password_pepper__"]["value"]
                except Exception:
                    collection["__password_pepper__"] = {
                        "_id": "__password_pepper__",
                        "value": self.pepper
                    }
        else:
            self.pepper = yuno.utils.security.check_key_type(pepper)
        self.hasher = argon2.PasswordHasher()

    def hash(self, password: str, salt: str = None):
        """
        Hash the given password.

        Parameters
        ----------
        password: str
            The password to hash
        salt: str
            The salt to use for the hash
        """
        if salt is not None:
            password = "{password}{salt}".format(password=password, salt=salt)
        return self.hasher.hash("{pepper}{password}".format(pepper=self.pepper, password=password))

    def verify(self, hashed: str, password: str, salt: str = None):
        """
        Verify the given password.

        Parameters
        ----------
        hashed: str
            The hashed password
        password: str
            The password to verify
        salt: str
            The salt to use for the hash
        """
        if salt is not None:
            password = "{password}{salt}".format(password=password, salt=salt)
        password = "{pepper}{password}".format(pepper=self.pepper, password=password)
        self.hasher.verify(hashed, password)
        if self.hasher.check_needs_rehash(hashed):
            return self.hasher.hash(password)
        return hashed

    def is_equal(self, hashed: str, password: str, salt: str = None):
        """
        Check if the given password is equal to the hashed password.

        Compared to verify(), this function will not raise an exception if the password is not equal.

        Also, this will not make any verification (rehashing for example).

        Parameters
        ----------
        hashed: str
            The hashed password
        password: str
            The password to verify
        salt: str
            The salt to use for the hash
        """
        if salt is not None:
            password = "{password}{salt}".format(password=password, salt=salt)
        password = "{pepper}{password}".format(pepper=self.pepper, password=password)
        try:
            return self.hasher.verify(hashed, password)
        except argon2.exceptions.VerifyMismatchError:
            return False
