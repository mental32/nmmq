# NMMQ
## Not My Messaging Queue

## Index

  - [Brief](#Brief)
  - [Examples](#Examples)

## Brief

NMMQ (pronounced _enn-emm-que_) is a ZMQ inspired message queue that takes a
"parasitic" approach to hosting.

NMMQ was designed in mind to allow internet-enabled applications to communicate
without the hassle of managing system infrastructure e.g. VPS, AWS, Cloudflare.
I wrote it originally a while back when I was a broke student and didn't just
wanted to network my machines without me caring about centralized/paid hosting.

## Examples

### Discord

Lets write a small client/server example using Discord as our backend.

The code will be divided into three parts:

  - `./client.py`
  - `./server.py`
  - `./utils.py`

#### Backend

```py
import json
from typing import Any

import nmmq
from nmmq.ext.discord import DiscordBackend


class Backend(DiscordBackend):
    def serialize(self, data: Any) -> Any:
        return json.dumps(data)

    def deserialize(self, data: Any) -> Any:
        return json.loads(data)
```

#### Client

```py
import nmmq
from . import utils

backend = utils.Backend(token="TOKEN")

socket = nmmq.PullSocket(backend=backend)
socket.connect()

for message in socket:
    print(f"{message=!r}")
```

#### Server

```py
import nmmq
from . import utils

backend = Backend(token="TOKEN")

socket = nmmq.PushSocket(backend=backend)
socket.connect()

for char in "Hello, World!":
    socket.send(char)
```
