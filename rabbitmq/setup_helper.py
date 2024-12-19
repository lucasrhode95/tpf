import asyncio
import logging
from dataclasses import dataclass
from typing import List

from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.spec import Basic, BasicProperties

from .client import Client
from .connection_manager import ConnectionManager
from .types import Address, MessageMetadata


@dataclass
class ClientConfigContainer:
    address: Address
    client: Client
    is_subscriber: bool


@dataclass
class SetupHelper:
    """
    Configuring a RabbitMQ connection, channel and queue using the non-blocking
    connection adapter `AsyncioConnection` is very cumbersome. We extracted the
    routines/callbacks that do so in this module. This improves the readabilty
    of the code by keeping actual functionality separate from boilerplate code.
    """
    clients: List[Client] = None

    # shared resources
    _connection: AsyncioConnection = None
    _channel: Channel = None

    # subscriber handler
    _consumer_tags: List[str] = None
    _consumer_tags_closed: int = 0

    def __init__(self, clients: List[Client]):
        self.clients = clients
        self._consumer_tags = []

    def setup(self) -> AsyncioConnection:
        """
        Prepares a series of set-up hooks BUT DOESN'T EXECUTE THEM
        - setup_channel
        - setup client(s)
           - setup_exchange
           - setup_queue
           - setup_routing_key
           - setup_qos
           - setup_message_callback

        This cascade of events will only go down once
        `self._connection.ioloop.run_forever()` is called

        See: ClientManager.start()
        """

        def callback(connection: AsyncioConnection):
            self._connection = connection
            self._setup_channel()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return ConnectionManager.get_connection(callback)

    def _setup_channel(self):
        def callback(channel):
            self._channel = channel
            self._setup_clients()

        ConnectionManager.get_channel(callback)

    def _setup_clients(self):
        for client in self.clients:
            client.set_channel(self._channel)
            self._setup_address(ClientConfigContainer(
                address=client.publisher_address,
                client=client,
                is_subscriber=False,
            ))
            self._setup_address(ClientConfigContainer(
                address=client.subscriber_address,
                client=client,
                is_subscriber=True,
            ))

    def _setup_address(self, data: ClientConfigContainer):
        if not data.address:
            return

        data.address.check_attributes()
        self._setup_exchange(data)

    def _setup_exchange(self, data: ClientConfigContainer):
        if data.address.is_default_exchange():
            # TODO: try to use `connection.ioloop.call_later(0.1, callback)`
            self._setup_queue(data)
            return

        self._channel.exchange_declare(
            exchange=data.address.exchange,
            exchange_type=data.address.exchange_type,
            callback=lambda _: self._setup_queue(data)
        )

    def _setup_queue(self, data: ClientConfigContainer):
        self._channel.queue_declare(
            queue=data.address.queue,
            callback=lambda _: self._setup_routing_key(data)
        )

    def _setup_routing_key(self, data: ClientConfigContainer):
        def callback(frame=None):
            if not data.is_subscriber:
                return

            self._setup_qos(data)

        if data.address.is_default_exchange():
            callback()
            return

        self._channel.queue_bind(
            data.address.queue,
            data.address.exchange,
            routing_key=data.address.routing_key,
            callback=callback
        )

    def _setup_qos(self, data: ClientConfigContainer):
        """This method sets up the consumer prefetch to only be delivered
        `self._prefetch_count` messages at a time. The consumer must acknowledge
        these messages before RabbitMQ will deliver another one. Experiment with
        different prefetch values to achieve desired performance.
        """
        self._channel.basic_qos(
            prefetch_count=data.client.prefetch_count,
            callback=lambda _: self._setup_message_callback(data)
        )

    def _setup_message_callback(self, data: ClientConfigContainer):
        """Sets up this class as a consumer of RabbitMQ messages.

        The consumer tag is a unique identifier of the consumer with RabbitMQ.
        We keep the value to use it when we want to cancel consuming.
        """

        def acknowledge_and_forward(_, basic_deliver: Basic.Deliver, properties: BasicProperties, body: bytes):
            self._channel.basic_ack(basic_deliver.delivery_tag)
            metadata = MessageMetadata(
                basic_deliver=basic_deliver,
                properties=properties
            )
            data.client.on_message_wrapper(body, metadata)

        consumer_tag = self._channel.basic_consume(
            queue=data.address.queue,
            on_message_callback=acknowledge_and_forward
        )
        self._consumer_tags.append(consumer_tag)

    def _close_channel_if_all_clients_stopped(self, _):
        """This will be called after each client has finished closing

        See: SetupHelper.tear_down"""
        self._consumer_tags_closed += 1
        if self._consumer_tags_closed < len(self._consumer_tags):
            # not all clients have been stopped yet...
            return

        logging.debug("Closing RabbitMQ channel and connection")
        # after the last client has finished closing, begin shutdown
        self._channel.close()
        self._connection.close()
        self._connection.ioloop.stop()

    def tear_down(self):
        # close consumer tags
        for tag in self._consumer_tags:
            self._channel.basic_cancel(
                consumer_tag=tag,
                callback=self._close_channel_if_all_clients_stopped
            )
