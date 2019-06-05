import re
import pathlib
from setuptools import setup

with open('requirements.txt') as file:
  requirements = [line.strip() for line in file.readlines()]

with open('README.md') as file:
  long_description = file.read()

with open('merlin/__init__.py') as file:
    match = re.search(r"((\d\.){2,5}\d)", file.read(), re.MULTILINE)

    if match is None:
        raise RuntimeError('Version could not be found.')

    version = match[0]

path = pathlib.Path('.').absolute().joinpath('merlin/core/backend')
backends = ['merlin.core.backend.{0}'.format(path.name) for path in filter((lambda f: f.is_dir()), path.iterdir())]

ext_path = pathlib.Path('.').absolute().joinpath('merlin/ext')
extensions = ['merlin.ext.{0}'.format(path.name) for path in filter((lambda f: f.is_dir()), ext_path.iterdir())]

packages = [
    'merlin',
    'merlin.core',
    'merlin.core.backend',
    'merlin.core.tcp',
    *extensions
]

classifiers = [
    'Intended Audience :: Developers',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Topic :: Internet',
]

kwargs = {
    'version': version,
    'packages': [*packages, *backends],
    'install_requires': requirements,
    'long_description': long_description,
    'classifiers': classifiers
}

setup(name='Merlin',
      author='mental',
      url='https://github.com/mental32/merlin',
      license='MIT',
      description='The client application that lets you build virtual networks and deploy services over them.',
      entry_points = {'console_scripts': ['merlin = merlin.__main__:main']},
      include_package_data=True,
      python_requires='>=3.5',
      **kwargs
)
