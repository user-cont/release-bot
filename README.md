# Release bot [![Build Status](https://travis-ci.org/user-cont/release-bot.svg?branch=master)](https://travis-ci.org/user-cont/release-bot) [![PyPI version](https://badge.fury.io/py/release-bot.svg)](https://badge.fury.io/py/release-bot) [![Build Status](https://ci.centos.org/job/release-bot-push/badge/icon)](https://ci.centos.org/job/release-bot-push/)

Automate releases on Github and PyPi.

## Description

This is a bot that helps maintainers deliver their software to users. It is meant to watch github repositories for
release pull requests. The PR must be named in one of the following formats:
* `0.1.0 release` if you want to create the "0.1.0" upstream release
* `new major release`, release-bot would then initiate a release from e.g. "1.2.3" to "2.0.0"
* `new minor release` e.g. "1.2.3" to "1.3.0"
* `new patch release` e.g. "1.2.3" to "1.2.4"

Release-bot now works with [SemVer](https://semver.org/) only.
Once the PR is merged, bot will create a new Github release and a PyPi release respectively.
Changelog will be pulled from root of the
repository and must be named `CHANGELOG.md`. Changelog for the new
version must begin with version heading, i.e `# 0.1.0`.
Everything between this heading and the heading for previous version will be pulled into the changelog.

Alternatively, you can let the bot do the boring work, update `__version__`
variable and fill changelog with commit messages from git log.
You can trigger this action by creating an issue and name it the same as you would do for a release PR, e.g. `0.1.0 release`, `new major release`, `new minor release`, `new patch release`.
All you have to do after that is merge the PR that the bot will make.

The bot works with
[pypa/setuptools_scm](https://github.com/pypa/setuptools_scm/) plugin. If
you're using it, you don't need to care about `__version__` at all. You can be
also sure that the bot will make the PyPI release correctly — before it
releases the software, it checks out the tag in the git repo.

A `release-conf.yaml` file is required. See [Configuration](#configuration) section for details.

Once a Github release is complete, bot will upload this release to PyPI.
Note that you have to setup your login details (see [Requirements](#requirements)).

## Try it locally
```
$ pip install release-bot
```
Other possible installations are through
[Docker](#docker-image), [OpenShift](#openshift-template), [Arch User Repository](#arch-user-repository).

First interaction with release bot may be automated releases on Github. Let's do it.

#### 1. Create upstream repository or use existing one
This is meant to be upstream repository where new releases will be published.

Within upstream repository create `release-conf.yaml` file which contains info on how to release the specific project.
Copy and edit [release-conf.yaml](release-conf-example.yaml).

At the end of `release-conf.yaml` add this line of code:
```yaml
# whether to allow bot to make PRs based on issues
trigger_on_issue: true
```
For possible advanced setup check [the documentation for an upstream repository](#upstream-repository).

#### 2. Create `conf.yaml`

Create configuration file `conf.yaml`. You can use [one](conf.yaml) from this repository. You will need to generate a [Github personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/).
Recommended permissions for access token are: `repo`, `delete_repo`, `user`.

At the end of `conf.yaml` add this line of code:
```yaml
# Name of the account that the github_token belongs to
# Only needed for triggering the bot on an issue.
github_username: <your_github_username>
```
**Note**: This file **should not** be stored in upstream repository as it contains sensitive data.

For possible advanced setup check [the documentation for a private repository](#private-repository).
Also, see [requirements](#requirements) in case you want include PyPi releases.

#### 3. Run release-bot
At this point, release-bot is installed. At least two configuration files are set `release-conf.yaml` and `conf.yaml` (optionally `.pypirc`).

 Launch bot by a command:
```$ release-bot -c <path_to_conf.yaml> --debug```
You can scroll down and see debug information of running bot.

#### 4. Make a new release
- Create an issue having `0.0.1 release` as a title in your upstream repository. You can select your own version numbers.
- Wait for the bot to make a new PR based on this issue (refresh interval is set in `conf.yaml`).
- Once the PR is merged bot will make a new release.
- Check release page of your upstream repository at GitHub and you should see new release `0.0.1`.

Since now, feel free to create releases automatically just by creating issues.

# Documentation

## Configuration
There are two yaml configuration files:
 1. `conf.yaml` -- a config for the bot itself with some sensitive data (recommended to store in private repo)
 2. `release-conf.yaml` -- stored in upstream repository and contains info on how to release the specific project.


## Private repository
You need to setup a git repository, where you'll store  the `conf.yaml` and `.pypirc` files.
If this is not a local repository, make sure it's private so you prevent any private info leaking out.
If the path to `conf.yaml` is not passed to bot with `-c/--configuration`,
bot will try to find it in current working directory.

Here are the `conf.yaml` configuration options:

| Option                       | Description       | Required      |
|------------------------------|-------------------|---------------|
| `repository_name`            | Name of your Github repository | Yes |
| `repository_owner`           | Owner of the repository | Yes |
| `github_token`               | [Github personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/) | Yes |
| `github_username`            | Name of the account that the `github_token` belongs to. Only needed for triggering the bot on an issue. | No |
| `github_app_installation_id` | Installation ID (a number) of the Github app. | No |
| `github_app_id`              | ID (a number) of the Github app. | No |
| `github_app_cert_path`       | Path to a certificate which Github provides as an auth mechanism for Github apps. | No |
| `refresh_interval`           | Time in seconds between checks on repository. Default is 180 | No |
| `clone_url`                  | URL used to clone your Github repository. By default, `https` variant is used. | No |

Sample config named [conf.yaml](conf.yaml) can be found in this repository.

Regarding `github_token`, it's usually a good idea to create a Github account for the bot
(and use its Github API token)
so you can keep track of what changes were made by bot and what are your own.

You can also create a Github app and use it as an authentication mechanism for
the bot. For that you need to specify the three config values prefixed with
`github_app`.

**Note:** If the Upstream repository is a [Private Github repository](https://help.github.com/en/articles/setting-repository-visibility#about-repository-visibility), it is required to specify the SSH URL
of the repository as the `clone_url` option in `conf.yaml`. This will allow the bot to authenticate using SSH, when fetching from the Upstream repository.

## Upstream repository

You also have to have a `release-conf.yaml` file in the root of your upstream project repository.
Here are possible options:

| Option        | Meaning       | Required      |
|---------------|---------------|---------------|
| `changelog`   | List of changelog entries. If empty, changelog defaults to `$version release` | No |
| `author_name`	| Author name for changelog. If not set, author of the merge commit is used	    | No |
| `author_email`| Author email for changelog. If not set, author of the merge commit is used	| No |
| `pypi`        | Whether to release on pypi. True by default | No |
| `pypi_project`| Name of your PyPI repository | No |
| `trigger_on_issue`| Whether to allow bot to make PRs based on issues. False by default. | No |
| `labels`      | List of labels that bot will put on issues and PRs | No |

Sample config named [release-conf-example.yaml](release-conf-example.yaml) can be found in this repository.

## Requirements
Are specified in `requirements.txt`.
You have to setup your PyPI login details in `$HOME/.pypirc` as described in
[PyPI documentation](https://packaging.python.org/tutorials/distributing-packages/#create-an-account).

## Docker image
To make it easier to run this, release-bot is available as an
 [source-to-image](https://github.com/openshift/source-to-image) builder image.

 You can then create the final image like this:
```
$ s2i build $CONFIGURATION_REPOSITORY_URL usercont/release-bot app-name
```

where $CONFIGURATION_REPOSITORY_URL is link to repository with conf.yaml and .pypirc files.

To test it locally, you can the run the final image like this:

```
$ docker run <app-name>
```

once all changes, configuration files exist in GitHub and git repository contains needed files,
you can try to create an issue  in your GitHub repository with string like "X.Y.Z release"
and you can see log like this:
```
$ docker run meta-test-family-bot
---> Setting up ssh key...
Agent pid 12
Identity added: ./.ssh/id_rsa (./.ssh/id_rsa)
11:47:36.212 configuration.py  DEBUG  Loaded configuration for fedora-modularity/meta-test-family
11:47:36.212 releasebot.py     INFO   release-bot v0.4.1 reporting for duty!
11:47:36.212 github.py         DEBUG  Fetching release-conf.yaml
11:47:51.636 releasebot.py     DEBUG  No merged release PR found
11:47:52.196 releasebot.py     INFO   Found new release issue with version: 0.8.4
11:47:55.578 releasebot.py     DEBUG  No more open issues found
11:47:56.098 releasebot.py     INFO   Making a new PR for release of version 0.8.5 based on an issue.
11:47:57.608 utils.py          DEBUG  ['git', 'clone', 'https://github.com/fedora-modularity/meta-test-family.git', '.']
...
```
## OpenShift template
You can also run this bot in OpenShift using [openshift-template.yml](openshift-template.yml) in this repository.
You must set two environment variables, the `$APP_NAME` is the name of your release-bot deployment,
and `$CONFIGURATION_REPOSITORY` which contains configuration for the release-bot.
The contents of the repository are described [above](#docker-image).
Note that if you use private repository (which you **absolutely** should),
you will need to set up a new [OpenShift secret](https://docs.openshift.com/container-platform/3.7/dev_guide/secrets.html) named
`release-bot-secret` to authenticate. It can be a ssh private key that you can use to access the repository
(for GitHub see [deploy keys](https://developer.github.com/v3/guides/managing-deploy-keys/)).
Here's an [guide](https://blog.openshift.com/deploy-private-git-repositories/) on
how to do that in OpenShift GUI, or another
[guide](https://blog.openshift.com/deploying-from-private-git-repositories/)
that uses `oc` commandline tool.

By default, the release-bot builder image won't update itself when a
new version of this image is pushed to docker hub.
You can change it by uncommenting lines with `#importPolicy:`
and `#scheduled: true` in [openshift-template.yml](openshift-template.yml).
Then the image will be pulled on a new release.

## Arch User Repository
For Arch or Arch based Linux distributions, you can install the bot from the [AUR Package](https://aur.archlinux.org/packages/release-bot).
You can use your favourite AUR Helper to install the package. For instance:
```
$ aurman -S release-bot
```
You can also install it by using the [PKGBUILD](https://aur.archlinux.org/cgit/aur.git/tree/PKGBUILD?h=release-bot) from the AUR repository.
To build the package, download the PKGBUILD and exectute:
```
$ makepkg -cs #c flag cleans the extra remaining source and compiled files. s flag installs the dependencies if you don't have it. 
```
To install the package execute,
```
$ sudo pacman -U release-bot-...tar.xz
```


# Contributing

If you are interested in making contribution to release-bot project, please read [Contribution guide](/CONTRIBUTING.md) for more information.
