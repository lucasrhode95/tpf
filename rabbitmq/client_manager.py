from typing import List

from pika.adapters.asyncio_connection import AsyncioConnection

from .client import Client
from .setup_helper import SetupHelper


class ClientManager:
    """User can attach concrete implementations of Client and this manager will
    handle all the necessary setup
    """
    __instance: "ClientManager" = None
    _clients: List[Client] = None
    _setup_helper: SetupHelper = None
    _connection: AsyncioConnection = None

    def __init__(self):
        self._clients = []
        self._setup_helper = SetupHelper(self._clients)

    @classmethod
    def instance(cls) -> "ClientManager":
        if cls.__instance is None:
            cls.__instance = ClientManager()

        return cls.__instance

    def start(self):
        self._connection = self._setup_helper.setup()
        self._connection.ioloop.run_forever()

    def stop(self):
        """Shuts down the entire connection to RabbitMQ"""
        self._setup_helper.tear_down()

    def add_client(self, client: Client):
        self._clients.append(client)
