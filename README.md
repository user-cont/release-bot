[![Build Status](https://travis-ci.org/user-cont/release-bot.svg?branch=master)](https://travis-ci.org/user-cont/release-bot) [![PyPI version](https://badge.fury.io/py/release-bot.svg)](https://badge.fury.io/py/release-bot) [![Build Status](https://ci.centos.org/job/release-bot-push/badge/icon)](https://ci.centos.org/job/release-bot-push/)

![Realease Bot](logo_design/logo-bot-extended-v1-readme-border.png)


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

### Install
```
$ pip install release-bot
```
Other possible installations are through [Arch User Repository](#arch-user-repository) or install on repo as [Github Application](#github-application).

First interaction with release bot may be automated releases on Github. Let's do it.

### Configure the release bot
Release bot can be configured in two ways, using `release-bot init` or manually

#### Configuration using `release-bot init`
Clone the upstream repository where new releases will be published
and from the root dir of the repository run the following command:
```shell
release-bot init
```
Enter the required details when asked by the bot. All of the default choices provided by the init should be enough for the current trial. You will also need to generate a [Github personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/).
Recommended permissions for access token are: `repo`, `delete_repo`, `user`.

You can later on modify all the config files. For possible advanced setup check [the documentation for an upstream repository](#upstream-repository) and [gitchanelog](#GitChangeLog).

After the init is completed **commit all of the changes and push it** to the upstream repo.

#### Manual Configuration

##### 1. Create upstream repository or use existing one
This is meant to be upstream repository where new releases will be published.

Within upstream repository create `release-conf.yaml` file which contains info on how to release the specific project.
Copy and edit [release-conf.yaml](release-conf-example.yaml).

At the end of `release-conf.yaml` add this line of code:
```yaml
# whether to allow bot to make PRs based on issues
trigger_on_issue: true
```
Then copy [.gitchangelog.rc](/gitchangelog/.gitchangelog.rc) and [markdown.tpl](/gitchangelog/.gitchangelog.rc) (which are the config files for the [gitchangelog](https://github.com/vaab/gitchangelog.git))
to the root dir of the upstream repository.
For possible advanced setup check [the documentation for an upstream repository](#upstream-repository) and [gitchanelog](#GitChangeLog).

##### 2. Create `conf.yaml`

Create configuration file `conf.yaml`. You can use [one](conf.yaml) from this repository. You will need to generate a [Github personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/).
Recommended permissions for access token are: `repo`, `delete_repo`, `user`.

At the end of `conf.yaml` add this line of code:
```yaml
# Name of the account that the github_token belongs to
# Only needed for triggering the bot on an issue.
github_username: <your_github_username>
gitchangelog: true
```
**Note**: This file **should not** be stored in upstream repository as it contains sensitive data.

For possible advanced setup check [the documentation for a private repository](#private-repository).
Also, see [requirements](#requirements) in case you want include PyPi releases.

### Run the release-bot
At this point, release-bot is installed. At least four configuration files are set `release-conf.yaml`, `conf.yaml`, `.gitchangelog.rc`, `markdown.tpl` (optionally `.pypirc`).

 Launch bot by a command:
```$ release-bot -c <path_to_conf.yaml> --debug```
You can scroll down and see debug information of running bot.

### Make a new release
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

There are two more files required if you use `gitchangelog` to genereate change logs:
 1. `.gitchangelog.rc` -- a config file used by the gitchangelog to specify the regex for converting commits and the output engine
 2.  `markdown.tpl` -- a template file used by pystache to genereate markdown

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
| `gitchangelog`               | Whether to use gitchangelog to generate change logs. False by default. | No |

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

## GitChangeLog

For using the [gitchangelog](https://github.com/vaab/gitchangelog) you must add the line `gitchanelog: true` to the conf.yaml, and add the files `.gitchangelog.rc` and `markdown.tpl` in the root of your upstream project repository. Sample config files: [.gitchangelog.rc](/gitchangelog/.gitchangelog.rc) and [template.tpl](/gitchangelog/template.tpl).

`.gitchangelog.rc` sample is heavily commented and should be enough to make modification but for specific details you can refer to the original [repository](https://github.com/vaab/gitchangelog).
The default template `markdown.tpl` is configured to create Markdown divided into sections (New, Changes, Fix, Others) based on the commits. The data sent to the output engine [pystache](https://github.com/defunkt/pystache) by the gitchangelog is in the following [format](https://github.com/vaab/gitchangelog/edit/master/README.rst#L331-L356). You can use it to create a custom template, please refer [mustache](http://mustache.github.io/).

## Requirements
Are specified in `requirements.txt`.
You have to setup your PyPI login details in `$HOME/.pypirc` as described in
[PyPI documentation](https://packaging.python.org/tutorials/distributing-packages/#create-an-account).

## Github Application

Release-bot as Github Application is currently in testing and will be available soon in Github market.
Github application will speed-up configuration process.   

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

## Logo design

Created by `Marián Mrva` - [@surfer19](https://github.com/surfer19)