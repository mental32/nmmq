from typing import Any

class Configuration(dict):
    """Configuration file wrapper class."""
    def __init__(self, *args, backend, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = backend

    def __matmul__(self, key):
        """Alias for Configuration.fallback_lookup."""
        return self.search(key)

    def search(self, key: Any, *, backend=None) -> Any:
        """A lookup that searches a backends settings before the shared settings"""
        data = self.get('config', {})

        try:
            return data.get(backend or self.backend, {})[key]
        except KeyError:
            return data[key]

    def write_back(self):
        """Write the current configuration back to its file."""
        raise NotImplementedError
