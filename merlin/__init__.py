import asyncio
import logging
from typing import NoReturn

from . import core
from .core import Service

__author__ = 'mental'
__version__ = '0.1.0'

logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)  # TODO: Setup proper logging environment.

def spawn(*args, **kwargs) -> NoReturn:
    """Start and spin a merlin client and block until it dies."""
    backend = core.backend.load(kwargs['config']['app']['backend'])

    loop = asyncio.get_event_loop()
    client = backend.Client(loop=loop)

    logging.info(f'Spawining client: {client!r}')

    try:
        loop.create_task(client.spawn(*args, **kwargs))
        loop.run_forever()
    except Exception:
        if loop.is_closed():
            logging.warn(f'Eventloop is closed! `Client.shutdown` was not called.')
            return

        # TODO: Gracefully shutdown the event loop
        loop.run_until_complete(client.shutdown())
