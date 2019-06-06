from abc import ABCMeta, abstractmethod
from itertools import count as itertools_count
from typing import Any

from .enums import OpCode


class AbstractPacket(metaclass=ABCMeta):
    sequence_number = (i for i in itertools_count())

    def __init__(self, *,  
            op: OpCode, 
            author: str = None, 
            data: Any = None, 
            recipient: str = None, 
            ttl: int = None, 
            timestamp: str = None,
            seq: int = None):
        self.seq = seq or next(AbstractPacket.sequence_number)
        self._message = None

        if not isinstance(op, (OpCode, int)):
            raise TypeError

        self.op = OpCode(op)
        self.author = author
        self.data = data
        self.recipient = recipient
        self.ttl = ttl
        self.timestamp = int(timestamp or 0)

    def __repr__(self):
        return f'<Packet: FROM={self.author!r}, OPCODE={self.op!r}, DATA={self.data!r}%s>' % (f', TIMESTAMP={self.timestamp}' if self.timestamp else '')

    def __str__(self):
        return self.json()

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
    @abstractmethod
    def payload(self):
        raise NotImplementedError

    # Methods

    @abstractmethod
    async def respond(self):
        raise NotImplementedError

    @abstractmethod
    def json(self):
        raise NotImplementedError
