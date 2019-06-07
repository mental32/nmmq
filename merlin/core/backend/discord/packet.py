import asyncio
import logging
import socket
import time
import traceback
import json
from typing import Any

from ...abc import AbstractPacket, OpCode

__all__ = ['OpCode', 'Packet', 'HeartbeatPacket', 'DyingPacket', 'AlivePacket']


class Packet(AbstractPacket):
    __slots__ = ('author', 'recipient', 'op', 'data', 'ttl', 'timestamp', 'snowflake', '__client', '_message', '__collected')

    def __init__(self, client, channel, **kwargs):
        self.snowflake = kwargs.pop('snowflake', None)

        super().__init__(**kwargs)

        self.__collected = False
        self.__client = client
        self._channel = channel
        self._message = None        

    # Constructors

    @classmethod
    def from_message(cls, client, channel, message):

        content = message.content[8:-3]
        content_length = len(content)

        if content_length < 13:
            raise ValueError('Message content was less than 13 characters, raising as invalid.')

        payload = json.loads(content)

        kwargs = {
            'author': payload['f'],
            'op': payload['op'],
            'snowflake': message.id,
            'recipient': payload['t'],
            'data': payload['d'],
            'ttl': payload['ttl'],
            'timestamp': payload['ts'],
            'seq': payload['s']
        }

        klass = cls(client, channel, **kwargs)
        klass._message = message

        return klass

    # Properties

    @property
    def channel(self):
        return self._channel

    @property
    def expires(self):
        return self.ttl is not None

    @property
    def expired(self):
        return self.expires and time.time() >= (self.ttl + self.timestamp)

    @property
    def payload(self):
        return {
            'op': self.op.value,         # Op code for the packet, uint
            'd': self.data,              # Data sent with the packet, Any
            'f': self.author,            # Hostname of the sending machine, String
            't': self.recipient,         # Hostname of the recipient, String
            'ts': f'{int(time.time())}', # Timestamp of when the packet was crafted/sent, size_t
            'ttl': self.ttl,             # Amount of time in seconds when the packet should be considered "expired", uint
            's': self.seq                # Sequence number of the packet, uint
        }

    def json(self) -> str:
        return json.dumps(self.payload)

    def encoded_json(self) -> str:
        return f'```json\n{self.json()}```'

    async def send(self):
        try:
            self._message = message = await self.channel.send(self.encoded_json())
        except Exception as error:
            traceback.print_exc()
            self.__client.dispatch('error', error)
        else:
            return message

    def response(self, op: OpCode, data: Any = None, ttl: int = None, *, author: str = socket.gethostname()):

        kwargs = {
            'author': author,
            'op': op,
            'recipient': self.author,
            'data': data,
            'ttl': ttl,
        }

        return Packet(self.__client, self._channel, **kwargs)

    async def respond(self, *args, **kwargs):
        return await self.response(*args, **kwargs).send()

    async def delete(self):
        return await self._message.delete()

    async def collect(self):
        if self.__collected:
            return
        else:
            self.__collected = True

        if self.ttl is not None:
            dead_at = (self.timestamp + self.ttl)

            while time.time() <= dead_at:
                await asyncio.sleep(int(dead_at - time.time()))

        try:
            await self._message.delete()
        except Exception as error:
            logging.info(f'Failed to clean up {self!r} ({error!r})')

    async def ack(self, data):
        return await Packet(self.__client, self._channel, op=OpCode.Ack, seq=self.seq, author=self.__client.hostname, recipient=self.author, data=data).send()
