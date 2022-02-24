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
    data = mongo.to_dict()
    data.pop("db_path", None)
    data["log_config"].pop("path", None)
    assert data == {'host': '127.0.0.1', 'port': 27017, 'fork': True, 'log_config': {'verbosity': 1, 'append': True,
                                                                                     'timezone': 'iso8601-utc', 'debug': False}, 'max_connections': 65536, 'json_validation': True, 'ipv6': True, 'monitoring': True}
    data = mongo.to_dict(camelCase=True)
    data.pop("dbPath", None)
    data["logConfig"].pop("path", None)
    assert data == {'host': '127.0.0.1', 'port': 27017, 'fork': True, 'logConfig': {'verbosity': 1, 'append': True,
                                                                                    'timezone': 'iso8601-utc', 'debug': False}, 'maxConnections': 65536, 'jsonValidation': True, 'ipv6': True, 'monitoring': True}

    mongo.dump("test.conf")
    mongo.dump(pathlib.Path("./test.conf"))
    with open("test.conf", "w") as f:
        mongo.dump(f)

    mongo.load("test.conf")

    mongo.loads(mongo.dumps())
