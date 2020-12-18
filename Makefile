.PHONY: test

IMAGE_NAME := usercont/release-bot
IMAGE_NAME_DEV := usercont/release-bot:dev
TEST_IMAGE_NAME := release-bot-tests

image: files/install-rpm-packages.yaml files/recipe.yaml
	docker build --rm -f Dockerfile.app --tag=$(IMAGE_NAME) .

image-test:
	docker build --tag=$(TEST_IMAGE_NAME) -f Dockerfile.test .

test-in-container:
	docker run -it \
		-v $(CURDIR)/release_bot:/usr/local/lib/python3.9/site-packages/release_bot:Z \
		-v $(CURDIR)/tests:/home/test-user/tests:Z \
		-e GITHUB_TOKEN=${GITHUB_TOKEN} \
		$(TEST_IMAGE_NAME) \
		make test TEST_TARGET='$(TEST_TARGET)'

test:
	PYTHONPATH=$(CURDIR) pytest --color=yes --verbose --showlocals $(TEST_TARGET)

clean:
	find . -name '*.pyc' -delete
