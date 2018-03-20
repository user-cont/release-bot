.PHONY: test

test:
	PYTHONPATH=$(CURDIR) pytest-3 tests/
