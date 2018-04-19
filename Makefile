.PHONY: test

IMAGE_NAME := usercont/release-bot
IMAGE_NAME_DEV := usercont/release-bot:dev
TEST_IMAGE_NAME := release-bot-tests

image:
	docker build --tag=$(IMAGE_NAME) .

image-dev:
	docker build --tag=$(IMAGE_NAME_DEV) -f Dockerfile.dev .

image-test:
	docker build --tag=$(TEST_IMAGE_NAME) -f Dockerfile.test .

test-in-container: image-test
	docker run -it $(TEST_IMAGE_NAME)

test:
	PYTHONPATH=$(CURDIR) pytest -v

clean:
	find . -name '*.pyc' -delete
