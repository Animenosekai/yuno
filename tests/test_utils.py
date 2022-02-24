import yuno

from . import init


def test_annotations():
    init.log("utils ~ Testing annotations")
    assert yuno.utils.annotations.Default(1) != 1
    assert yuno.utils.annotations.Default(1).value == 1
    assert yuno.utils.annotations.Default().value is None
    assert yuno.utils.annotations.Default().__repr__() == "Default(None)"


def test_logging():
    init.log("utils ~ Testing logging")

    def test():
        return yuno.utils.logging.caller_name() == "tests.test_utils.test_logging"
    assert test()

    colors = yuno.utils.logging.Colors()
    for color, code in [
        ('normal', '\033[0m'),
        ('grey', '\033[90m'),
        ('red', '\033[91m'),
        ('green', '\033[92m'),
        ('blue', '\033[94m'),
        ('cyan', '\033[96m'),
        ('white', '\033[97m'),
        ('yellow', '\033[93m'),
        ('magenta', '\033[95m')
    ]:
        assert colors[color] == code

    assert yuno.utils.logging.LogLevels.DEBUG.debug
    assert not yuno.utils.logging.LogLevels.INFO.debug
    assert not yuno.utils.logging.LogLevels.WARNING.debug
    assert not yuno.utils.logging.LogLevels.ERROR.debug


def test_string():
    init.log("utils ~ Testing string")
    assert yuno.utils.string.toCamelCase("hello_world") == "helloWorld"
    assert yuno.utils.string.toCamelCase("how are you") == "howAreYou"
    assert yuno.utils.string.toCamelCase("how_are_you") == "howAreYou"
    assert yuno.utils.string.toCamelCase("howAreYou") == "howAreYou"
    assert yuno.utils.string.toCamelCase("howareyou") == "howareyou"


def test_unpack():
    init.log("utils ~ Testing unpack")
    assert yuno.utils.unpack.is_unpackable({"hello": "world"})
    assert not yuno.utils.unpack.is_unpackable([1, 2, 3])
