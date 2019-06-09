import asyncio
import logging
from abc import ABCMeta, abstractmethod
from collections import defaultdict as _defaultdict
from functools import reduce as _functools_reduce
from socket import gethostname as _socket_gethostname

from . import State, OpCode, BaseNetwork
from .packet import AbstractPacket


class AbstractClient(metaclass=ABCMeta):
    """An ABCMeta Mixin for anything that is a Client.

    Attributes
    ----------
    HOSTNAME : str
        The class default hostname for a client.
        this is usually the result of `socket.gethostname()`
    loop : `event loop`
        The event loop to use and run on.
    _network_stack : BaseNetwork
        The clients copy of the network map.
    _listeners : Dict[Any, List[Callable[..., Awaitable]]]
        Internal bookkeeping for listeners.
    """
    # Default hostname for a client is the system hostname.
    HOSTNAME: str = _socket_gethostname()

    def __init__(self, loop):
        self.loop = loop

        self._network_stack = BaseNetwork()
        self.__state = State.Dead
        self.__services = {}
        self._listeners = _defaultdict(list, {tp: [] for tp in (None, *OpCode)})

    def __repr__(self):
        return f'<Client: {self._state!r}>'

    # Internals

    @property
    def services(self):
        return self.__services

    @services.setter
    def services(self, val):
        self.__services = val

    @property
    def _state(self):
        return self.__state

    @_state.setter
    def _state(self, value):
        logging.info(f'{self._state!r} => {value!r}')
        self.__state = value

    @property
    def hostname(self) -> str:
        return self.HOSTNAME

    @property
    def state(self) -> State:
        return self._state

    async def _discover_task(self, alive_packet, sync_packet):
        assert self._state is not State.Discovery
        assert isinstance(alive_packet, AbstractPacket)
        assert isinstance(sync_packet, AbstractPacket)

        await alive_packet.send()

        self._state = State.Discovery

        step = (1 for _ in range(15))

        while self._state is not State.Alive:
            try:
                await asyncio.sleep(next(step))
            except StopIteration:
                break

        if self._state is State.Alive:
            return

        logging.info(f'[ INIT ] Timed out!')

        stack = self._network_stack
        backlog = stack.backlog

        if not backlog:
            stack.reset([self.hostname])
        else:
            _functools_reduce(stack.step, backlog)
            await sync_packet.send()

        self._state = State.Alive

    # Packet event handler

    async def on_packet(self, packet):
        op = packet.op

        if self._state not in (State.Alive, State.Discovery):
            # Only process packets if we are
            # Discovering or Alive.
            return

        elif self._state is State.Alive:
            for func in self._listeners[op] + self._listeners[None]:
                self.loop.create_task(func(packet))

        recipient = packet.recipient
        author = packet.author
        authored = author == self.hostname

        # Schedule a cleanup for our packet
        if authored and packet.expires:
            self.loop.create_task(packet.collect())

        # Ignore packets we send so we dont get feedback.
        # Also ignore packets not addressed to us.
        if authored or ((recipient != self.hostname) and recipient is not None):
            return

        # Here we know that the packet is:
        #  a) Not sent by us AND
        #  b) Addressed to us OR
        #    c) Addressed to `null` which is intended as a "broadcast"

        network = self._network_stack

        if self._state is State.Discovery:
            if op not in (OpCode.Hello, OpCode.Sync):
                # Drop any packet that isn't initializing
                # These could be leftovers for the last session.
                logging.info(f'[ INIT ] Discovering but found non initialzing packet: {packet!r}')
                network.backlog.append(packet)
                return

            elif op is OpCode.Sync:
                self._network_stack = NetworkStack(packet.data, [])
                logging.info(f'[ INIT ]Being force sync\'d into the network!')

            else:
                self._network_stack.from_data(packet.data, self.hostname)
                self._network_stack = NetworkStack(packet.data['s'] + [self.hostname], packet.data['b'] or network.backlog)
                logging.info(f'[ INIT ] Discovering and found initializing packet: {packet!r}')

            self._state = State.Alive

        elif op == OpCode.Alive and network.head == self.hostname:
            # We are the network stack head and we must initialize this client.
            await packet.respond(op=OpCode.Hello, data=network.into_raw(), ttl=15)

        elif op is OpCode.Dead:
            network.remove(packet.data)

        elif op in (OpCode.Heartbeat, OpCode.Hello):
            # No response, drop the packet.
            return

        else:
            logging.info(f'Unhandled OP Code: {op} for {packet!r}')

    # Public API

    def is_alive(self):
        return self._state is State.Alive

    def dispatch_internal(self, tp, *args, **kwargs):
        return [self.loop.create_task(func(*args, **kwargs)) for func in self._listeners[tp]]

    # Interface

    @abstractmethod
    def is_ready(self):
        raise NotImplementedError

    @abstractmethod
    def send_packet(self):
        raise NotImplementedError

    @abstractmethod
    async def spawn(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def shutdown(self):
        raise NotImplementedError
