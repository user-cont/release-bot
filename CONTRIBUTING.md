# Contributing Guidelines

Thanks for your interest in contributing to `release-bot`.

The following is a set of guidelines for contributing to `release-bot`.
Use your best judgement, and feel free to propose changes to this document in a pull request.

## Reporting Bugs

Before creating bug reports, please check a [list of known issues](https://github.com/user-cont/release-bot/issues) to see if the problem has already been reported (or fixed in a master branch).

If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/user-cont/release-bot/issues/new).
Be sure to include a **descriptive title and a clear description**. Ideally, please provide:

* version of release-bot you are using (`pip freeze | grep release-bot`)

* the command you executed with output

If possible, add a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.

**Note:** If you find a **Closed** issue that seems like it is the same thing that you're experiencing, open a new issue and include a link to the original issue in the body of your new one. You can also comment on the closed issue to indicate that upstream should provide a new release with a fix.

## Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.
When you are creating an enhancement issue, **use a clear and descriptive title**
and **provide a clear description of the suggested enhancement**
in as many details as possible.

## Guidelines for Developers

If you would like to contribute code to the `release-bot` project, this section is for you!

### Is this your first contribution?

Never contributed to an open-source project before?  No problem!  We're excited that you are considering `release-bot` for your first contribution!

Please take a few minutes to read GitHub's guide on [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/).  It's a quick read, and it's a great way to introduce yourself to how things work behind the scenes in open-source projects.

### Dependencies

If you are introducing a new dependency, please make sure it's added to:
 * requirements.txt

### Documentation

We are maintaining whole project documentation inside [README.md](/README.md).

#### Changelog

When you are contributing to changelog, please follow these suggestions:

* The changelog is meant to be read by everyone. Imagine that an average user
  will read it and should understand the changes. `docker_image.mount() via .get_archive()` is
  not very descriptive. `DockerImage class now utilizes get_archive() from
  docker-py for its mount() method.` is a more friendly description.
* Every line should be a complete sentence. Either tell what is the change that the tool is doing or describe it precisely:
  * Bad: `Use search method in label regex`
  * Good: `Colin now uses search method when...`
* And finally, with the changelogs we are essentially selling our projects:
  think about a situation that you met someone at a conference and you are
  trying to convince the person to use the project and that the changelog
  should help with that.

### How to contribute code to release-bot

1. Create a fork of the `release-bot` repository.
2. Create a new branch just for the bug/feature you are working on.

   - If you want to work on multiple bugs/features, you can use branches to keep them separate, so that you can submit a separate Pull Request for each one.

3. Once you have completed your work, create a Pull Request, ensuring that it meets the requirements listed below.

### Requirements for Pull Requests

* Please create Pull Requests against the `master` branch.
* Please make sure that your code complies with [PEP8](https://www.python.org/dev/peps/pep-0008/).
* One line should not contain more than 100 characters.
* Make sure that new code is covered by a test case (new or existing one).
* We don't like [spaghetti code](https://en.wikipedia.org/wiki/Spaghetti_code).
* All the tests in the test-suite have to pass.

## Development Environment

### Requirements

Currently, the development environment can be set up on __Linux__, and __MacOS__.
We support two methods for setting up the environment.

1. Docker method (using containers)

2. Direct installation on host

We recommend new developers to use the first method.
Before beginning any of the above setups, please ensure you have installed and set up the following on your machine:

- pip3 (If performing direct installation)

- Docker (If using the docker method. [installation guide](https://docs.docker.com/install/))

- make utility

### Docker Method

#### Building a test image

Open up a terminal and go to the cloned `release-bot` git repository.
Execute the command

```
make image-test
```

It builds a Docker image using your local repository, with release-bot installed in it. This may take some time when building for the first time.

To check if the build was successful, run  `docker images`. If the build was successful, an image named `release-bot-tests` will be present in the output list.

#### Testing new changes

To test any new changes you made in the code, first build a test image using the above instructions, and then execute the following command

```
docker run -it -v ${PWD}:/home/test-user/app/ -v path/to/conf.yaml:/home/test-user/conf.yaml -e PYTHONPATH=/home/test-user/app release-bot-tests /bin/bash
```

* `path/to/conf.yaml` is the absolute path of the configuration file in your machine.

A terminal in the container will open up. Now run the bot using the command

```
release-bot -d -c conf.yaml
```

### Running the test-suite

For testing, we are using [pytest](https://docs.pytest.org/en/latest/) framework. Tests are stored in the [tests](/tests) directory. We recommend to run tests inside docker container using:

```
# execute whole test suite
make test-in-container GITHUB_TOKEN=your_github_token
```

Learn more about GitHub tokens [here](https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line).

You can also run specific tests by setting `TEST_TARGET` variable equal to test file path, for example:

```
make test-in-container TEST_TARGET=tests/test_github.py
```

__Note:__ You may need to specify your token in the above command depending on test you are running. We recommend to specify it with every test.

### Direct Installation

#### Installing dependencies

Go to the cloned `release-bot` git repository, and run the following commands in a terminal:

```
pip3 install -r requirements.txt
pip3 install -r tests/requirements.txt
```

#### Running release-bot

To run `release-bot` to test any changes made in the code, run the command:

```
python3 -m release_bot.releasebot -d -c /path/to/conf.yaml
```

#### Running the test-suite

To run the test suite, first set the `GITHUB_TOKEN` environment variable, and then run the command given below:

```
make test
```

### Cleanup after testing

We have an integration test suite in release bot which creates a new project on
github and tries the functionality in there. It may easily happen that a bunch
of test repositories will be left out in your account:

 * We have a script which is able to delete all of these, please check
   `./hack/clean-testing-github-repos`. We suggest reading out the sources
   first before using it.
 * The prerequisite for both, the integration tests and the script mentioned
   above, is to have a token which is able to delete projects.

Thank you!

release-bot team.