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
