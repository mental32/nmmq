from .enums import OpCode


class BaseNetwork(list):
    __slots__ = ('backlog',)

    def __init__(self, *args, backlog=[], **kwargs):
        super().__init__(*args, **kwargs)
        self.backlog = backlog

    def __repr__(self):
        return f'<body: {object.__repr__(self)}, backlog: {self.backlog!r}, head: {self[-1]!r}>'

    @property
    def head(self):
        return self[-1]

    def into_raw(self):
        return {'s': self, 'b': self.backlog}

    def reset(self, data=[]):
        self.backlog = []
        self.clear()
        self.extend(data)

    def step(self, op: OpCode):
        pass
