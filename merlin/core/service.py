import inspect
import importlib
import logging
import sys
import pathlib
import traceback
from collections import defaultdict
from typing import Callable, Dict, Optional

from .abc import OpCode


class Service:
    """Base class for a Merlin Service extension.

    Attributes
    ----------
    _client : AbstractClientInterface
        A read only attribute that refrences the client used.
    """
    def __init__(self, client):
        self.__client = client

    def __repr__(self):
        return f'<Service({self.__class__.__name__!r})>'

    @staticmethod
    def listener(type_: Optional[OpCode] = None):
        """A decorator that marks a function as an event listener."""
        if not isinstance(type_, str):
            try:
                type_ = OpCode(type_)
            except ValueError:
                if type_ is not None:
                    raise TypeError(f'Expected type `OpCode` got {type(type_)!r}')

        def wrapped(func):
            # TODO: Type check the function to make sure its a coroutine function
            func._listner_type = type_
            return func
        return wrapped

    # Properties

    @property
    def _client(self):
        return self.__client

    def listeners(self) -> Dict[OpCode, Callable]:
        data = defaultdict(list)

        for _, obj in inspect.getmembers(self):
            if hasattr(obj, '_listner_type'):
                tp = obj._listner_type

                data[tp].append(obj)

        return data


def load(path, *args, **kwargs):
    """Given a path, filter and instantiate classes that derive from `Services`."""
    def _filter(obj):
        return isinstance(obj, type) and obj is not Service and issubclass(obj, Service)

    is_file = path.is_file()

    if not is_file:
        f = lambda p: True
    else:
        _file_path = path
        path = path.parent
        f = lambda p: p == _file_path

    sys_path = str(path.absolute())

    sys.path.append(sys_path)

    listeners = defaultdict(list)
    services = {}

    for _path in filter(f, path.iterdir()):
        name = _path.name

        if _path.is_file():
            if name.count('.') > 1:
                logging.error(f'Cannot import service as it has a bad import name: {name!r}')
                continue

            name, *_ = name.rpartition('.')

        elif not path.is_dir():
            logging.error(f'Failed to load service, target is neither a file or directory: {name!r}')
            continue

        try:
            module = importlib.import_module(f'{name}')
        except ModuleNotFoundError as err:
            traceback.print_exc()
            continue

        for name, obj in inspect.getmembers(module, _filter):
            services[name] = service = obj(*args, **kwargs)

            for tp, val in service.listeners().items():
                listeners[tp].extend(val)

    if is_file:
        sys.path.remove(sys_path)

    return dict(listeners), services


def load_from(sequence, *args, **kwargs):
    """Load services from a sequence of paths.

    .. note ::
        This is equivelent to calling :func:`load` in a loop
        and collecting the results.

    Parameters
    ----------
    sequence : Sequence[pathlib.Path]
        A sequence of paths.
    """
    _listeners = defaultdict(list)
    _services = {}

    for path in sequence:
        listeners_, services = load(pathlib.Path(path).absolute(), *args, **kwargs)

        _services.update(services)

        for tp, val in listeners_.items():
            _listeners[tp].extend(val)

    return dict(_listeners), _services
