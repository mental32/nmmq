#!/usr/bin/make -f

install:
	@python -m pip install --user -r requirements.txt

flake:
	-@flake8 merlin
