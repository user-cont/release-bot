# 0.7.0

* fix last two test failures
* address codacy warning
* Unparametrize test_different_pypi_name() again
* dont bail when you cannot delete the temp gh repo
* parametrize test_different_pypi_name
* fix test_look_for_version_files
* use setdefault() with pypi project name
* Fix cyclic dependency with logger
* add test case for custom PyPI name
* Initial work on: PyPI name can be different than repository name
* [test_utils.py] fix test_look_for_version_files()
* Add support for using the version variable
* Updated return values to be more consistent.
* Add dry-run tests.
* Added dry-run argument.
* Update tests.
* set default value for docker image
* In openshift-template-dev add container repository into variable.
* Update tests.
* implementation of github webhooks handling
* Fix Codacy issues.
* Removed the extra comments.
* Changed function definitions to include individual variables.
* Updated contributing guidelines
* Removed previously left over code
* Updated class names.
* Added New_PR class. Updated it's references
* Added New_Release class. Updated it's references.
* Update readme.
* Remove `GITHUB_USER` env variable
* Added test for loading conf.yaml
* Moved checking of clone_url to `configuration.py`
* Modify unit test for git to check for tag name
* Return tag_name instead of release_name
* Update README
* Add new configuration option to specify clone url.
* delete s2i check for pypi configuration
* Remove fedora functionality from release-bot.
* Remove trailing whitespace
* Add the comments for checkout master branch before release_pr
* Modify make_release_pr() to check for master before branching and return to master after
* Modify make_new_pypi_release() to checkout master branch in the end
* Added condition to check if user wants to release for PyPi or not.
* remove check for github_api_status
* Remove unwanted library Version
* Add tests for version_from_title
* Remove trailing whitespace
* Update README.md and Add function documentation
* Add different version formats user-cont#12
* Removed the extra white-space.
* Fixed a bug introduced in #162
* Update guide to use trigger_on_issue
* Document how to try release-bot locally

# 0.6.1

* Bot ignores 'python_versions' in release-conf and builds an sdist and a py3 wheel.

# 0.6.0

* Jenkinsfile and Contribution guide have been added.
* Metadata from setup.py have been moved to setup.cfg.
* README.md has been updated.
* A way to authenticate as a Github App has been added.
* Bot works in the upstream git repo instead of downloading zip.
* Bot adds a link to Bodhi (to Github comment) when fedora builds are successful.
* Base images have been bumped to F29.
* Some tests have been fixed.

# 0.5.0

* You can specify github labels in release-conf.yaml configuration file
  which should be applied on a pull request created by release bot.
* Documentation is updated and is more clear now.
* The bot no longer tries to release old versions again.

# 0.4.1

* Fix wrong PR description
* Fix pytest fixture warnings
* Fix git credentials for Fedora releasing

# 0.4.0

* Allow self-releasing on issue
* Fix code style issues
* Add more tests on github & bot itself
* Ability to do initial release + fixes
* Fix minor issues from code review, change how release-conf is loaded
* Fix code style issues
* Add ability to make PRs with version change based on release issue
* Update config files from kwaciaren
* Use bandit/pylintrc file from kwaciaren
* [.s2i/bin/run] Don't use --keytab if there's no such file
* Use absolute imports

# 0.3.8
* Fedora-related bug fixes

# 0.3.7
* Fix KeyError

# 0.3.6
* Fix KeyError

# 0.3.5
* Request/Limit openshift resources

# 0.3.2
* Iterate over PRs in descending order
* Use nss_wrapper to create/use custom passwd file
* Add status comments to PR

# 0.3.0
* Structure code into classes
* bug fixes, bug fixes, bug fixes

# 0.1.1
* Fix changelog parsing
* Bump up version because of PyPi

# 0.1.0

* Initial release.
