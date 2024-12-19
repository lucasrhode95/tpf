import asyncio


class EventWithTimeout(asyncio.Event):
    """
    Adds a "timeout" functionality to asyncio.Event().wait()
    """

    async def wait(self, timeout: float = None) -> bool:
        if timeout is None:
            await super().wait()
        else:
            try:
                await asyncio.wait_for(self.wait(), timeout)
            except asyncio.TimeoutError:
                pass

        return self.is_set()
