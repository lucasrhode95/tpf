"""
Contains methods to help the user configure the application
"""
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from abc import ABC
from os import path
from configparser import ConfigParser, NoOptionError, NoSectionError
import __main__


class AppSettings(ABC):
    """
    Handles the reading/writing of global parameters of the application, such
    as database URLs, usernames and passwords.
    All the parameters are stored on the "app_settings.ini" file. On that file,
    each section contains parameters for a different environment, namely
    "development", "production" and "localhost".

    Please note that the `setup` method also configures the logging
    environment using a StreamHandler and a TimedRotatingFileHandler
    See: https://docs.python.org/3/library/logging.handlers.html

    ----
    Usage example:
    def main()
        AppSettings.setup(AppSettings.PRODUCTION)
        connect()

    def connect(self):
        try:
            db = mysql.connect(
                host = AppSettings.get_str('db_host', default='localhost'),
                user = AppSettings.get_str('db_user', default='postgres'),
                password = AppSettings.get_str('db_password', default=''),
                port = AppSettings.get_int('db_port', default=5432)
            )
        except:
            pass
    """

    # environment names
    DEVELOPMENT = 'development'
    PRODUCTION = 'production'
    # localhost mode refers to when you run the program via command line,
    # like `python main.py` instead of using docker-compose up
    LOCALHOST = 'localhost'

    environment = DEVELOPMENT

    _parser: ConfigParser = ConfigParser()
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

        cls.setup_parser()
        cls.setup_logger()

    @classmethod
    def setup_parser(cls) -> None:
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
    def setup_logger(cls) -> None:
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
    def get_str(cls, param: str, default: str = None) -> str:
        cls._check_setup(default)
        try:
            out = cls._parser.get(cls.environment, param)
            cls._log('%s.%s="%s"', cls.environment, param, out)
        except (NoSectionError, NoOptionError):
            if default is not None:
                out = default
                msg = 'Unable to read [%s.%s] from [%s]. Using default "%s".'
                cls._log(msg, cls.environment, param,
                         cls.CONFIG_FILE_PATH, out)
            else:
                raise

        return out

    @classmethod
    def get_int(cls, param: str, default: int = None) -> int:
        cls._check_setup(default)
        try:
            out = cls._parser.getint(cls.environment, param)
            cls._log('%s.%s=%s', cls.environment, param, out)
        except (NoSectionError, NoOptionError):
            if default is not None:
                out = default
                msg = 'Unable to read [%s.%s] from [%s]. Using default %s.'
                cls._log(msg, cls.environment, param,
                         cls.CONFIG_FILE_PATH, out)
            else:
                raise

        return out

    @classmethod
    def _check_setup(cls, default: any = None) -> None:
        if not cls._initialized_parser:
            if default is None:
                msg = 'AppSettings has not been initialized. Either call ' + \
                      'AppSettings.setup(), AppSettings.setup_parser() or ' + \
                      'use a default value argument'
                raise RuntimeError(msg)

    @classmethod
    def is_development(cls) -> bool:
        return cls.environment == cls.DEVELOPMENT

    @classmethod
    def is_production(cls) -> bool:
        return cls.environment == cls.PRODUCTION

    @classmethod
    def is_localhost(cls) -> bool:
        return cls.environment == cls.LOCALHOST
