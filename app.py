"""
Contains methods used to encapsulate the main method execution of an
application
"""
# system imports
import logging
import platform
import sys
from abc import ABC, abstractmethod
from signal import SIGTERM, signal
from threading import Event

# framework imports
from .helpers.app_settings import AppSettings
from .utils.cli import get_cli_arg


class App(ABC):
    """
    Class used to encapsulate all the application info. It helps you create and
    execute a main method easily by encapsulating error handling, ctrl+C event
    listening and cleaning up
    """

    shutdown = Event()

    def __init__(self):
        clazz = type(self).__name__
        # use App.start(), do NOT use App().start()
        raise RuntimeError(f'Abstract class "{clazz}" cannot be instantiated')

    @classmethod
    def setup(cls) -> None:
        pass

    @classmethod
    @abstractmethod
    def run(cls) -> None:
        raise NotImplementedError()

    @classmethod
    def tear_down(cls) -> None:
        pass

    @classmethod
    def start(cls) -> None:
        """
        Encapsulates all steps necessary to create and run an application.
        """
        cls.shutdown.clear()

        # sets up the environment
        env = get_cli_arg(1, AppSettings.LOCALHOST)
        AppSettings.setup(env)

        logging.debug('APP STARTED (ENV=%s)', env)

        # executes the setup method
        try:
            cls.setup()
        except Exception as ex:
            logging.error('Error while executing SETUP method (%s)', ex)
            cls._execute_tear_down()
            raise

        # executes main method
        try:
            cls.run()
        except Exception as ex:
            logging.error('Error while executing RUN method (%s)', ex)
            raise
        finally:
            cls._execute_tear_down()
            logging.debug('EXECUTION FINISHED')

    @classmethod
    def wait_for_ctrl_c(cls) -> None:
        """
        Prevents the application from finishing until the user presses ctrl+C.

        Alternatively, clients can send a termination signal OR simply call
        App.force_stop()
        """
        # makes sure the app is listening to termination signals
        cls.register_termination_signals()

        logging.info('Press ctrl+C to quit')
        while not cls.shutdown.is_set():
            try:
                # when running on windows systems we need to use a polling
                # strategy, otherwise the ctrl+C event will not be heard
                if platform.system() == 'Linux':
                    cls.shutdown.wait()
                else:
                    cls.shutdown.wait(1)
            except KeyboardInterrupt:
                logging.debug('^C listener stopped (KeyboardInterrupt)')
                return

        logging.debug('^C listener stopped (shutdown.set())')

    @classmethod
    def register_termination_signals(cls) -> None:
        """
        Converts a interrupt signal (like when we press ctrl+C on a
        docker container) into a KeyboardInterrupt exception.

        This is necessary for gracefully shutting down a docker container
        """

        def handler(*args):
            logging.debug('SIGTERM received')
            cls.shutdown.set()

        signal(SIGTERM, handler)

    @classmethod
    def _execute_tear_down(cls) -> None:
        """
        Executes the clean up routine
        """
        logging.debug('Running TEAR_DOWN method')
        try:
            cls.tear_down()
        except Exception as ex:
            logging.error('Error while executing TEAR_DOWN method (%s)', ex)
            raise

    @classmethod
    def force_stop(cls, exit_code=0) -> None:
        """
        Takes all the necessary steps to kill the application as gracefully as
        possible
        """
        logging.debug('Graceful shutdown requested')
        cls.shutdown.set()
        sys.exit(exit_code)
