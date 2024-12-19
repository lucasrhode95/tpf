# README #
Package with different reusable Python methods for managing the execution flow of backend applications.

It contains

- An [App Manager](./app_manager.py) abstract class that developers can extend to get a wrapper that managers the setup, execution and cleanup of an app (works well with Dockerized apps!)

- An [App Settings](./app_settings.py) class to read `.ini` files, enabling developers to separate app configuration from code

- A [RabbitMQ lib](./rabbitmq) that enables developers to easily publish and subscribe messages to a RabbitMQ broker using an asynchronous lib

- A [Redis connection manager](./redis) to ease the pub/sub process in redis

### Who do I talk to? ###
* Main developer: [rhode.lucasb@gmail.com](mailto:rhode.lucasb@gmail.com)
