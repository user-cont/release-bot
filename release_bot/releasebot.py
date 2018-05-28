# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module provides functionality for automation of releasing projects
into various downstream services
"""
import logging
import re
import time
from semantic_version import Version, validate
from sys import exit

from .cli import CLI
from .configuration import configuration
from .exceptions import ReleaseException
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
        self.new_release = {}

    def cleanup(self):
        if 'tempdir' in self.new_release:
            self.new_release['tempdir'].cleanup()
        self.new_release = {}
        self.github.comment = []
        self.fedora.progress_log = []

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
                                        'pr_id': edge['node']['id'],
                                        'author_name': merge_commit['author']['name'],
                                        'author_email': merge_commit['author']['email']}
                    return True

    def make_new_github_release(self):
        def release_handler(success):
            result = "released" if success else "failed to release"
            msg = f"I just {result} version {self.new_release['version']} on Github"
            level = logging.INFO if success else logging.ERROR
            self.logger.log(level, msg)
            self.github.comment.append(msg)

        try:
            released, self.new_release = self.github.make_new_release(self.new_release,
                                                                      self.pypi.latest_version())
            if released:
                release_handler(success=True)
        except ReleaseException:
            release_handler(success=False)
            raise

        return self.new_release

    def make_new_pypi_release(self):
        def release_handler(success):
            result = "released" if success else "failed to release"
            msg = f"I just {result} version {self.new_release['version']} on PyPI"
            level = logging.INFO if success else logging.ERROR
            self.logger.log(level, msg)
            self.github.comment.append(msg)

        latest_pypi = self.pypi.latest_version()
        if Version.coerce(latest_pypi) >= Version.coerce(self.new_release['version']):
            self.logger.info(f"{self.new_release['version']} has already been released on PyPi")
            return False

        # load release configuration from release-conf.yaml in repository
        release_conf = self.conf.load_release_conf(self.new_release['fs_path'])
        self.new_release.update(release_conf)
        try:
            self.pypi.release(self.new_release)
            release_handler(success=True)
        except ReleaseException:
            release_handler(success=False)
            raise

        return True

    def make_new_fedora_release(self):
        if not self.new_release.get('fedora'):
            self.logger.debug('Skipping Fedora release')
            return

        self.logger.info("Triggering Fedora release")

        def release_handler(success):
            result = "released" if success else "failed to release"
            msg = f"I just {result} on Fedora"
            builds = ', '.join(self.fedora.builds)
            if builds:
                msg += ", successfully built for branches: {builds}"
            level = logging.INFO if success else logging.ERROR
            self.logger.log(level, msg)
            self.github.comment.append(msg)

        try:
            success_ = self.fedora.release(self.new_release)
            release_handler(success_)
        except ReleaseException:
            release_handler(success=False)
            raise

    def run(self):
        self.logger.info(f"release-bot v{configuration.version} reporting for duty!")

        while True:
            try:
                if self.find_newest_release_pull_request():
                    self.make_new_github_release()
                    # Try to do PyPi release regardless whether we just did github release
                    # for case that in previous iteration (of the 'while True' loop)
                    # we succeeded with github release, but failed with PyPi release
                    if self.make_new_pypi_release():
                        # There's no way how to tell whether there's already such a fedora 'release'
                        # so try to do it only when we just did PyPi release
                        self.make_new_fedora_release()
            except ReleaseException as exc:
                self.logger.error(exc)

            self.github.add_comment(self.new_release.get('pr_id'))
            self.cleanup()
            self.logger.debug(f"Done. Going to sleep for {self.conf.refresh_interval}s")
            time.sleep(self.conf.refresh_interval)


def main():
    CLI.parse_arguments()
    configuration.load_configuration()

    rb = ReleaseBot(configuration)
    rb.run()


if __name__ == '__main__':
    exit(main())
