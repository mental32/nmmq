#!/usr/bin/python3

import sys

assert sys.version_info[:2], 'fatal: python3.6+ required'  # noqa

import os
import argparse
import tempfile
import shutil
import pathlib
import traceback
import logging
import itertools
from subprocess import check_output as _check_output

import click
import toml
from click import UsageError

from .core.tcp import serve as _tcp_serve
from . import spawn

def _resolve(string: str, *, is_dir: bool = True) -> pathlib.Path:
    """Resolve a string to a filepath on disk"""
    if '://' in string:
        protocol = string[:string.index('://')]

        if not protocol:
            raise ValueError(f'`protocol` could not be parsed for {string}')

        elif string.startswith('git+'):
            protocol = 'git'
            string = string[4:]

        dst = tempfile.mkdtemp() if is_dir else tempfile.mkftemp()

        if protocol == 'git':
            _check_output(f'git clone {string} {dst}', shell=True)

        elif protocol in ('http', 'https'):
            _check_output(f'wget {"-R" if is_dir else ""} -P {dst} {string}', shell=True)

        string = dst

    path = pathlib.Path(string)

    if not path.exists():
        raise FileNotFoundError

    return path

def _resolve_config(string: str) -> dict:
    path = _resolve(string, is_dir=False)

    with open(str(path.absolute())) as file:
        return toml.load(file), path

def _assert_configuration(config: dict) -> None:
    """Give a dictionary configuration assert that it satisfies the bare requirements.

    .. note ::
        This function also mutates the configuration.
    """
    if not isinstance(config, dict):
        raise TypeError('configuration is not a dict')

    if 'config' not in config:
        config['config'] = {}

    if 'source' not in config:
        config['app']['source'] = []

    if 'backend' not in config['app']:
        raise KeyError('`backend` not specified in app config')

    backend = config['app']['backend']

    if not isinstance(backend, str):
        raise TypeError

    elif not backend:
        raise ValueError

@click.command(name='merlin')
@click.argument('sources', nargs=-1)
@click.option('-c', '--config', default=None)
@click.option('-s', '--serve', '--server', is_flag=True, default=False)
def main(sources, config, serve):
    if not sources and config is None:
        raise UsageError('Either source or config must be supplied')

    if sources:
        sources = [_resolve(path) for path in sources]

    if config is None:
        for source in sources:
            path = source / 'merlin.toml'

            if path.exists():
                break
        else:
            raise sys.exit(f'Could not find a configuration file in any of the sources.')

        cfg_path = path

        with open(str(path.absolute())) as file:
            config = toml.load(file)
    else:
        config, cfg_path = _resolve_config(config)

    try:
        _assert_configuration(config)
    except Exception as err:
        sys.exit(err)
    else:
        _cfg_sources = config['app']['source']

    if isinstance(_cfg_sources, str):
        cfg_sources = [_resolve(path).absolute()]

    elif isinstance(_cfg_sources, list):
        cfg_sources = [_resolve(path).absolute() for path in _cfg_sources]

    sources = (source.absolute() for source in itertools.chain(sources, cfg_sources))
    resolved = []

    for source in sources:
        if source.exists():
            resolved.append(source)
        else:
            logging.warning(f'Source path does not exist: "{source}"')

    config['app']['source'] = resolved

    try:
        if serve:
            _tcp_serve(config)
        else:
            spawn(config=config)
    except Exception as err:
        traceback.print_exc()
        sys.exit(err)
    finally:
        if source.exists() and source.parent.name == 'tmp':
            shutil.rmtree(str(source.absolute()))

if __name__ == '__main__':
    main(prog_name='Merlin')
