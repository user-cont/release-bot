.PHONY: test

test:
	PYTHONPATH=$(CURDIR) pytest-3 tests/

travis:
	if [ $(TRAVIS_PYTHON_VERSION) = 3.6 ]; then PYTHONPATH=$(CURDIR) pytest tests/ --ignore tests/test_pypi_2.py; else PYTHONPATH=$(CURDIR) pytest tests/ --ignore tests/test_pypi_3.py;fi
