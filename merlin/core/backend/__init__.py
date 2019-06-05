import importlib
import pathlib

__all__ = ['load']
_backends = {}


def load(name: str):
    try:
        module = importlib.import_module('.{0}'.format(name), package=__name__)
    except ImportError:
        raise NotImplementedError(f'Backend not supported: {name}')
    else:
        _backends[name] = module

    return module

def load_all():
	for fp in pathlib.Path(__file__).iterdir():
		load(fp.name)
