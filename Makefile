.PHONY: test

test:
	PYTHONPATH=$(CURDIR) pytest-3 tests/

clean:
	find . -name '*.pyc' -delete
