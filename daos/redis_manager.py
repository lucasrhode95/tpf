"""Contains facilities that help clients connect and subscribe to redis
channels."""
# system imports
import json
import logging
import re
import threading
from abc import ABC
from dataclasses import dataclass
from typing import Callable

# api import
import redis

# framework imports
from ..helpers.app_settings import AppSettings


def _default_exception_handler(ex: Exception, subscription: 'Subscription'):
    subscription.log_exception(ex)
    logging.debug('Re-raising the exception')
    raise ex


def _handle_msg(msg, subscription: 'Subscription'):
    """Everything we need to do before calling the user's callback function"""
    subscription.last_message_received_raw = msg

    payload = msg['data'].decode('unicode-escape')
    if msg['type'] != 'message':
        debug_msg = 'Ignoring message. Channel=[%s] | Type=[%s] | Payload=[%s]'
        logging.debug(debug_msg, subscription.channel, msg['type'], payload)
        return

    if subscription.decode_json:
        payload = _decode_json(payload)

    try:
        subscription.callback(payload)
    except Exception as ex:
        logging.debug('Executing exception_handler')
        subscription.exception_handler(ex, subscription)


def _decode_json(msg: str) -> dict:
    msg = re.sub('^"|"$', '', msg)  # removes leading and trailing quotes
    msg = json.loads(msg)
    return msg


@dataclass
class Subscription:
    """Data of a redis subscription"""
    # INPUTS
    channel: str
    callback: Callable[[str], None]

    # OUTPUTS
    thread: threading.Thread = None
    pubsub: redis.client.PubSub = None
    last_message_received_raw: dict = None
    last_message_posted_payload: str = None

    # OPTIONAL INPUTS
    decode_json: bool = False
    exception_handler: Callable[[Exception, 'Subscription'], None] = \
        _default_exception_handler

    def __post_init__(self) -> None:
        if not callable(self.callback):
            raise TypeError('"callback" must be a function')
        if self.exception_handler and not callable(self.exception_handler):
            raise TypeError('"exception_handler" must be None or a function')

    def log_exception(self, ex: Exception):
        logging.error(
            '%s("%s") while processing message. Channel=[%s] | Payload=[%s]',
            type(ex).__name__, ex, self.channel,
            self.last_message_received_raw
        )


class RedisManager:
    """
    Class to wrap the main functions of redis.Redis.

    It provides facilities to access the core methods, connection pooling,
    threaded subscriptions etc.

    See also: https://pypi.org/project/redis/
    """

    def __init__(self, host='localhost', port=6379):
        # list of active subscriptions. The format is:
        # {'my_channel': Subscription}
        self._subscriptions: dict = {}

        # connection pool
        self._pool = redis.ConnectionPool(
            host=AppSettings.get_str('redis_host', default=host),
            port=AppSettings.get_int('redis_port', default=port)
        )

        # other configurations
        self._charset = AppSettings.get_str('redis_charset', default='utf-8')

    def _build_redis(self) -> redis.Redis:
        return redis.Redis(
            connection_pool=self._pool,
            charset=self._charset,
            decode_responses=True
        )

    def subscribe(self, subscription: Subscription = None, **kwargs) -> None:
        """
        Subscribes to a channel in a new thread and binds a callback to
        handle messages
        """
        if subscription is None:
            subscription = Subscription(**kwargs)

        self._unsubscribe_if_already_subscribed(subscription)
        self._create_pubsub_and_thread(subscription)
        self._subscriptions[subscription.channel] = subscription
        logging.debug('Subscribed to "%s"', subscription.channel)

    def unsubscribe(self, channel: str) -> None:
        """
        Unsubscribes from a given channel

        NOTE: do NOT use pubsub.close() here because it will close the
        connection to redis server, causing all other subscriptions to raise
        exceptions
        """
        try:
            subscription = self.get_subscription_by_channel(channel)
            subscription.pubsub.unsubscribe(channel)

            # tries to forcefully stop the thread using a deprecated method
            try:
                subscription.thread.stop()
            except AttributeError:
                logging.debug('Method threading.Thread.stop unavailable.')

            logging.debug('Unsubscribed from "%s"', channel)
        except KeyError:
            msg = 'Tried to unsubscribe from "%s" but not subscription exists'
            logging.debug(msg, channel)
        except Exception as ex:
            msg = '%s(%s) while unsubscribing from "%s"'
            logging.debug(msg, type(ex).__name__, ex, channel)

    def publish(self, channel: str, msg: str) -> None:
        self._build_redis().publish(channel, msg)

        if self.is_subscribed_to(channel):
            subscription = self.get_subscription_by_channel(channel)
            subscription.last_message_posted_payload = msg

        logging.debug('Published to "%s"', channel)

    def get_subscription_by_channel(self, channel: str) -> Subscription:
        return self._subscriptions[channel]

    def clean_up(self) -> None:
        """Destructor - performs all necessary clean up"""
        # here we need to create a list from the keys dict because
        # self.unsubscribe actually removes elements from the _subscriptions
        # dict during its execution
        for channel in list(self._subscriptions.keys()):
            # noinspection PyBroadException
            try:
                self.unsubscribe(channel)
            except:
                pass

    def is_subscribed_to(self, channel: str) -> bool:
        try:
            self.get_subscription_by_channel(channel)
            return True
        except KeyError:
            return False

    def _unsubscribe_if_already_subscribed(self, subscription: Subscription) \
            -> None:
        if self.is_subscribed_to(subscription.channel):
            logging.info('Subscription %s already exists and will be '
                         'replaced.', subscription.channel)
            self.unsubscribe(subscription.channel)

    def _create_pubsub_and_thread(self, subscription: Subscription) -> None:
        subscription.pubsub = self._build_redis().pubsub()
        subscription_dict = {
            subscription.channel: lambda msg: _handle_msg(msg, subscription)
        }
        subscription.pubsub.subscribe(**subscription_dict)
        subscription.thread = subscription.pubsub.run_in_thread(daemon=True)


class RedisManagerSingleton(ABC):
    """Thread-safe singleton for clients that need a Redis singleton instance"""

    __instance: RedisManager = None

    @classmethod
    def instance(cls) -> RedisManager:
        """Returns a singleton instance of RedisManager"""
        # https://en.wikipedia.org/wiki/Double-checked_locking
        if cls.__instance is None:
            with threading.Lock():
                if cls.__instance is None:
                    cls.__instance = RedisManager()

        return cls.__instance
