import asyncio
import inspect
import json
import logging
import traceback
from abc import ABC
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Callable, Coroutine

from pika.channel import Channel
from pika.spec import BasicProperties

from .errors import InvalidFormatError, MissingPublisherAddressError
from .types import Address, MessageMetadata
from ..app_settings import AppSettings

OnMessageCallbackType = Callable[[dict | str, MessageMetadata], None] | Coroutine[any, dict, MessageMetadata]
OnMessageErrorCallbackType = Callable[["Client", Exception, MessageMetadata], None]


class DefaultParameters(ABC):
    """
    Instead of creating a bunch of module-variables, we use this abstract class
    to store our default values.
    """
    ON_MESSAGE_ERROR: OnMessageErrorCallbackType = None


@dataclass
class Client:
    """
    Client to publish and subscribe to queues in RabbitMQ.
    """
    # exchange, queue + routing key
    subscriber_address: Address = None
    publisher_address: Address = None

    # behavior config
    on_message: OnMessageCallbackType = None
    on_message_error: OnMessageErrorCallbackType = None
    parse_json: bool = True  # automatically parse messages?

    # performance config
    prefetch_count = 1  # in production, experiment with higher values for increased consumer throughput

    # shared resources
    _channel: Channel = None

    # internal variables
    consumer_tag: str = None
    _publish_properties: BasicProperties = None  # App metadata, sent along with each published message

    def set_channel(self, channel: Channel):
        self._channel = channel

    def _parse_incoming_message(self, body: bytes) -> dict | str:
        data = str(body, "utf-8")
        if not self.parse_json:
            return data

        try:
            return json.loads(data)
        except JSONDecodeError as e:
            message = f"Couldn't decode string as JSON: {data}"
            logging.error(message)
            raise InvalidFormatError(message) from e

    def on_message_wrapper(self, body: bytes, metadata: MessageMetadata):
        message_id = metadata.basic_deliver.delivery_tag
        queue = self.subscriber_address.queue

        if self.on_message is not None:
            logging.debug("Processing message #%s @ \"%s\"", message_id, queue)
        else:
            logging.debug("Ignoring message #%s @ \"%s\"", message_id, queue)
            return

        async def task_wrapper():
            try:
                message = self._parse_incoming_message(body)
                output = self.on_message(message, metadata)

                if inspect.isawaitable(output):
                    await output
            except (Exception, KeyboardInterrupt) as e:
                if self.on_message_error:
                    self.on_message_error(self, e, metadata)
                elif DefaultParameters.ON_MESSAGE_ERROR:
                    DefaultParameters.ON_MESSAGE_ERROR(self, e, metadata)
                else:
                    logging.error("Uncaught error while processing message (%s) \"%s\"", e, body)
                    logging.debug(traceback.format_exc())

        loop = asyncio.get_event_loop()
        loop.create_task(task_wrapper())

    def _get_publish_properties(self):
        if self._publish_properties is None:
            self._publish_properties = BasicProperties(
                app_id=AppSettings.get_str("rabbitmq_app_id", "Unknown"),
                content_type="application/json",
            )

        return self._publish_properties

    def publish(self, message: str | dict):
        if not self.publisher_address:
            raise MissingPublisherAddressError("Cannot publish messages without a publisher address")

        if not isinstance(message, str):
            message = json.dumps(message)

        logging.debug("Publishing message at \"%s\"", self.subscriber_address.queue)

        self._channel.basic_publish(
            exchange=self.publisher_address.exchange,
            routing_key=self.publisher_address.routing_key,
            body=message,
            properties=self._get_publish_properties()
        )

    @classmethod
    def set_default_on_message_error_handler(cls, on_message_error: OnMessageErrorCallbackType):
        DefaultParameters.ON_MESSAGE_ERROR = on_message_error
