# Turing Python Framework (TPF)

### Summary

This is an initial attempt to generalize and centralize reusable Python snippets and classes that our team (CERTI->CES->Turing) implements.
As of right now (march, 24, 2020) I am the only contributor to this, that's why it is in my private repository. In the future the fate of this repository will be to be merge into the super-strict agile-ces workspace. However, since that workspace is tighly controlled and I do not have adminitrative rights, I will not be uploading it there anytime soon.

### Setup

Just download/clone this repository in a folder next to your Python entrypoint (i.e. `main.py`) and you are good to go

## Examples

### Getting Started

> TPF makes it super easy for you to create an app with a setup, a main and a tear-down method.

Consider a project with the following structure:

```
.
├── main.py
└── turing
```

You can create a setup->run->tear down app by extending the `App` class as follows
**main.py:**

```python
from tpf.app import App

class Main(App):

    message: str

    @classmethod
    def setup(cls):
        cls.message = 'Hello World!'

    @classmethod
    def run(cls):
        print(cls.message)

    @classmethod
    def tear_down(cls):
        cls.message = None

if __name__ == '__main__':
    Main.start()
```

> Note: `setup` and `tear_down` methods are optional. They can be removed from the

### Using RedisManager

**main.py:**

```python
from tpf.app import App
from tpf.daos.redis_manager import RedisManager

class Main(App):

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
    Main.start()
```

###
