from dataclasses import dataclass

from pika.exchange_type import ExchangeType
from pika.spec import Basic, BasicProperties

DEFAULT_EXCHANGE = ""
DEFAULT_EXCHANGE_TYPE = ExchangeType.direct


@dataclass
class Address:
    queue: str = None
    routing_key: str = None  # if left blank, we'll use the same string set for "QUEUE"
    exchange: str = DEFAULT_EXCHANGE
    exchange_type: ExchangeType = DEFAULT_EXCHANGE_TYPE

    def check_attributes(self):
        if self.queue is None:
            raise AttributeError("Missing `queue` attribute")

        if self.routing_key is None:
            self.routing_key = self.queue

    def is_default_exchange(self) -> bool:
        return self.exchange == ""

    def __to_string__(self) -> str:
        return self.queue


@dataclass
class MessageMetadata:
    basic_deliver: Basic.Deliver
    properties: BasicProperties
