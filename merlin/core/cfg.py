from typing import Any

class Configuration(dict):
    """Configuration file wrapper class.

    .. note :: 

        This is essentially an enhanced :class:`dict` 
        focused on fetching configuration settings.

    Attributes
    ----------
    backend : str
        The name of the default backend being used.
    """
    def __init__(self, *args, backend, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = backend

    def __matmul__(self, key):
        """Operator for :meth:`search`."""
        return self.search(key)

    def search(self, key: Any, *, backend=None) -> Any:
        """A lookup that searches a backends settings before the shared settings.

        Parameters
        ----------
        key : Any
            The key to look for.
        backend : Optional[str]
            The name of the backend configuration
            to search.

        Raises
        ------
        KeyError
            Raised when the lookup fails.

        Returns
        -------
        value : Any
            The data associated with the key.
        """
        data = self.get('config', {})

        try:
            return data.get(backend or self.backend, {})[key]
        except KeyError:
            return data[key]
