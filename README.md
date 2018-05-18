Release bot [![Build Status](https://travis-ci.org/user-cont/release-bot.svg?branch=master)](https://travis-ci.org/user-cont/release-bot) [![PyPI version](https://badge.fury.io/py/release-bot.svg)](https://badge.fury.io/py/release-bot)
============
This is a bot that helps maintainers deliver their software to users. It is meant to watch github repositories for
release pull requests. The PR must be named in this format `0.1.0 release`. No other format is supported yet.
Once the PR is merged, bot will create a new Github release. Changelog will be pulled from root of the
repository and must be named `CHANGELOG.md`. Changelog for the new version must begin with version heading, i.e `# 0.1.0`.
Everything between this heading and the heading for previous version will be pulled into the changelog.

A `release-conf.yaml` file is required. See [Configuration](#configuration) section for details.

Once a Github release is complete, bot will upload this release to PyPI. Note that you have to setup your login details (see [Requirements](#requirements)).

After PyPI release, if enabled in  `release-conf.yaml`, bot will try to release on Fedora dist-git, on `master` branch and branches specified in configuration. 
It should not create merge conflicts, but in case it does, you have to solve them first before attempting the release again.


# Configuration
There are two yaml configuration files, `conf.yaml` and `release-conf.yaml`.
`conf.yaml` must be accessible during bot initialization and specifies how to access Github repository,
while `release-conf.yaml` must be stored in the repository itself and specifies how to do a Github/PyPI/Fedora releases.
If the path to `conf.yaml` is not passed to bot with `-c/--configuration`, bot will try to find it in current working directory.

Here are the `conf.yaml` configuration options:

| Option        | Meaning       | Required      |
|------------- |-------------|-------------| 
| `repository_name`     | Name of your Github repository  | Yes |
| `repository_owner`    | Owner of the repository    	  | Yes |
| `github_token`		| [Github personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/)   | Yes |
| `fas_username`		| [FAS](https://fedoraproject.org/wiki/Account_System)	username. Only need for releasing on Fedora| No |
| `refresh_interval`	| Time in seconds between checks on repository. Default is 180 | No |

Sample config named [conf.yaml](conf.yaml) can be found in this repository.

Regarding `github_token`, it's usually a good idea to create a Github account for the bot (and use its Github API token)
so you can keep track of what changes were made by bot and what are your own.

You also have to have a `release-conf.yaml` file in the root of your project repository.
Here are possible options:

| Option        | Meaning       | Required      |
|---------------|---------------|---------------| 
| `python_versions`     | List of major python versions that bot will build separate wheels for | Yes |
| `changelog`   | List of changelog entries. If empty, changelog defaults to `$version release` | No |
| `author_name`	| Author name for changelog. If not set, author of the merge commit is used	    | No |
| `author_email`| Author email for changelog. If not set, author of the merge commit is used	| No |
| `fedora`      | Whether to release on fedora. False by default | No |
| `fedora_branches`     | List of branches that you want to release on. Master is always implied | No |

Sample config named [release-conf-example.yaml](release-conf-example.yaml) can be found in this repository.

# Requirements
Releasing to PyPI requires to have `wheel` package both for python 2 and python 3,
therefore please install `requirements.txt` with both versions of `pip`.
You also have to setup your PyPI login details in `$HOME/.pypirc`
as described in [PyPI documentation](https://packaging.python.org/tutorials/distributing-packages/#create-an-account).
If you are releasing to Fedora, you will need to have an active kerberos ticket while the bot runs
or specify path to kerberos keytab file with `-k/--keytab`.
Also, `fedpkg` requires that you have ssh key in your keyring, that you uploaded to FAS.

# Docker image
To make it easier to run this, release-bot is available as an [source-to-image](https://github.com/openshift/source-to-image) builder image. You need to setup a git repository, where you'll store the `conf.yaml` and `.pypirc` files. If you are releasing on Fedora, you will also need to add `id_rsa` (a private ssh key that you configured in FAS) and `fedora.keytab` (kerberos keytab for fedora). If this is not a local repository, make sure it's private so you prevent any private info leaking out. You can then create the final image like this:
```
$ s2i build $CONFIGURATION_REPOSITORY_URL usercont/release-bot app-name
``` 

# OpenShift template
You can also run this bot in OpenShift using [openshift-template.yml](openshift-template.yml) in this repository. You must set two environment variables, the `$APP_NAME` is the name of your release-bot deployment, and `$CONFIGURATION_REPOSITORY` which contains configuration for the release-bot. The contents of the repository are described [above](#docker-image). Note that if you use private repository (which you **absolutely** should), you will need to set up a new [OpenShift secret](https://docs.openshift.com/container-platform/3.7/dev_guide/secrets.html) named `release-bot-secret` to authenticate. It can be a ssh private key that you can use to access the repository (for GitHub see [deploy keys](https://developer.github.com/v3/guides/managing-deploy-keys/)). Here's an [guide](https://blog.openshift.com/deploy-private-git-repositories/) on how to do that in OpenShift GUI, or another [guide](https://blog.openshift.com/deploying-from-private-git-repositories/) that uses `oc` commandline tool.

By default, the release-bot builder image won't update itself when a new version of this image is pushed to docker hub.
You can change it by uncommenting lines with `#importPolicy:` and `#scheduled: true` in [openshift-template.yml](openshift-template.yml). Then the image will be pulled on a new release.
