import importlib
import pathlib

__all__ = ['load']
_backends = {}


def load(name: str):
	"""give a name; load it's backend

	.. note ::
		Memoization occurs so calling twice
		with the same name will yield a cached
		value.

	Parameters
	----------
	name : str
		The name of the backend to load.

	Returns
	-------
	module : :obj:`module`
		The backends module.
	"""
	if name in _backends:
		return _backends[name]

    try:
        module = importlib.import_module('.{0}'.format(name), package=__name__)
    except ImportError:
        raise NotImplementedError(f'Backend not supported: {name}')
    else:
        _backends[name] = module

    return module

def load_all():
	"""Iterates through all backends and loads them individually."""
	for fp in pathlib.Path(__file__).iterdir():
		load(fp.name)
