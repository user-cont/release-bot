"""
This module provides functionality for automation of releasing projects
into various downstream services
"""
import re
import time
import os
from semantic_version import Version, validate
from sys import exit

from .cli import CLI
from .configuration import configuration
from .fedora import Fedora
from .github import Github
from .pypi import PyPi


class ReleaseBot:

    def __init__(self, configuration):
        self.conf = configuration
        self.github = Github(configuration)
        self.pypi = PyPi(configuration)
        self.fedora = Fedora(configuration)
        self.logger = configuration.logger
        self.logger.info(f"release-bot v{configuration.version} reporting for duty!")
        self.new_release = {}

    def find_newest_release_pull_request(self):
        """
        Find newest merged release PR

        :return: bool, whether PR was found
        """
        cursor = ''
        while True:
            edges = self.github.walk_through_closed_prs(start=cursor, direction='before')
            if not edges:
                self.logger.debug(f'No merged release PR found')
                return False

            for edge in reversed(edges):
                cursor = edge['cursor']
                match = re.match(r'(.+) release', edge['node']['title'].lower())
                if match and validate(match[1]):
                    merge_commit = edge['node']['mergeCommit']
                    self.logger.info(f"Found merged release PR with version {match[1]}, "
                                      f"commit id: {merge_commit['oid']}")
                    self.new_release = {'version': match[1],
                                        'commitish': merge_commit['oid'],
                                        'author_name': merge_commit['author']['name'],
                                        'author_email': merge_commit['author']['email']}
                    return True

    def make_new_github_release(self):
        self.new_release = self.github.make_new_release(self.new_release,
                                                        self.pypi.latest_version())
        return self.new_release

    def make_new_pypi_release(self):
        latest_pypi = self.pypi.latest_version()
        if Version.coerce(latest_pypi) >= Version.coerce(self.new_release['version']):
            self.logger.info(f"{self.new_release['version']} has already been released on PyPi")
            return False

        # load release configuration from release-conf.yaml in repository
        release_conf = self.conf.load_release_conf(os.path.join(self.new_release['fs_path'],
                                                                'release-conf.yaml'))
        self.new_release.update(release_conf)
        self.pypi.release(self.new_release)
        return True

    def make_new_fedora_release(self):
        if self.new_release['fedora']:
            self.logger.info("Triggering Fedora release")
            self.fedora.release(self.new_release)
            self.new_release['tempdir'].cleanup()

    def run(self):
        while True:
            if self.find_newest_release_pull_request():
                self.make_new_github_release()
                # Try to do PyPi release regardless whether we just did github release
                # for case that in previous iteration (of the 'while True' loop)
                # we succeeded with github release, but failed with PyPi release
                if self.make_new_pypi_release():
                    # There's no way how to tell whether there's already such a fedora 'release'
                    # so try to do it only when we just did PyPi release
                    self.make_new_fedora_release()
            time.sleep(self.conf.refresh_interval)


def main():
    CLI.parse_arguments()
    configuration.load_configuration()

    rb = ReleaseBot(configuration)
    rb.run()


if __name__ == '__main__':
    exit(main())
