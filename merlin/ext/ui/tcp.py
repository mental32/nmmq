import asyncio
import logging
import inspect
from merlin.core import Service

__all__ = ['TcpServer']


class TcpServer:
    """Base class for a raw TCP Server.

    User code should inherit from this class in
    order to make use of the TCP server.

    ```
    class Echo(Service, TcpServer)
        \"\"\"An echo server implementation.\"\"\"

        @TcpServer.client_connected
        async def callback(self, reader, writer):
            while True:
                data = await reader.read(1)
                writer.write(data)
                await writer.drain()
    ```
    """
    _TCP_SERVER_CB = None
    _TCP_SERVER_HOST = '127.0.0.1'
    _TCP_SERVER_PORT = 1234

    @staticmethod
    def client_connected(func):
        """A decorator to mark the callback for the server to use.

        .. note ::
            This function marks the callback by setting
            a `__tcp__entry__` attribute to `True`

        Parameters
        ----------
        func : Callable[..., Awaitable]
            The function to mark as the callback function.
            This must be a coroutine function.

        Raises
        ------
        TypeError
            If a coroutine function was not supplied
            a `TypeError` will be raised.
        """
        if not inspect.iscoroutinefunction(func):
            raise TypeError('callback must be a coroutine function!')
        else:
            func.__tcp_entry__ = True
            return func

    def __init_subclass__(cls):
        for _, obj in inspect.getmembers(cls):
            if getattr(obj, '__tcp_entry__', False):
                cls._TCP_SERVER_CB = obj
                return

    @Service.listener('starting')
    async def __tcp_bootstrap(self):
        async def nonce(self, r, w):
            raise NotImplementedError

        callback = self._TCP_SERVER_CB or nonce

        logging.info(f'[ TCP ] Starting tcp server on {self._TCP_SERVER_HOST}:{self._TCP_SERVER_PORT}')
        server = await asyncio.start_server(callback, self._TCP_SERVER_HOST, self._TCP_SERVER_PORT)

        async with server:
            await server.serve_forever()
