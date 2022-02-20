import inspect
import time


class Colors:
    normal = '\033[0m'
    grey = '\033[90m'
    red = '\033[91m'
    green = '\033[92m'
    blue = '\033[94m'
    cyan = '\033[96m'
    white = '\033[97m'
    yellow = '\033[93m'
    magenta = '\033[95m'

    _colors = {normal, grey, red, green, blue, cyan, white, yellow, magenta}


class LogLevel():
    def __init__(self, level: str, template: str, debug: bool = False) -> None:
        self.level = str(level)
        self.template = str(template)
        self.debug = bool(debug)

        self._draw_time = "{time}" in self.template
        self._draw_name = "{name}" in self.template
        self._draw_step = "{step}" in self.template
        self._draw_message = "{message}" in self.template

    def __repr__(self) -> str:
        return "<LogLevel: {level}>".format(level=self.level)


class LogLevels:
    INFO = LogLevel(level="Info", template=Colors.grey +
                    "{time}｜" + Colors.normal + "[INFO] ({name}) [{step}] {message}")
    DEBUG = LogLevel(debug=True, level="Debug", template=Colors.grey +
                     "{time}｜" + Colors.normal + "[DEBUG] ({name}) [{step}] {message}")
    WARNING = LogLevel(level="Warning", template=Colors.grey +
                       "{time}｜" + Colors.normal + "[WARNING] ({name}) [{step}] " + Colors.yellow + "{message}" + Colors.normal)
    ERROR = LogLevel(level="Error", template=Colors.grey +
                     "{time}｜" + Colors.normal + "[ERROR] ({name}) [{step}] " + Colors.red + "!! {message} !!" + Colors.normal)

    def __repr__(self) -> str:
        return "<LogLevels Container>"


def caller_name(skip: int = 2):
    """
    https://stackoverflow.com/a/9812105/11557354
       Get a name of a caller in the format module.class.method

       `skip` specifies how many levels of stack to skip while getting caller
       name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

       An empty string is returned if skipped levels exceed stack height
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return ''
    parentframe = stack[start][0]
    name = []
    module = inspect.getmodule(parentframe)
    if module:
        name.append(module.__name__)
    if 'self' in parentframe.f_locals:
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append(codename)  # function or a method
    del parentframe, stack
    return ".".join(name)


def log(message: str = "Log", level: LogLevel = LogLevels.DEBUG, step: str = None):
    if not level.debug:
        formatting = {}
        if level._draw_time:
            formatting["time"] = int(time.time())
        if level._draw_step:
            formatting["step"] = step if step is not None else caller_name()
        if level._draw_name:
            formatting["name"] = "Yuno"
        if level._draw_message:
            formatting["message"] = message

        print(level.template.format(**formatting))
