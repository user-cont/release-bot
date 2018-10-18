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

from release_bot.cli import CLI
from release_bot.configuration import configuration
from release_bot.exceptions import ReleaseException
from release_bot.fedora import Fedora
from release_bot.github import Github
from release_bot.pypi import PyPi


class ReleaseBot:

    def __init__(self, configuration):
        self.conf = configuration
        self.github = Github(configuration)
        self.pypi = PyPi(configuration)
        self.fedora = Fedora(configuration)
        self.logger = configuration.logger
        self.new_release = {}
        self.new_pr = {}

    def cleanup(self):
        if 'tempdir' in self.new_release:
            self.new_release['tempdir'].cleanup()
        self.new_release = {}
        self.new_pr = {}
        self.github.comment = []
        self.fedora.progress_log = []

    def load_release_conf(self):
        """
        Updates new_release with latest release-conf.yaml from repository
        :return:
        """
        # load release configuration from release-conf.yaml in repository
        conf = self.github.get_configuration()
        release_conf = self.conf.load_release_conf(conf)
        self.new_release.update(release_conf)

    def find_open_release_issues(self):
        """
        Looks for opened release issues on github
        :return: True on found, False if not found
        """
        cursor = ''
        release_issues = {}
        while True:
            edges = self.github.walk_through_open_issues(start=cursor, direction='before')
            if not edges:
                self.logger.debug(f'No more open issues found')
                break
            else:
                for edge in reversed(edges):
                    cursor = edge['cursor']
                    match = re.match(r'(.+) release', edge['node']['title'].lower())
                    if match and validate(match[1]) and \
                            edge['node']['authorAssociation'] in ['MEMBER', 'OWNER', 'COLLABORATOR']:
                        release_issues[match[1]] = edge['node']
                        self.logger.info(f'Found new release issue with version: {match[1]}')
        if len(release_issues) > 1:
            msg = f'Multiple release issues are open {release_issues}, please reduce them to one'
            self.logger.error(msg)
            return False
        if len(release_issues) == 1:
            for version, node in release_issues.items():
                self.new_pr = {'version': version,
                               'issue_id': node['id'],
                               'issue_number': node['number'],
                               'labels': self.new_release.get('labels')}
                return True
        else:
            return False

    def find_newest_release_pull_request(self):
        """
        Find newest merged release PR

        :return: bool, whether PR was found
        """
        cursor = ''
        while True:
            edges = self.github.walk_through_prs(start=cursor, direction='before', closed=True)
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
                    new_release = {'version': match[1],
                                   'commitish': merge_commit['oid'],
                                   'pr_id': edge['node']['id'],
                                   'author_name': merge_commit['author']['name'],
                                   'author_email': merge_commit['author']['email']}
                    self.new_release.update(new_release)
                    return True

    def make_release_pull_request(self):
        """
        Makes release pull request and handles outcome
        :return: whether making PR was successful
        """

        def pr_handler(success):
            """
            Handler for the outcome of making a PR
            :param success: whether making PR was successful
            :return:
            """
            result = 'made' if success else 'failed to make'
            msg = f"I just {result} a PR request for a release version {self.new_pr['version']}"
            level = logging.INFO if success else logging.ERROR
            self.logger.log(level, msg)
            if success:
                msg += f"\n Here's a [link to the PR]({self.new_pr['pr_url']})"
            comment_backup = self.github.comment.copy()
            self.github.comment = [msg]
            self.github.add_comment(self.new_pr['issue_id'])
            self.github.comment = comment_backup
            if success:
                self.github.close_issue(self.new_pr['issue_number'])
            self.new_pr['repo'].cleanup()

        prev_version = self.github.latest_release()
        self.new_pr['previous_version'] = prev_version
        if Version.coerce(prev_version) >= Version.coerce(self.new_pr['version']):
            msg = f"Version ({prev_version}) is already released and this issue is ignored."
            self.logger.warning(msg)
            return False
        msg = f"Making a new PR for release of version {self.new_pr['version']} based on an issue."
        self.logger.info(msg)

        try:
            self.new_pr['repo'] = self.github.clone_repository()
            if not self.new_pr['repo']:
                raise ReleaseException("Couldn't clone repository!")

            if self.github.make_release_pr(self.new_pr):
                pr_handler(success=True)
                return True
        except ReleaseException:
            pr_handler(success=False)
            raise
        return False

    def make_new_github_release(self):
        def release_handler(success):
            result = "released" if success else "failed to release"
            msg = f"I just {result} version {self.new_release['version']} on Github"
            level = logging.INFO if success else logging.ERROR
            self.logger.log(level, msg)
            self.github.comment.append(msg)

        try:
            latest_github = self.github.latest_release()
            if Version.coerce(latest_github) >= Version.coerce(self.new_release['version']):
                self.logger.info(
                    f"{self.new_release['version']} has already been released on Github")
                # to fill in new_release['fs_path'] so that we can continue with PyPi upload
                self.new_release = self.github.download_extract_zip(self.new_release)
                return self.new_release
        except ReleaseException as exc:
            raise ReleaseException(f"Failed getting latest Github release (zip).\n{exc}")

        try:
            released, self.new_release = self.github.make_new_release(self.new_release)
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
                msg += f", successfully built for branches: {builds}"
            level = logging.INFO if success else logging.ERROR
            self.logger.log(level, msg)
            self.github.comment.append(msg)

        try:
            name, email = self.github.get_user_contact()
            self.new_release['commit_name'] = name
            self.new_release['commit_email'] = email
            success_ = self.fedora.release(self.new_release)
            release_handler(success_)
        except ReleaseException:
            release_handler(success=False)
            raise

    def run(self):
        self.logger.info(f"release-bot v{configuration.version} reporting for duty!")
        while True:
            try:
                self.load_release_conf()
                if self.find_newest_release_pull_request():
                    self.make_new_github_release()
                    # Try to do PyPi release regardless whether we just did github release
                    # for case that in previous iteration (of the 'while True' loop)
                    # we succeeded with github release, but failed with PyPi release
                    if self.make_new_pypi_release():
                        # There's no way how to tell whether there's already such a fedora 'release'
                        # so try to do it only when we just did PyPi release
                        self.make_new_fedora_release()
                if self.new_release.get('trigger_on_issue') and self.find_open_release_issues():
                    if self.new_release.get('labels') is not None:
                        self.github.put_labels_on_issue(self.new_pr['issue_number'],
                                                        self.new_release.get('labels'))
                    self.make_release_pull_request()
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
