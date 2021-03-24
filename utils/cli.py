"""
Contains facilities to deal with command line args
"""
import sys
import time
import logging


def block_execution():
    """
    Waits for a ctrl+C event
    """
    while True:
        logging.info('Waiting for ctrl+C event (printed every 15min)')
        try:
            time.sleep(900)
        except KeyboardInterrupt:
            logging.info('^C')
            break


def get_cli_arg(idx: int = 1, default: any = None) -> str:
    """
    Retrieves a switch from the command line interface
    """
    try:
        return sys.argv[idx]
    except IndexError:
        return default
