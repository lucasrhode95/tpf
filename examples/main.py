from app_manager import AppManager
from redis.redis_manager import RedisManager


class Main(AppManager):
    redis: RedisManager

    @classmethod
    def setup(cls):
        # configures the connection:
        cls.redis = RedisManager(
            host='localhost',
            port=6379
        )

        # subscribes to 'my_channel_listen'
        cls.redis.subscribe(
            channel='my_channel_listen',
            callback=cls.my_channel_callback
        )

    @classmethod
    def run(cls):
        # keeps the app running until the user hits Ctrl+C
        cls.wait_for_ctrl_c()

    @classmethod
    def tear_down(cls):
        # unsubscribes from all channels
        cls.redis.clean_up()

    @classmethod
    def my_channel_callback(cls, msg):
        print('Message received!', msg)
        cls.redis.publish(
            channel='my_channel_response',
            message='echo: ' + msg
        )


if __name__ == '__main__':
    Main.start("my-app-name")
