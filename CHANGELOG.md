# 0.7.1

- Few bug fixes and base image update.

# 0.7.0

**We would like to thank all GSoC applicants for their contribution to this project during the application period!**

## Breaking changes

- **Releasing to Fedora is now deprecated.** We removed Fedora functionality in favor of the new project [packit](https://packit.dev/).

## New features

- Dry-run mode! Now you can try release process without making actual changes. Thanks to @Aniket-Pradhan.
- You can now use new issue titles, when you are making new release:
  - `new major release`
  - `new minor release`
  - `new patch release` , Thanks to @shresthagrawal.
- Release bot can now handle Github webhooks. Thanks to @marusinm.
- You can now specify name of your PyPI project in configuration, in case it is different than repo name. Thanks to @Elias999.
- Releasing to PyPI is now _optional_. Thanks to @Aniket-Pradhan.
- You can explicitly specify `clone_url` in Release bot configuration file. Thanks to @Z0Marlin.
- Support also for `version` variable (besides the `__version__`). Thanks to @Toaster192.

## Fixes and docs

- Tutorial on how to make your first release with release-bot locally. Thanks to @marusinm.
- Contribution guide is now more newcomers-friendly. Thanks to @Z0Marlin.
- Support for installing release-bot from arch user repository. Thanks to @Aniket-Pradhan.
- Release-bot now checks for tag instead of release name, when checking latest release. Thanks to @shresthagrawal.

# 0.6.1

- Bot ignores 'python_versions' in release-conf and builds an sdist and a py3 wheel.

# 0.6.0

- Jenkinsfile and Contribution guide have been added.
- Metadata from setup.py have been moved to setup.cfg.
- README.md has been updated.
- A way to authenticate as a Github App has been added.
- Bot works in the upstream git repo instead of downloading zip.
- Bot adds a link to Bodhi (to Github comment) when fedora builds are successful.
- Base images have been bumped to F29.
- Some tests have been fixed.

# 0.5.0

- You can specify github labels in release-conf.yaml configuration file
  which should be applied on a pull request created by release bot.
- Documentation is updated and is more clear now.
- The bot no longer tries to release old versions again.

# 0.4.1

- Fix wrong PR description
- Fix pytest fixture warnings
- Fix git credentials for Fedora releasing

# 0.4.0

- Allow self-releasing on issue
- Fix code style issues
- Add more tests on github & bot itself
- Ability to do initial release + fixes
- Fix minor issues from code review, change how release-conf is loaded
- Fix code style issues
- Add ability to make PRs with version change based on release issue
- Update config files from kwaciaren
- Use bandit/pylintrc file from kwaciaren
- [.s2i/bin/run] Don't use --keytab if there's no such file
- Use absolute imports

# 0.3.8

- Fedora-related bug fixes

# 0.3.7

- Fix KeyError

# 0.3.6

- Fix KeyError

# 0.3.5

- Request/Limit openshift resources

# 0.3.2

- Iterate over PRs in descending order
- Use nss_wrapper to create/use custom passwd file
- Add status comments to PR

# 0.3.0

- Structure code into classes
- bug fixes, bug fixes, bug fixes

# 0.1.1

- Fix changelog parsing
- Bump up version because of PyPi

# 0.1.0

- Initial release.
