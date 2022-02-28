"""
token.py

Manages JWT tokens.
"""

import secrets
import typing
import datetime

import jwt
import yuno
from yuno.security.hash import Hasher
from yuno.security.encrypt import AES

from yuno.utils.annotations import Default

HASHER = Hasher()
YUNO_OBJECTS = (yuno.YunoClient, yuno.YunoDatabase, yuno.YunoCollection)
RANDOMIZING_TYPES = (Default, *YUNO_OBJECTS)


class TokenManager():
    """
    Easily create and decode JWT tokens
    """

    def __init__(self, key: typing.Union[str, bytes, yuno.YunoClient, yuno.YunoDatabase, yuno.YunoCollection] = Default("RANDOM"), sign: typing.Union[str, bytes, yuno.YunoClient, yuno.YunoDatabase, yuno.YunoCollection] = None) -> None:
        """
        Initialize the token manager

        Parameters
        ----------
        key: str | bytes | yuno.YunoClient | yuno.YunoDatabase | yuno.YunoCollection
            The key to use for the token
            If the key is a YunoClient, YunoDatabase or YunoCollection, the key will be generated randomly and stored in the database.
            By default, a random key will be generated but the generated encryption will not be reusable (test purposes).
        sign: str | bytes | yuno.YunoClient | yuno.YunoDatabase | yuno.YunoCollection
            The sign to use for the token
            If the sign is a YunoClient, YunoDatabase or YunoCollection, the sign will be generated randomly and stored in the database.
            By default no extra signing will be added to the token.
        """
        if isinstance(key, RANDOMIZING_TYPES) or isinstance(sign, RANDOMIZING_TYPES):
            if isinstance(key, YUNO_OBJECTS):
                self.key = secrets.token_bytes(32)
                collection = yuno.utils.security.get_security_collection(key)
                try:
                    self.key = collection["__jwt_key__"]["value"]
                except Exception:
                    collection["__jwt_key__"] = {
                        "_id": "__jwt_key__",
                        "value": self.key
                    }
            if isinstance(sign, YUNO_OBJECTS):
                self.sign = secrets.token_bytes(32)
                collection = yuno.utils.security.get_security_collection(sign)
                try:
                    self.sign = collection["__jwt_sign__"]["value"]
                except Exception:
                    collection["__jwt_sign__"] = {
                        "_id": "__jwt_sign__",
                        "value": self.sign
                    }
            self.key = yuno.utils.security.check_key_type(key)
            if sign is not None:
                self.sign = yuno.utils.security.check_key_type(sign)
            else:
                self.sign = None
        else:
            self.key = yuno.utils.security.check_key_type(key)
            if sign is not None:
                self.sign = yuno.utils.security.check_key_type(sign)
            else:
                self.sign = None

    def generate(self, user: str = None, expire: datetime.timedelta = datetime.timedelta(days=1), encryption: AES = None, data: dict = None, **kwargs) -> str:
        """
        Generate a JWT token for the given user.

        Parameters
        ----------
        user: str, default = None
            The user to generate the token for
            If None, no user will be added to the token
        expire: datetime.timedelta, default=1 day
            The time after which the token will expire
        encryption: yuno.security.encrypt.AES, default=None
            The encryption to use for the token
            If None, the token will not be encrypted
        data: dict, default=None
            The data to add to the token
            If None, no data will be added to the token
        **kwargs:
            Additional data to add to the token
        """
        result = {
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + expire
        }
        if user is not None:
            result["user"] = user
        if self.sign:
            rand = secrets.token_bytes(8)
            result["rand"] = rand.hex()
            result["sign"] = HASHER.hash_bytes(rand + self.sign)
        result.update(data or {})
        result.update(kwargs)
        token = jwt.encode(result, self.key, algorithm="HS256", headers={"alg": "HS256", "typ": "JWT"})
        if encryption is None:
            return token
        return encryption.encrypt(token)

    def decode(self, token: str, encryption: AES = None) -> dict:
        """
        Decode a JWT token.

        Parameters
        ----------
        token: str
            The token to decode
        encryption: yuno.security.encrypt.AES, default=None
            The encryption to use for the token
            If None, the token will not be decrypted

        Returns
        -------
        dict
            The decoded token
        """
        if encryption is not None:
            data = encryption.decrypt(token)
        else:
            data = token
        data = jwt.decode(data, self.key, algorithms=["HS256"], options={"require": ["iat", "exp"]})
        if self.sign is not None:
            rand = data["rand"]
            sign = data["sign"]
            if HASHER.hash_bytes(bytes.fromhex(rand) + self.sign) != sign:
                raise ValueError("Invalid token signature")
        return data
