.PHONY: test

test:
	PYTHONPATH=$(CURDIR) pytest -v

clean:
	find . -name '*.pyc' -delete
