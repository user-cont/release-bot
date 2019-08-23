.PHONY: test

IMAGE_NAME := marusinm/release-bot
IMAGE_NAME_DEV := usercont/release-bot:dev
TEST_IMAGE_NAME := release-bot-tests

image: files/install-rpm-packages.yaml files/recipe.yaml
	docker build --rm -f Dockerfile.githubapp --tag=$(IMAGE_NAME) .

image-dev:
	docker build --tag=$(IMAGE_NAME_DEV) -f Dockerfile.dev .

image-dev-no-cache:
	docker build --no-cache --tag=$(IMAGE_NAME_DEV) -f Dockerfile.dev .

image-test:
	docker build --tag=$(TEST_IMAGE_NAME) -f Dockerfile.test .

test-in-container:
	docker run -it \
		-v $(CURDIR):/usr/src/app:Z \
		-e GITHUB_TOKEN=${GITHUB_TOKEN} \
		$(TEST_IMAGE_NAME) \
		make test TEST_TARGET='$(TEST_TARGET)'

test:
	PYTHONPATH=$(CURDIR) pytest --color=yes --verbose --showlocals $(TEST_TARGET)

clean:
	find . -name '*.pyc' -delete
