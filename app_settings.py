"""
Contains methods to help the user configure the application
"""
import __main__
import logging
import os
import sys
from abc import ABC
from configparser import BasicInterpolation, ConfigParser, NoOptionError, NoSectionError
from logging.handlers import TimedRotatingFileHandler
from os import path
from typing import Callable


class EnvVarsInterpolation(BasicInterpolation):
    """
    Adds the ability to bind environment variables in app_settings.ini by
    prepending`$` to the variable name.

    For example, given an environment variable called `MY_SECRET_PASSWORD`,
    users can use that value in the `app_settings.ini` file as follows:

    db_password=$MY_SECRET_PASSWORD

    Then, `AppSettings.get_str("db_password")` will return the value of the
    environment variable "MY_SECRET_PASSWORD"
    """

    def get_env_var(self, var_name: str):
        if var_name not in os.environ:
            raise RuntimeError(f"Environment variable \"{var_name}\" is not defined")

        return os.environ[var_name]

    def before_get(self, parser, section, option, value, defaults):
        if value.startswith("$"):
            var_name = value[1:]  # remove dollar sign
            value = self.get_env_var(var_name)

        return super().before_get(parser, section, option, value, defaults)


class AppSettings(ABC):
    """
    Handles the reading/writing of global parameters of the application, such
    as database URLs, usernames and passwords.

    All the parameters are stored on the "app_settings.ini" file. In that file,
    each section contains parameters for a different environments, such as
    "development", "homolog", "production" etc. The environment is controlled by
    the variable `AppSettings.environment`

    It also supports environment variable binding `my_parameter=$env_var_name`
    and a [DEFAULT] section with fallback values for every app environment

    Please note that the `setup` method also configures the logging
    environment using a StreamHandler and a TimedRotatingFileHandler
    See: https://docs.python.org/3/library/logging.handlers.html

    ----
    Usage example:

    # In Python:
    AppSettings.setup("development")
    print(AppSettings.get_str('db_host', default='localhost'))
    print(AppSettings.get_str('db_password'))

    # app_settings.ini:
    [DEFAULT]
    log_level=DEBUG
    [development]
    db_host=<uri-to-mysql>
    db_password=$my_secret_password
    """
    # section of the `app_settings.ini` file to be used
    environment = 'development'
    # when a key isn't found in the `environment` section, AppSettings will look
    # for it under a "global" section, with this name:
    global_environment = 'DEFAULT'

    _parser: ConfigParser = ConfigParser(interpolation=EnvVarsInterpolation())
    CONFIG_FILE_PATH = path.join(
        path.dirname(__main__.__file__),
        'app_settings.ini'
    )

    LOG_FILE_PATH = path.join(
        path.dirname(__main__.__file__),
        'app.log'
    )

    _initialized_parser = False
    _initialized_logger = False

    @classmethod
    def setup(cls, environment: str = None) -> None:
        """
        Initializes the settings file parser and configures the logging library
        """
        if environment:
            cls.environment = environment

        cls._setup_parser()
        cls._setup_logger()

    @classmethod
    def _setup_parser(cls) -> None:
        """
        Initializes the settings file parser
        """
        if path.exists(cls.CONFIG_FILE_PATH):
            cls._parser.read(cls.CONFIG_FILE_PATH)
            cls._initialized_parser = True
            cls._log('Settings file parser initialized')
        else:
            file_name = cls.CONFIG_FILE_PATH
            msg = 'The configuration file "%s" does not exist. Using only ' \
                  'default attribute values.'
            cls._log(msg, file_name)

    @classmethod
    def _setup_logger(cls) -> None:
        cls._clean_up_log_handlers()
        cls._setup_log_level()

        formatter = cls._build_log_formatter()
        cls._setup_console_logging(formatter)
        cls._setup_file_logging(formatter)

        sys.stdout.flush()

        cls._initialized_logger = True
        cls._log('Logger initialized')

    @classmethod
    def _get_logger(cls) -> logging.Logger:
        return logging.getLogger()

    @classmethod
    def _get_log_handlers(cls) -> list:
        return cls._get_logger().handlers[:]

    @classmethod
    def _clean_up_log_handlers(cls) -> None:
        for handler in cls._get_log_handlers():
            cls._get_logger().removeHandler(handler)
            handler.close()

    @classmethod
    def _setup_log_level(cls) -> None:
        log_level = cls.get_str('log_level', default='DEBUG').upper()
        cls._get_logger().setLevel(log_level)

    @classmethod
    def _build_log_formatter(cls) -> logging.Formatter:
        max_logging_length = cls.get_int('log_max_length', 200)
        format_str = '%(asctime)s: [%(levelname)s][%(module)s:%(lineno)d] ' + \
                     f'%(message).{max_logging_length}s'
        return logging.Formatter(format_str, '%Y-%m-%d %H:%M:%S')

    @classmethod
    def _setup_console_logging(cls, formatter: logging.Formatter) -> None:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        cls._get_logger().addHandler(sh)

    @classmethod
    def _setup_file_logging(cls, formatter: logging.Formatter) -> None:
        file_path = cls.get_str('log_file', default=cls.LOG_FILE_PATH)
        fh = TimedRotatingFileHandler(file_path, 'midnight')
        fh.setFormatter(formatter)
        fh.suffix = '%Y-%m-%d'
        cls._get_logger().addHandler(fh)

    @classmethod
    def flush_log(cls):
        handler: logging.Handler
        for handler in cls._get_log_handlers():
            handler.flush()

    @classmethod
    def _log(cls, msg: str, *args) -> None:
        if cls._initialized_logger:
            logging.debug(msg, *args)
        else:
            print(msg.replace('%s', '{}').format(*args))

    @classmethod
    def _try_to_get_value(cls, getter: Callable, param: str, environment: str) -> str:
        out = getter(environment, param)

        if isinstance(out, str):
            cls._log('%s.%s="%s"', cls.environment, param, out)
        else:
            cls._log('%s.%s=%s', cls.environment, param, out)

        return out

    @classmethod
    def _try_to_get_local_environment_fallback_to_global(cls, getter: Callable, param: str) -> str:
        try:
            # Plan A: read from current environment
            return cls._try_to_get_value(getter, param, cls.environment)
        except (NoSectionError, NoOptionError):
            # Plan B: read from global environment
            try:
                return cls._try_to_get_value(getter, param, cls.global_environment)
            except (NoSectionError, NoOptionError):
                raise NoOptionError(option=param, section=cls.global_environment)

    @classmethod
    def _get_any(cls, getter: Callable, param: str, default: any = None) -> any:
        cls._check_setup(default)

        try:
            out = cls._try_to_get_local_environment_fallback_to_global(getter, param)
        except (NoSectionError, NoOptionError):
            if default is None:
                raise

            out = default
            msg = 'Unable to read [%s.%s] from [%s]. Using default "%s".'
            cls._log(msg, cls.environment, param, cls.CONFIG_FILE_PATH, out)

        return out

    @classmethod
    def get_str(cls, param: str, default: str = None) -> str:
        getter = cls._parser.get
        return cls._get_any(getter, param, default)

    @classmethod
    def get_int(cls, param: str, default: int = None) -> int:
        getter = cls._parser.getint
        return cls._get_any(getter, param, default)

    @classmethod
    def get_bool(cls, param: str, default: bool = None) -> bool:
        getter = cls._parser.getboolean
        return cls._get_any(getter, param, default)

    @classmethod
    def get_float(cls, param: str, default: float = None) -> float:
        getter = cls._parser.getfloat
        return cls._get_any(getter, param, default)

    @classmethod
    def _check_setup(cls, default: any = None) -> None:
        if not cls._initialized_parser:
            if default is None:
                msg = 'AppSettings has not been initialized. Call AppSettings.setup() or use a default value argument'
                raise RuntimeError(msg)
