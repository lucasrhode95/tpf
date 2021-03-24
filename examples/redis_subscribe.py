import time
from redis_manager_standalone import RedisManager


def my_channel_callback(msg):
    print('Message received!', msg)


redis = RedisManager(host='localhost', port=6379)
redis.subscribe(
    channel='my_channel',
    callback=my_channel_callback
)
print('Listening for messages on "my_channel"...')

# If our program finishes execution, the subscription is automatically closed.
# Therefore we need to keep the program alive:

print('Press Ctrl+C to quit')
while True:
    time.sleep(1)
