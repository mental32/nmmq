import asyncio as _asyncio
import logging as _logging
from typing import NoReturn as _NoReturn

from . import core
from .core import Service

__author__ = 'mental'
__version__ = '0.1.1'

_logging.basicConfig(format='[%(levelname)s] %(message)s', level=_logging.INFO)  # TODO: Setup proper logging environment.

def spawn(*args, **kwargs) -> _NoReturn:
    """Start and spin a merlin client and block until it dies."""
    backend = core.backend.load(kwargs['config']['app']['backend'])

    loop = _asyncio.get_event_loop()
    client = backend.Client(loop=loop)

    _logging.info(f'Spawining client: {client!r}')

    try:
        loop.create_task(client.spawn(*args, **kwargs))
        loop.run_forever()
    except BaseException:
        if loop.is_closed():
            _logging.error(f'Eventloop is closed! `Client.shutdown` was not called.')
            return

        # TODO: Gracefully shutdown the event loop
        loop.run_until_complete(client.shutdown())
