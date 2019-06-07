import asyncio
import logging
import inspect
from merlin.core import Service

__all__ = ['TcpServer']

class TcpServer:
    _TCP_SERVER_CB = None
    _TCP_SERVER_HOST = '127.0.0.1'
    _TCP_SERVER_PORT = 1234

    @staticmethod
    def client_connected(func):
        if not callable(func):
            raise TypeError('callback must be callable!')

        elif not inspect.iscoroutinefunction(func):
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
    async def bootstrap(self):
        async def nonce(self, r, w):
            raise NotImplementedError

        callback = self._TCP_SERVER_CB or nonce

        logging.info(f'[ TCP ] Starting tcp server on {self._TCP_SERVER_HOST}:{self._TCP_SERVER_PORT}')
        server = await asyncio.start_server(callback, self._TCP_SERVER_HOST, self._TCP_SERVER_PORT)

        async with server:
            await server.serve_forever()
