import asyncio
import logging
import traceback
import sys
from contextlib import suppress
from functools import partial
from pathlib import Path
from io import BytesIO
from typing import Optional

import aiohttp
import discord
from discord.http import Route as _Route

from ... import (
    AbstractClient,
    Configuration,
    State,
    service
)

from .packet import (
    OpCode,
    Packet,
)

__all__ = ['Client']


class Client(discord.Client, AbstractClient):
    STACK_MESSAGES_ENDPOINT: str = f'{_Route.BASE}/channels/%s/messages'

    def __init__(self, *, loop=None):
        super().__init__(loop=loop)
        AbstractClient.__init__(self, loop=loop)

    def __del__(self):
        self._shutdown()

    # Staticmethods

    def _assert_configuration(self, config):
        backend = config['config']['discord']

        if 'inbound' not in backend:
            raise KeyError('Missing inbound channel.')
        else:
            backend['inbound'] = inbound = int(backend['inbound'])

        backend['outbound'] = outbound = int(str(backend.get('outbound', inbound)))

        self.__inbound = inbound
        self.__outbound = outbound

    # Properties

    @property
    def inbound(self):
        return self.get_channel(self.__inbound)

    @property
    def outbound(self):
        return self.get_channel(self.__outbound)

    # Internals

    # Shutdown mechanism

    def _shutdown(self):
        # If we're already Dead this is a nop
        if self._state is State.Dead:
            return

        loop = asyncio.new_event_loop()

        async def _inner_shutdown():
            async with aiohttp.ClientSession(loop=loop) as session:
                kwargs = {
                    'headers': {
                        'Content-Type': 'application/json',
                        'Authorization': self.http.token
                    },

                    'json': {
                        'content': Packet(self, self.outbound, author=self.hostname, op=OpCode.Dead, ttl=60).encoded_json(),
                    }
                }

                logging.info('[ DEATH ] Posting Dying packet.')
                await session.request('POST', self.STACK_MESSAGES_ENDPOINT, **kwargs)

        try:
            loop.run_until_complete(_inner_shutdown())
        except Exception:
            pass  # Don't care if we fail.
        finally:
            self._state = State.Dead
            loop.close()

    # Event handlers

    async def on_connect(self):
        self._state = State.Connected
        self.dispatch_internal('connected')

    async def on_ready(self):
        logging.info(f'[ INIT ] Begining discovery')

        alive_packet = Packet(self, self.outbound, author=self.hostname, op=OpCode.Alive, ttl=60)
        sync_packet = Packet(self, self.outbound, author=self.hostname, op=OpCode.Sync, ttl=30)

        await self._discover_task(alive_packet, sync_packet)

    async def _stream_reader_task(self, check):
        while True:
            message = await self.wait_for('message')

            if not check(message):
                continue

            try:
                packet = Packet.from_message(self, message.channel, message)
            except ValueError:
                logging.info(f'Dropping packet as it\'s read invalid: {message!r}')
            else:
                self.dispatch('packet', packet)

    # Public API

    async def send_packet(self, *, channel=None, ack_cb=None, **kwargs):
        packet = Packet(self, channel or self.outbound, author=self.hostname, **kwargs)

        if ack_cb is not None:
            async def callback(_self, recieved):
                if recieved.seq == packet.seq:
                    try:
                        with suppress(ValueError):
                            self._listeners[OpCode.Ack].remove(_self)

                        await ack_cb(recieved)
                    except Exception:
                        traceback.print_exc()

            def _(func):
                async def inner(*args, **kwargs):
                    return await func(func, *args, **kwargs)
                return inner

            self._listeners[OpCode.Ack].append(_(callback))

        await packet.send()

    async def channel_history(self, *args, **kwargs):
        check = kwargs.pop('check', lambda *_: True)

        async for message in self.inbound.history(*args, **kwargs):
            try:
                packet = Packet.from_message(self, message)
            except Exception:
                continue

            if check(packet):
                yield packet

    async def spawn(self, config):
        self._assert_configuration(config)
        self._config = _config = Configuration(config, backend='discord')

        listeners, services = service.load_from(config['app']['source'], self)

        self.services = services
        self._listeners.update(listeners)

        self.dispatch_internal('starting')

        try:
            token = _config @ 'token'
        except KeyError:
            sys.exit('backed.discord: No token found in configuration file.')

        try:
            bot = _config @ 'bot'
        except KeyError:
            bot = False

        self.loop.create_task(self._stream_reader_task(lambda m: m.channel == self.inbound))
        self.loop.create_task(self.start(token, bot=bot))

    async def shutdown(self):
        # TODO: Cancel all active tasks.

        logging.info(f'Shutting down.')

        # Shutdown discord client
        await self.close()

        try:
            # Send Dying packet.
            self._shutdown(loop=self.loop)
        except Exception:
            pass
