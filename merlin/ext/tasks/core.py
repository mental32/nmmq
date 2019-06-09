import asyncio
import inspect
import logging
import traceback
from contextlib import suppress

log = logging.getLogger(__name__)

MAX_ASYNCIO_SECONDS = 3456000

class Task:
    """asyncio.Task but for humans.

    .. _event loop: https://docs.python.org/3/library/asyncio-eventloops.html

    ```
    import asyncio

    from merlin.ext.tasks import Task

    @Task(seconds=10)
    async def some_task(n)
        await asyncio.sleep(n)
        print(f'Slept for {n}!')

    some_task.start(3)
    some_task.loop.run_forever()
    ```

    Attributes
    ----------
    seconds : Optional[int]
        The amount of seconds specified.
    hours : Optional[int]
        The amount of hours specified.
    minutes : Optional[int]
        The amount of minutes specified.
    loop : Optional[event loop]
        The event loop to run the task on.
        If left unspecified the `asyncio.get_event_loop()` will be used.
    coro : Callable[..., Awaitable]
        The coroutine function to run.
    """
    def __init__(self, seconds=0, hours=0, minutes=0, count=None, loop=None):
        if count is not None and count <= 0:
            raise ValueError('count must be greater than 0 or None.')
        else:
            self.count = count

        self.seconds = seconds
        self.hours = hours
        self.minutes = minutes

        sleep = seconds + (minutes * 60.0) + (hours * 3600.0)

        if sleep >= MAX_ASYNCIO_SECONDS:
            fmt = 'Total number of seconds exceeds asyncio imposed limit of {0} seconds.'
            raise ValueError(fmt.format(MAX_ASYNCIO_SECONDS))

        elif sleep < 0:
            raise ValueError('Total number of seconds cannot be less than zero.')

        else:
            self._sleep = sleep

        self.loop = loop or asyncio.get_event_loop()
        self.coro = None
        self._current_loop = 0
        self._task = None
        self._injected = None
        self._before_loop = None
        self._after_loop = None
        self._is_being_cancelled = False
        self._has_failed = False
        self._stop_next_iteration = False

    def __get__(self, obj, objtype):
        if obj is not None:
            self._injected = obj

        return self

    def __call__(self, coro):
        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'Expected coroutine function, received {type(coro).__name__!r}.')
        else:
            self.coro = coro

        return self

    # Properties

    @property
    def is_being_cancelled(self):
        """:class:`bool`: Whether the task is being cancelled."""
        return self._is_being_cancelled

    @property
    def failed(self):
        """:class:`bool`: Whether the internal task has failed."""
        return self._has_failed

    @property
    def current_loop(self):
        """:class:`int`: The current iteration of the loop."""
        return self._current_loop

    @property
    def task(self):
        """Optional[:class:`asyncio.Task`]: Fetches the internal task or ``None`` if there isn't one running."""
        return self._task

    # Private

    @property
    def _can_be_cancelled(self):
        return not self._is_being_cancelled and self._task and not self._task.done()

    async def _loop(self, *args, **kwargs):
        async def _get_loop_function(self, name):
            coro = getattr(self, '_' + name)
            if coro is None:
                return

            if self._injected is not None:
                return await coro(self._injected)
            else:
                return await coro()

        with suppress(Exception):
            await _get_loop_function('before_loop')

        try:
            while True:
                await self.coro(*args, **kwargs)

                if self._stop_next_iteration:
                    return

                self._current_loop += 1
                if self._current_loop == self.count:
                    break

                await asyncio.sleep(self._sleep)

        except asyncio.CancelledError:
            self._is_being_cancelled = True
            raise

        except Exception as err:
            traceback.print_exc()
            self._has_failed = True
            log.exception('Internal background task failed.')
            raise

        finally:
            with suppress(Exception):
                await _get_loop_function('after_loop')

            self._is_being_cancelled = False
            self._current_loop = 0
            self._stop_next_iteration = False
            self._has_failed = False

    # Public

    def start(self, *args, **kwargs):
        r"""Starts the internal task in the event loop.

        Parameters
        ------------
        \*args
            The arguments to to use.
        \*\*kwargs
            The keyword arguments to use.

        Raises
        --------
        RuntimeError
            A task has already been launched and is running.

        Returns
        ---------
        :class:`asyncio.Task`
            The task that has been created.
        """
        if self._task is not None and not self._task.done():
            raise RuntimeError('Task is already launched and is not completed.')

        elif self._injected is not None:
            args = (self._injected, *args)

        self._task = task = self.loop.create_task(self._loop(*args, **kwargs))

        return task

    def stop(self):
        r"""Gracefully stops the task from running.

        Unlike :meth:`cancel`\, this allows the task to finish its
        current iteration before gracefully exiting.

        .. note::

            If the internal function raises an error that can be
            handled before finishing then it will retry until
            it succeeds.

            If this is undesirable, either remove the error handling
            use :meth:`cancel` instead.
        """
        if self._task and not self._task.done():
            self._stop_next_iteration = True

    def cancel(self):
        """Cancels the internal task, if it is running."""
        if self._can_be_cancelled:
            self._task.cancel()

    def restart(self, *args, **kwargs):
        r"""A convenience method to restart the internal task.

        .. note::

            Due to the way this function works, the task is not
            returned like :meth:`start`.

        Parameters
        ------------
        \*args
            The arguments to to use.
        \*\*kwargs
            The keyword arguments to use.
        """
        def restart_when_over(fut, *, args=args, kwargs=kwargs):
            self._task.remove_done_callback(restart_when_over)
            self.start(*args, **kwargs)

        if self._can_be_cancelled:
            self._task.add_done_callback(restart_when_over)
            self._task.cancel()

    # Decorators

    def before_loop(self, coro):
        """A decorator that registers a coroutine to be called before the loop starts running.

        The coroutine must take no arguments (except ``self`` in a class context).

        Parameters
        ------------
        coro: :ref:`coroutine <coroutine>`
            The coroutine to register before the loop runs.

        Raises
        -------
        TypeError
            The function was not a coroutine.
        """
        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'Expected coroutine function, received {type(coro).__name__!r}.')

        self._before_loop = coro
        return coro

    def after_loop(self, coro):
        """A decorator that register a coroutine to be called after the loop finished running.

        The coroutine must take no arguments (except ``self`` in a class context).

        .. note::

            This coroutine is called even during cancellation. If it is desirable
            to tell apart whether something was cancelled or not, check to see
            whether :meth:`is_being_cancelled` is ``True`` or not.

        Parameters
        ------------
        coro: :ref:`coroutine <coroutine>`
            The coroutine to register after the loop finishes.

        Raises
        -------
        TypeError
            The function was not a coroutine.
        """
        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'Expected coroutine function, received {type(coro).__name__!r}.')

        self._after_loop = coro
        return coro
