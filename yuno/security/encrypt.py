"""
encrypt.py

Manages AES encryption and decryption.
"""
import secrets
import typing

import yuno
from Crypto.Cipher import AES as __aes__
from yuno.utils.annotations import Default

VERSION_HEX = yuno.__version_string__().encode("utf-8").hex()
RANDOMIZING_TYPES = (Default, yuno.YunoClient, yuno.YunoDatabase, yuno.YunoCollection)


class AES():
    """
    The AES Encryption Manager for yuno
    """
    PREFIX_SEPARATOR = "+"
    SEPARATOR = ","

    def __init__(self, key: typing.Union[str, bytes, yuno.YunoClient, yuno.YunoDatabase, yuno.YunoCollection] = Default("RANDOM"), key_length: typing.Literal[16, 24, 32] = 32, prefix: str = "yuno") -> None:
        """
        The AES Encryption Manager for yuno

        Parameters
        ----------
        key: str | bytes | YunoClient | YunoDatabase | YunoCollection
            The key to use for the encryption.
            If the key is a YunoClient, YunoDatabase or YunoCollection, the key will be generated randomly and stored in the database.
            By default, a random key will be generated but the generated encryption will not be reusable (test purposes).
        prefix: str
            The prefix to recognize the generated token.
        """
        if isinstance(key, RANDOMIZING_TYPES):
            self.key = secrets.token_bytes(key_length)
            if not isinstance(key, Default):
                collection = yuno.utils.security.get_security_collection(key)
                try:
                    self.key = collection["__aes_key__"]["value"]
                except Exception:
                    collection["__aes_key__"] = {
                        "_id": "__aes_key__",
                        "value": self.key
                    }
        else:
            self.key = yuno.utils.security.check_key_type(key)
        self.cipher = __aes__.new(self.key, __aes__.MODE_GCM)
        self.prefix = str(prefix) + str(self.PREFIX_SEPARATOR)

    def encrypt(self, element: typing.Union[str, bytes], encoding: str = "utf-8"):
        """
        Encrypts the given element

        Parameters
        ----------
        element: str | bytes
            The element to encrypt
        encoding: str
            The encoding to use for the element

        Returns
        -------
        str
            The encrypted element
        """
        self.cipher = __aes__.new(self.key, __aes__.MODE_GCM)
        if not isinstance(element, bytes):
            element = str(element).encode(encoding)
        encrypted, tag = self.cipher.encrypt_and_digest(element)
        return "{prefix}{version}{sep}{nonce}{sep}{element}{sep}{tag}".format(
            prefix=self.prefix,
            version=VERSION_HEX,
            sep=self.SEPARATOR,
            nonce=self.cipher.nonce.hex(),
            element=encrypted.hex(),
            tag=tag.hex()
        )

    def decrypt(self, encrypted: str, decode: str = "utf-8", ignore_prefix: bool = False):
        """
        Decrypts the given encrypted element

        Parameters
        ----------
        encrypted: str
            The encrypted element to decrypt
        decode: str
            The encoding to use for the decoded element (None if no decoding is needed)
        ignore_prefix: bool
            To ignore the prefix checking.
            If ignored, the prefix checking will be replaced by a splitting on the PREFIX_SEPARATOR.

        Returns
        -------
        str | bytes
            The decrypted element
        """
        encrypted = str(encrypted)
        if ignore_prefix:
            splitting = encrypted.split(self.PREFIX_SEPARATOR)
            if len(splitting) > 1:
                encrypted = self.PREFIX_SEPARATOR.join(splitting[1:])
        else:
            if not encrypted.startswith(self.prefix):
                raise ValueError("The given encrypted string does not start with the right prefix ({})".format(self.prefix))
            encrypted = encrypted[len(self.prefix):]
        try:
            version, nonce, content, tag = [bytes.fromhex(element) for element in encrypted.split(self.SEPARATOR)]
        except Exception as err:
            raise ValueError("The given encrypted element is not valid") from err
        print("aes", version, nonce, content, tag)
        self.cipher = __aes__.new(self.key, __aes__.MODE_GCM, nonce=nonce)
        decrypted = self.cipher.decrypt_and_verify(content, received_mac_tag=tag)
        if decode is not None:
            return decrypted.decode(str(decode))
        return decrypted
