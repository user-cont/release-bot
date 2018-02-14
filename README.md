Release bot
============
This is a bot that helps maintainers deliver their software to users. It is meant to watch github repositories for 
release Pull Requests. The PR must be named in this format `0.1.0 release`. No other format is supported yet.Once 
this PR is closed (and merged) bot will create a new github release. Changelog will be pulled from root of the 
repository and must be named `CHANGELOG.md`. Changelog for new version must begin with version heading, i.e `# 0.1.0`
. Everything between this heading and the heading for previous version will be pulled into the changelog. 

Once a release is complete, bot will upload this release to PyPi. Note that you have to setup your login details (see Requirements). This is subject 
to change, but right now bot will build sdist and then wheels for python2 and for python3 and upload them.

# Configuration
Configuration is in a form of a yaml file. You can specify your config using `-c file.yaml` or `--configuration file.yaml`. If you do not specify it using an argument, bot will try to find `conf.yaml` in current working directory.
Here are the configuration options:
| Option        | Meaning       | Required      |
| ------------- |:-------------:|:-------------:| 
| repository_name     | Name of your Github repository  | Yes |
| repository_owner    | Owner of the repository    		| Yes |
| github_token		  | [Github personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/)   | Yes |
| refresh_interval	  | Time in seconds betwwen checks on repository. Default is 180 | No |

Sample config can be found in this repository

Best option for this is creating a github account for this bot so you can keep track of what changes were made by bot and what are your own.

# Requirements
This requires that you have following installed:
* twine - `pip install twine`
* wheel - for both versions of python
⋅⋅* `pip install wheel`
⋅⋅* `pip3 install wheel`
This + the bot.py imports. You also have to setup your PyPi login details in `$HOME/.pypirc` as described in [PyPi documentation](https://packaging.python.org/tutorials/distributing-packages/#create-an-account)

