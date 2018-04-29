"""
This module provides functionality for automation of releasing projects
into various downstream services
"""
import re
import time
import os
import argparse
import logging
from semantic_version import Version, validate
from sys import exit

from .configuration import configuration
from .fedora import Fedora
from .github import Github
from .pypi import PyPi


def parse_arguments():
    """Parse application arguments"""
    parser = argparse.ArgumentParser(description="Automatic releases bot", prog='release-bot')
    parser.add_argument("-d", "--debug", help="turn on debugging output",
                        action="store_true", default=False)
    parser.add_argument("-c", "--configuration", help="use custom YAML configuration",
                        default='')
    parser.add_argument("-v", "--version", help="display program version", action='version',
                        version=f"%(prog)s {configuration.version}")
    parser.add_argument("-k", "--keytab", help="keytab file for fedora", default='')

    args = parser.parse_args()
    if args.configuration:
        path = args.configuration
        if not os.path.isabs(path):
            args.configuration = os.path.join(os.getcwd(), path)
        if not os.path.isfile(path):
            configuration.logger.error(
                f"Supplied configuration file is not found: {args.configuration}")
            exit(1)
    if args.debug:
        configuration.logger.setLevel(logging.DEBUG)
    for key, value in vars(args).items():
        setattr(configuration, key, value)


class ReleaseBot:

    def __init__(self, configuration):
        self.conf = configuration
        self.github = Github(configuration)
        self.pypi = PyPi(configuration)
        self.fedora = Fedora(configuration)
        self.logger = configuration.logger
        self.logger.info(f"release-bot v{configuration.version} reporting for duty!")
        self.new_release = {}

    def find_pull_request_with_latest_pypi_release(self):
        latest_pypi = self.pypi.latest_version()
        self.logger.debug(f"Latest PyPi release: {latest_pypi}")

        cursor = ''
        found = False
        # try to find closed PR with latest_pypi version
        while not found:
            response = self.github.walk_through_closed_prs(cursor, 'before')
            if not response['data']['repository']['pullRequests']['edges']:
                self.logger.debug(f'No closed PR with the latest {latest_pypi} PyPI release found')
                cursor = ''
                break
            for edge in reversed(response['data']['repository']['pullRequests']['edges']):
                cursor = edge['cursor']
                if latest_pypi + ' release' == edge['node']['title'].lower():
                    self.logger.debug(
                        f'Found closed PR with the latest {latest_pypi} PyPi release')
                    found = True
                    break
        return cursor

    def check_for_new_pull_request_since_latest_pypi(self, cursor):
        while True:
            response = self.github.walk_through_closed_prs(cursor, which="first")
            if not response['data']['repository']['pullRequests']['edges']:
                self.logger.debug('No newer release PR found')
                self.new_release = {}
                return False
            for edge in response['data']['repository']['pullRequests']['edges']:
                cursor = edge['cursor']
                match = re.match(r'(.+) release', edge['node']['title'].lower())
                if match and validate(match[1]):
                    merge_commit = edge['node']['mergeCommit']
                    self.logger.debug(f'Found newer PR with version {match[1]}')
                    self.new_release = {'version': match[1],
                                        'commitish': merge_commit['oid'],
                                        'author_name': merge_commit['author']['name'],
                                        'author_email': merge_commit['author']['email']}
                    return True

    def make_new_pypi_release(self):
        # check if a new release was made
        latest_pypi = self.pypi.latest_version()
        if Version.coerce(latest_pypi) < Version.coerce(self.new_release['version']):
            self.logger.info("Newer version on github, triggering PyPi release")
            # load release configuration from release-conf.yaml in repository
            release_conf = self.conf.load_release_conf(os.path.join(self.new_release['fs_path'],
                                                                    'release-conf.yaml'))
            self.new_release.update(release_conf)
            self.pypi.release(self.new_release)
        else:
            self.logger.debug((f"PyPi version {latest_pypi} | "
                               f"Github version {self.github.latest_version()} -> nothing to do"))

    def make_new_fedora_release(self):
        if self.new_release['fedora']:
            self.logger.info("Triggering Fedora release")
            self.fedora.release(self.new_release)
            self.new_release['tempdir'].cleanup()

    def make_new_github_release(self):
        self.new_release = self.github.make_new_release(self.new_release,
                                                        self.pypi.latest_version())
        return self.new_release

    def run(self):
        while True:
            cursor = self.find_pull_request_with_latest_pypi_release()
            # now walk through PRs since the latest_pypi version and check for a new one
            if cursor and self.check_for_new_pull_request_since_latest_pypi(cursor):
                # if found, make a new release on github
                # this has to be done using older github api because v4 doesn't support this yet
                if self.make_new_github_release():
                    self.make_new_pypi_release()
                    self.make_new_fedora_release()
            time.sleep(self.conf.refresh_interval)


def main():
    parse_arguments()
    configuration.load_configuration()

    rb = ReleaseBot(configuration)
    rb.run()


if __name__ == '__main__':
    exit(main())
