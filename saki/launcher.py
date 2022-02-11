import atexit
import pathlib
import time
import threading
import typing
from subprocess import PIPE, Popen

import nasse.utils
import psutil
import yaml

TimezoneType = typing.Literal["iso8601-utc", "iso8601-local"]


class Timezone:
    """
    MongoDB timestamps format enum

    The time format for timestamps in log messages.

    The default is "iso8601-utc" (Timezone.UTC).

    |----------------|----------------|------------------------
    | Name           | Value          | Description
    |----------------|----------------|------------------------
    |                |                | Displays timestamps in Coordinated Universal Time (UTC)
    | Timezone.UTC   | iso8601-utc    | in the ISO-8601 format. For example, for New York at the
    |                |                | start of the Epoch: 1970-01-01T00:00:00.000Z
    |----------------|----------------|------------------------
    |                |                | Displays timestamps in local time in the ISO-8601 format.
    | Timezone.LOCAL | iso8601-local  | For example, for New York at the start of the
    |                |                | Epoch: 1969-12-31T19:00:00.000-05:00
    |----------------|----------------|------------------------
    """
    UTC: TimezoneType = "iso8601-utc"
    LOCAL: TimezoneType = "iso8601-local"


TERMINAL = "terminal"
SYSLOG = "syslog"


class Configuration:
    """
    This object represents part of a configuration file for MongoDB (and thus Saki)
    """

    def __init__(self) -> None:
        """
        Initializes the Configuration object
        """
        pass

    def to_cli_args(self) -> list[str]:
        """
        Returns a list of CLI arguments to pass to the MongoDB executable

        Returns
        -------
        list[str]
            The list of CLI arguments
        """
        pass

    def loads(self, data: str, decode: bool = True) -> None:
        """
        Loads the configuration from a YAML string (if decode == True) or a dictionary (if decode == False)

        Parameters
        ----------
        data: str
            The YAML string to load the configuration from
        """
        raise NotImplementedError("This method should be implemented by the child class")

    def load(self, file: typing.Union[str, pathlib.Path, typing.TextIO]) -> None:
        """
        Loads the configuration from a file.

        Parameters
        ----------
        file: str, pathlib.Path, typing.TextIO
            The file to load the configuration from.
        """
        if hasattr(file, "read"):
            self.loads(file.read())
            return
        with open(file, "r") as f:
            self.loads(f.read())

    def dumps(self, indent: int = 4) -> str:
        """
        YAML representation of the Configuration object

        Returns
        -------
        str
            The configuration as a YAML string
        """
        raise NotImplementedError("This method should be implemented by the child class")

    def dump(self, file: typing.Union[str, pathlib.Path, typing.TextIO]) -> None:
        """
        Dumps the configuration to a file.

        Parameters
        ----------
        file: str, pathlib.Path, typing.TextIO
            The file to dump the configuration to.
        """
        if hasattr(file, "write"):
            file.write(self.dumps())
            return
        with open(file, "w") as f:
            f.write(self.dumps())

    def to_dict(self) -> None:
        """
        Returns a `dict` representation of the Configuration object

        Returns
        -------
        dict
            The `dict` representation of the Configuration object
        """
        raise NotImplementedError("This method should be implemented by the child class")

    def __dict__(self) -> dict:
        """
        `dict` representation of the Configuration object

        Please refer to the `to_dict` method for more information
        """
        return self.to_dict()

    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, self.to_dict())


def _runtime_error_message(reason: str = None, message: str = None, output: str = None) -> str:
    """
    Internal function used to generate the RuntimeErrors' messages

    Parameters
    ----------
    reason: str
        The reason of the error
    message: str
        A warning message to add to the error
    output: str
        The MongoDB process output

    Returns
    -------
    str
        The message of the error
    """
    result = "Failed to start MongoDB process"
    if reason:
        result += " ({})".format(reason)
    if message:
        result += "\nWarning: {}".format(message)
    if output:
        result += "\n\nFull MongoDB output:\n-------------------\n{}".format(output)
    return result


class LogConfig(Configuration):
    """
    Configuration for the MongoDB logging system
    """

    def __init__(
        self,
        verbosity: int = 1,
        path: typing.Union[str, pathlib.Path] = "./saki/db.saki.log",
        append: bool = True,
        timezone: TimezoneType = Timezone.UTC,
        debug: bool = False
    ) -> None:
        """
        Initializes the LogConfig object

        Parameters
        ----------
        verbosity: int -> 1 ~ 5, default=1
            The verbosity level of the MongoDB logging system
        path: str, default="./saki/db.saki.log"
            The path of the MongoDB log file
            It can also be TERMINAL or SYSLOG
        append: bool, default=True
            Whether to append to the log file or not
        timezone: TimezoneType -> "iso8601-utc" | "iso8601-local", default=Timezone.UTC
            The timezone of the timestamps format
        debug: bool, default=False
            Whether to enable the debug mode or not
        """
        self.verbosity = min(max(1, int(verbosity)), 5)  # 1 ~ 5
        if path in (TERMINAL, SYSLOG):
            self.path = path
        else:
            self.path = pathlib.Path(path).absolute()
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.append = bool(append)
        self.timezone = timezone
        self.debug = bool(debug)
        if self.debug:
            self.verbosity = 5

    def to_cli_args(self) -> list[str]:
        results = [
            f"-{'v' * self.verbosity}",
            "--timeStampFormat", str(self.timezone)
        ]
        if self.path not in (TERMINAL, SYSLOG):
            results.extend(["--logpath", str(self.path)])
            if self.append:
                results.append("--logappend")
        elif self.path == SYSLOG:
            results.append("--syslog")
        if self.debug:
            results.append("--traceExceptions")

        return results

    def to_dict(self) -> dict:
        return {
            "verbosity": self.verbosity,
            "path": str(self.path),
            "append": self.append,
            "timezone": self.timezone,
            "debug": self.debug
        }

    def dumps(self, indent: int = 4) -> str:
        spacing = " " * indent
        file_destination = self.path not in (TERMINAL, SYSLOG)
        return "systemLog:\n" + f"\n{spacing}".join([s for s in [
            spacing + "verbosity: {}".format(self.verbosity),
            'path: "{}"'.format(self.path) if file_destination else "",
            "destination: file" if file_destination else ("destination: syslog" if self.path == SYSLOG else ""),
            "logAppend: {}".format(str(self.append).lower()),
            "timeStampFormat: {}".format(self.timezone),
            "traceAllExceptions: {}".format(str(self.debug).lower())
        ] if s.replace(" ", "") != ""])

    def loads(self, data: str, decode: bool = True) -> None:
        if decode:
            data = yaml.safe_load(data)
        data = dict(data)
        self.__init__(**{
            "verbosity": data.get("verbosity", self.verbosity),
            "path": data.get("path", self.path),
            "append": data.get("logAppend", self.append),
            "timezone": data.get("timeStampFormat", self.timezone),
            "debug": data.get("traceAllExceptions", self.debug)
        })


class MongoDB(Configuration):
    """
    Configuration for the MongoDB server

    This class is used to configure and run a MongoDB server.
    """
    __process__ = None

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 27017,
        db_path: typing.Union[str, pathlib.Path] = "./saki/data",
        fork: bool = True,
        log_config: LogConfig = None,
        max_connections: int = 65536,
        json_validation: bool = True,
        ipv6: bool = True,
        monitoring: bool = True
    ):
        """
        Initializes the MongoDB object

        If `log_config` is not provided, the default one will be used.

        Parameters
        ----------
        host: str, default="127.0.0.1"
            The host of the MongoDB server (net.bindIp)
        port: int, default=27017
            The port of the MongoDB server (net.port)
        db_path: str, default="./saki/data"
            The path of the MongoDB database (storage.dbPath)
        fork: bool, default=True
            Whether to fork the MongoDB process or not (processManagement.fork)
        log_config: LogConfig, default=None
            The MongoDB logging configuration (systemLog)
        max_connections: int, default=65536
            The maximum number of connections allowed (net.maxIncomingConnections)
        json_validation: bool, default=True
            Whether to enable the JSON validation or not (net.wireObjectCheck)
        ipv6: bool, default=True
            Whether to enable IPv6 or not (net.ipv6)
        monitoring: bool, default=True
            Whether to enable the free MongoDB monitoring or not (cloud.monitoring.free.state)
        """
        if nasse.utils.annotations.is_unpackable(log_config):
            log_config = LogConfig(**log_config)
        elif log_config is None:
            log_config = LogConfig()
        self.host = str(host)
        self.port = int(port)
        self.db_path = pathlib.Path(db_path).absolute()
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.fork = bool(fork)
        self.log_config = log_config
        self.max_connections = int(max_connections)
        self.json_validation = bool(json_validation)
        self.ipv6 = bool(ipv6)
        self.monitoring = bool(monitoring)

    def to_cli_args(self) -> typing.List[str]:
        """
        Returns a list of command line arguments for the MongoDB process.

        Returns
        -------
        list[str]
            A list of command line arguments for the mongo process.
        """
        results = [
            "--bind_ip", self.host,
            "--port", str(self.port),
            "--dbpath", str(self.db_path),
            "--maxConns", str(self.max_connections),
            "--enableFreeMonitoring", "on" if self.monitoring else "off"
            # "--wireObjectCheck", str(self.json_validation), # this is not supported by cli args
        ]
        if self.fork:
            results.append("--fork")
        if self.ipv6:
            results.append("--ipv6")
        results.extend(self.log_config.to_cli_args())

        return results

    def to_dict(self, camelCase: bool = False) -> dict[str, typing.Any]:
        result = {
            "host": self.host,
            "port": self.port,
            "db_path": str(self.db_path),
            "fork": self.fork,
            "log_config": self.log_config.to_dict(),
            "max_connections": self.max_connections,
            "json_validation": self.json_validation,
            "ipv6": self.ipv6,
            "monitoring": self.monitoring
        }
        if camelCase:
            for key, value in result.items():
                result.pop(key, None)
                key_split = key.split("_")
                result[key_split[0] + "".join([k.capitalize() for k in key_split[1:]])] = value
        return result

    def dumps(self, indent: int = 4) -> str:
        spacing = " " * indent
        return "\n".join([
            self.log_config.dumps(indent),
            "net:",
            "\n{}".format(spacing).join([
                spacing + "port: {}".format(self.port),
                "bindIp: {}".format(self.host),
                "maxIncomingConnections: {}".format(self.max_connections),
                "wireObjectCheck: {}".format(str(self.json_validation).lower()),
                "ipv6: {}".format(str(self.ipv6).lower())
            ]),
            "storage:",
            '{}dbPath: "{}"'.format(spacing, self.db_path),
            "processManagement:",
            "{}fork: {}".format(spacing, str(self.fork).lower()),
            "cloud:",
            "{}monitoring:\n{}free:\n{}state: {}".format(spacing, spacing*2, spacing*3, "on" if self.monitoring else "off")
        ])

    def loads(self, data: typing.Union[str, dict[str, typing.Any]], decode: bool = True) -> None:
        if decode:
            data = yaml.safe_load(data)
        data = dict(data)
        net = data.get("net", {})
        self.__init__(**{
            "host": net.get("bindIp", self.host),
            "port": net.get("port", self.port),
            "db_path": data.get("storage", {}).get("dbPath", self.db_path),
            "fork": data.get("processManagement", {}).get("fork", self.fork),
            "max_connections": net.get("maxIncomingConnections", self.max_connections),
            "json_validation": net.get("wireObjectCheck", self.json_validation),
            "ipv6": net.get("ipv6", self.ipv6),
            "monitoring": data.get("cloud", {}).get("monitoring", {}).get("free", {}).get("state", self.monitoring)
        })
        if "systemLog" in data:
            self.log_config.loads(data["systemLog"], decode=False)

    def start(self, executable: str = "mongod", wait: float = 3, keep_alive: bool = False) -> None:
        """
        Starts a MongoDB process.

        Parameters
        ----------
        executable: str, default="mongod"
            The path to the MongoDB executable.
        wait: float, default=3
            The number of seconds to wait for the process to start.
        keep_alive: bool, default=False
            Whether to keep the process alive or not (fork will be enabled)
        """
        fork = self.fork
        if keep_alive:
            if fork:
                nasse.utils.logging.log("The 'fork' option will be enabled because 'keep_alive' is enabled",
                                        level=nasse.utils.logging.LogLevels.WARNING)
            fork = True
        process = Popen([executable] + self.to_cli_args(), stdout=PIPE)
        if fork:
            code = process.wait()
            mongo_output = process.stdout.read().decode("utf-8")
            if code != 0:
                raise RuntimeError(_runtime_error_message(reason="Non-zero code exit",
                                   message="MongoDB exited with a {} code before starting.".format(code), output=mongo_output))
            if not "child process started successfully, parent exiting" in mongo_output:
                raise RuntimeError(_runtime_error_message(reason="No successfull confirmation",
                                   message="Saki couldn't find the confirmation that MongoDB successfully launched.", output=mongo_output))
            for line in mongo_output.split("\n"):
                try:
                    if "forked process" in line:
                        pid = int("".join([char for char in line if char.isdigit()]))
                        self.__process__ = psutil.Process(pid)
                        if not keep_alive:
                            atexit.register(self.kill)
                        return
                except Exception:
                    continue  # to raise a NO PID FOUND exception if there is an error
            raise RuntimeError(_runtime_error_message(reason="No PID found",
                               message="MongoDB may have been started but Saki could not find its PID.", output=mongo_output))
        # raise NotImplementedError("Synchronous MongoDB is not implemented yet.")

        def read_line():
            while process.poll() is None:
                time.sleep(0.01)
        t = threading.Thread(target=read_line)
        t.start()
        t.join(wait)
        code = process.poll()
        if code is not None:
            raise RuntimeError(_runtime_error_message(reason="Non-zero code exit",
                               message="MongoDB exited with a {} code before starting.".format(code)))

        # there is no timeout no more because mongodb doesn't flush its stdout so we can't wait for it
        # raise RuntimeError(_runtime_error_message(
        #     reason="Timeout", message="MongoDB didn't start within the specified timeout.", output=output))

        # we just assume that it's running

        # we need to use psutil for the forked processes, so we are forced to use the same method, even though plain Popen process would be better
        self.__process__ = psutil.Process(process.pid)

    def kill(self):
        if self.__process__ is None:
            raise RuntimeError(_runtime_error_message(reason="No process", message="MongoDB is not running."))
        self.__process__.kill()

    # aliases
    stop = kill
    terminate = kill
    close = kill

    def restart(self):
        self.kill()
        self.start()
