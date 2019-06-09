from enum import IntEnum


class OpCode(IntEnum):
    """OpCodes to be used for network communication."""

    # Sending a heartbeat out into the network.
    Heartbeat = 0

    # A host is alive on the network.
    Alive = 1

    # A host is dead on the network.
    Dead = 2

    # A generic code used for any data transmission.
    Data = 3

    # A generic code used for an acknowledgement of something.
    Ack = 4

    # The code used when initializing a host.
    Hello = 5

    # The code used to sync network stacks across hosts.
    Sync = 6


class State(IntEnum):
    """States of a client."""
    Dead = 0
    Connected = 1
    Discovery = 2
    Alive = 3
    Dying = 4
