import time
from redis_manager_standalone import RedisManager

redis = RedisManager(host='localhost', port=6379)

while True:
    redis.publish(
        channel='my_channel',
        message='Hello World!'
    )
    time.sleep(1)
