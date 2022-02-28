import secrets

import yuno
from Crypto.Cipher import AES as __aes__

from io import BytesIO

from . import init


@init.use_client
def test_encrypt(client):
    init.log("security ~ Testing encrypt")
    aes = yuno.security.encrypt.AES()
    assert aes.decrypt(aes.encrypt("test")) == "test"
    aes = yuno.security.encrypt.AES(key=client)
    assert aes.decrypt(aes.encrypt("test")) == "test"
    diff_prefix = yuno.security.encrypt.AES(prefix="diff")
    assert aes.decrypt(diff_prefix.encrypt("test"), ignore_prefix=True) == "test"
    try:
        aes.decrypt("not a valid token")
    except ValueError:
        pass
    yuno.security.encrypt.AES(key=secrets.token_bytes(16))
    for length in (16, 24, 32):
        yuno.security.encrypt.AES(key_length=length)


def test_sha():
    init.log("security ~ Testing SHA-256")
    hasher = yuno.security.hash.Hasher()
    assert hasher.hash("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    assert hasher.hash_string("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    assert hasher.hash_bytes(b"test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    new_io = BytesIO()
    new_io.write(b"test")
    new_io.seek(2)
    assert hasher.hash_buffer(new_io) == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    assert new_io.tell() == 2
    assert hasher.hash_buffer(new_io, start=2, end=4) == "56af4bde70a47ae7d0f1ebb30e45ed336165d5c9ec00ba9a92311e33a4256d74"
    assert new_io.tell() == 2


@init.use_client
def test_argon(client):
    init.log("security ~ Testing Argon2id")
    hasher = yuno.security.hash.PasswordHasher()
    hashed = hasher.hash("test")
    assert hasher.verify("test", hashed) == hashed
    assert hasher.is_equal("test", hashed)
    assert not hasher.is_equal("test", hasher.hash("test2"))
    assert hasher.is_equal("test", hasher.hash("test", "my salt"), salt="my salt")
    assert not hasher.is_equal("test", hasher.hash("test", "my salt"), salt="my salt2")
    hasher = yuno.security.hash.PasswordHasher(pepper=client)
    hashed = hasher.hash("test")


@init.use_client
def test_token(client):
    init.log("security ~ Testing token manager")
    token_manager = yuno.security.token.TokenManager()
    token = token_manager.generate(user="id-123", username="username-123", roles=["admin", "user"],
                                   main=True, extra={"hello": "world"}, float_test=1.5, int_test=2, hey={"hello": "world"})
    assert token_manager.decode(token) == {
        "user": "id-123",
        "username": "username-123",
        "roles": ["admin", "user"],
        "main": True,
        "float_test": 1.5,
        "int_test": 2,
        "hello": "world",
        "hey": {"hello": "world"}
    }
    token_manager = yuno.security.token.TokenManager(key=client)
    token_manager.decode(token_manager.generate())
    aes = yuno.security.encrypt.AES()
    token_manager.decode(token_manager.generate(encryption=aes), encryption=aes)

    token_manager = yuno.security.token.TokenManager(key=client, sign="signature")
    token_manager.decode(token_manager.generate())
    token_manager.decode(token_manager.generate(encryption=aes), encryption=aes)

    token_manager = yuno.security.token.TokenManager(key=client, sign=client)
    token_manager.decode(token_manager.generate())
    token_manager.decode(token_manager.generate(encryption=aes), encryption=aes)
