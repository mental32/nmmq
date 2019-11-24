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
        """A decorator that marks a function as an event listener.

        Parameters
        ----------
        type_ : Optional[Union[OpCode, str]]
            Either a specific OpCode to listen for
            Or a specific broadcast with a string (e.g. `"starting"`)

        Raises
        ------
        TypeError
            Raised when an invalid type to listen for was passed in.
            Or when a coroutine function wasn't passed into the returned decorator.

        Returns
        -------
        decorator : Callable[Callable[..., Awaitable]]
            A passive decorator that takes a coroutine function
            and marks it by setting a `_listener_type` attribute
            to the type passed in.
        """
        if not isinstance(type_, str):
            try:
                type_ = OpCode(type_)
            except ValueError:
                if type_ is not None:
                    raise TypeError(f'Expected type `OpCode` got {type(type_)!r}')

        def wrapped(func):
            if not inspect.iscoroutinefunction(func):
                raise TypeError('`func` must be a coroutine function!')

            func._listner_type = type_
            return func
        return wrapped

    # Properties

    @property
    def _client(self):
        return self.__client

    def listeners(self) -> Dict[OpCode, Callable]:
        """Inspect a service instance for its listeners.

        Returns
        -------
        listeners : Dict[Union[OpCode, str, None], Callable]
            A :class:`dict` of all the listeners marked on this
            instance.
        """
        data = defaultdict(list)

        for _, obj in filter((lambda obj: hasattr(obj, '_listner_type')), inspect.getmembers(self)):
            data[obj._listner_type].append(obj)

        return dict(data)


def load(path, *args, **kwargs) -> Tuple[Dict[Union[OpCode, str, None], Callable], Dict[str, Service]]:
    r"""Given a path, filter and instantiate classes that derive from `Services`.

    Parameters
    ----------
    \*args
        The args to pass when instanciating a Service.
    \*\*kwargs
        The kwargs to pass when instanciating a Service.

    Returns
    -------
    data : Tuple[Dict[Union[OpCode, str, None], Callable], Dict[str, Service]]
        A tuple of the listeners and services respectively.
    """
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


def load_from(sequence, *args, **kwargs) -> Tuple[Dict[Union[OpCode, str, None], Callable], Dict[str, Service]]:
    r"""Load services from a sequence of paths.

    .. note ::
        This is equivelent to calling :func:`load` in a loop
        and collecting the results.

    Parameters
    ----------
    sequence : Sequence[pathlib.Path]
        A sequence of paths.
    \*args
        The args to pass when instanciating a Service.
    \*\*kwargs
        The kwargs to pass when instanciating a Service.

    Returns
    -------
    data : Tuple[Dict[Union[OpCode, str, None], Callable], Dict[str, Service]]
        A tuple of the listeners and services respectively.
    """
    _listeners = defaultdict(list)
    _services = {}

    for path in sequence:
        listeners_, services = load(pathlib.Path(path).absolute(), *args, **kwargs)

        _services.update(services)

        for tp, val in listeners_.items():
            _listeners[tp].extend(val)

    return dict(_listeners), _services
