# Data Access Objects (DAOs)

### Summary

* Redis
* MySQL
* PostgreSQL

## Redis

We implement the `redis_manager` and `redis_manager_standalone` modules to access redis databases ([https://redis.io/](https://redis.io/)).
The standalone version removes all dependencies that the original module has on the TPF repository.

That is, you can copy and paste `redis_manager_standalone` and use it without the need to clone the entire repository.

> NOTE: currently we only support PUB/SUB, but feel free to add GET/SET support

### Using redis\_manager

See TPF's homepage for a complete usage example

### Using redis\_manager\_standalone

The standalone version can by copied to any folder in your project. Consider the following directory structure:

``` text
.
├── redis_manager_standalone.py
├── redis_publish.py
└── redis_subscribe.py
```

You can listen/publish messages as shown in `redis_publish.py` and `redis_subscribe.py`:

**redis\_publish.py:**

``` python
import time
from redis_manager_standalone import RedisManager

redis = RedisManager(host='localhost', port=6379)

while True:
    redis.publish(
        channel='my_channel',
        message='Hello World!'
    )
    time.sleep(1)
```

**redis\_subscribe.py:**

``` python
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

print('If our program finishes execution, the subscription is automatically closed.')
print('Therefore we need to keep the program alive with a while True')

print('Press Ctrl+C to quit')
while True:
    time.sleep(1)
```