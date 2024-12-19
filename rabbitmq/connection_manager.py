import asyncio
import logging
from typing import Callable

from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.connection import ConnectionParameters
from pika.credentials import PlainCredentials

from ..app_settings import AppSettings


class ConnectionManager:
    __connection: AsyncioConnection = None
    __channel: Channel = None
    connection_parameters: ConnectionParameters = None

    @classmethod
    def get_connection_parameters(cls):
        """If no connection parameters are set, will try to read parameters from
        `app_settings.ini`
        """
        if cls.connection_parameters is not None:
            return cls.connection_parameters

        credentials = PlainCredentials(
            username=AppSettings.get_str("rabbitmq_username"),
            password=AppSettings.get_str("rabbitmq_password"),
        )

        cls.connection_parameters = ConnectionParameters(
            host=AppSettings.get_str("rabbitmq_host"),
            port=AppSettings.get_int("rabbitmq_port"),
            credentials=credentials,
            virtual_host=AppSettings.get_str("rabbitmq_virtual_host"),
        )

        return cls.connection_parameters

    @classmethod
    def on_connection_open_error(cls, _unused_connection, err):
        """This method is called by pika if the connection to RabbitMQ
        can't be established.
        """
        logging.error("Connection open failed: %s", err)

    @classmethod
    def _setup_event_loop(cls):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

    @classmethod
    def get_connection(cls, on_open_callback: Callable[[AsyncioConnection], object] = None) -> AsyncioConnection:
        if cls.__connection is not None and not cls.__connection.is_open:
            if on_open_callback is not None:
                # TODO: try to use `connection.ioloop.call_later(0.1, callback)`
                on_open_callback(cls.__connection)
        else:
            cls._setup_event_loop()
            cls.__connection = AsyncioConnection(
                parameters=cls.get_connection_parameters(),
                on_open_callback=on_open_callback,
            )

        return cls.__connection

    @classmethod
    def close_connection(cls):
        if cls.__connection.is_closing or cls.__connection.is_closed:
            return

        cls.__connection.close()

    @classmethod
    def get_channel(cls, on_open_callback: Callable[[Channel], object] = None) -> Channel:
        if cls.__channel is not None and cls.__channel.is_open:
            if on_open_callback is not None:
                # TODO: try to use `connection.ioloop.call_later(0.1, callback)`
                on_open_callback(cls.__channel)
        else:
            cls.__channel = cls.__connection.channel(on_open_callback=on_open_callback)

        return cls.__channel
