import pathlib

import yuno

from . import init


def test_attributes():
    init.log("launcher ~ Testing attributes")
    mongo = yuno.MongoDB()
    assert mongo.host == "127.0.0.1"
    assert mongo.port == 27017
    assert isinstance(mongo.db_path, pathlib.Path)
    assert mongo.fork == True
    assert isinstance(mongo.log_config, yuno.LogConfig)
    assert mongo.log_config.verbosity == 1
    assert isinstance(mongo.log_config.path, pathlib.Path)
    assert mongo.log_config.append == True
    assert mongo.log_config.timezone == yuno.launcher.Timezone.UTC
    assert mongo.log_config.debug == False
    assert mongo.max_connections == 65536
    assert mongo.json_validation == True
    assert mongo.ipv6 == True
    assert mongo.monitoring == True
    assert mongo.__process__ is None


def test_methods():
    init.log("launcher ~ Testing methods")
    mongo = yuno.MongoDB()

    DEFAULT = ['--bind_ip', '127.0.0.1', '--port', '27017', '--maxConns', '65536', '--enableFreeMonitoring',
               'on', '--fork', '--ipv6', '-v', '--timeStampFormat', 'iso8601-utc', '--logappend']

    args = mongo.to_cli_args()
    for arg in DEFAULT:
        assert arg in args

    assert isinstance(mongo.dumps(), str)
    assert mongo.to_dict() == {'host': '127.0.0.1', 'port': 27017, 'db_path': '/Users/animenosekai/Documents/Coding/Projects/yuno/yuno/data', 'fork': True, 'log_config': {'verbosity': 1,
                                                                                                                                                                           'path': '/Users/animenosekai/Documents/Coding/Projects/yuno/yuno/db.yuno.log', 'append': True, 'timezone': 'iso8601-utc', 'debug': False}, 'max_connections': 65536, 'json_validation': True, 'ipv6': True, 'monitoring': True}
    assert mongo.to_dict(camelCase=True) == {'host': '127.0.0.1', 'port': 27017, 'dbPath': '/Users/animenosekai/Documents/Coding/Projects/yuno/yuno/data', 'fork': True, 'logConfig': {
        'verbosity': 1, 'path': '/Users/animenosekai/Documents/Coding/Projects/yuno/yuno/db.yuno.log', 'append': True, 'timezone': 'iso8601-utc', 'debug': False}, 'maxConnections': 65536, 'jsonValidation': True, 'ipv6': True, 'monitoring': True}

    mongo.dump("test.conf")
    mongo.dump(pathlib.Path("./test.conf"))
    with open("test.conf", "w") as f:
        mongo.dump(f)

    mongo.load("test.conf")

    mongo.loads(mongo.dumps())
