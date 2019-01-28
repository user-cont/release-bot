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
This module provides interface to git
"""
import shutil
from tempfile import TemporaryDirectory, mkdtemp
from os import path

from release_bot.utils import run_command, run_command_get_output
from release_bot.exceptions import GitException


class Git:
    """
    Interface to git
    """
    def __init__(self, url, conf):
        self.repo_path = self.clone(url)
        self.credential_store = None
        self.conf = conf
        self.logger = conf.logger

    @staticmethod
    def clone(url):
        """
        Clones repository from url to temporary directory
        :param url:
        :return: TemporaryDirectory object
        """
        temp_directory = mkdtemp()
        if not run_command(temp_directory, f'git clone {url} .',
                           "Couldn't clone repository!", fail=True):
            raise GitException(f"Can't clone repository {url}")
        return temp_directory

    def get_log_since_last_release(self, latest_version):
        """
        Utilizes git log to get log since last release, excluding merge commits
        :param latest_version: previous version
        :return: changelog or placeholder
        """
        cmd = f'git log {latest_version}... --no-merges --format=\'* %s\''
        success, changelog = run_command_get_output(self.repo_path, cmd)
        return changelog if success and changelog else 'No changelog provided'

    def add(self, files: list):
        """
        Executes git add
        :param files: list of files to add
        :return:
        """
        for file in files:
            success = run_command(self.repo_path, f'git add {file}', '', False)
            if not success:
                raise GitException(f"Can't git add file {file}!")

    def commit(self, message='release commit', allow_empty=False):
        """
        Executes git commit
        :param message: commit message
        :return:
        """
        arg = '--allow-empty' if allow_empty else ''
        success = run_command(self.repo_path, f'git commit {arg} -m \"{message}\"', '', False)
        if not success:
            raise GitException(f"Can't commit files!")

    def pull(self):
        """
        Pull from origin/master to local master branch.
        """
        run_command(
            self.repo_path,
            'git pull --rebase origin master',
            'Unable to pull from remote repository', True)

    def push(self, branch):
        """
        Executes git push
        :param branch: branch to push
        :return:
        """
        success = run_command(self.repo_path, f'git push origin {branch}', '', False)
        if not success:
            raise GitException(f"Can't push branch {branch} to origin!")

    def set_credentials(self, name, email):
        """
        Sets credentials fo git repo to keep git from resisting to commit
        :param name: committer name
        :param email: committer email
        :return: True on success False on fail
        """
        email = run_command(self.repo_path, f'git config user.email "{email}"', '', fail=False)
        name = run_command(self.repo_path, f'git config user.name "{name}"', '', fail=False)
        return email and name

    def set_credential_store(self):
        """
        Edits local git config with credentials to be used for pushing
        :return: path to temp file with credentials
        """
        if not self.credential_store:
            # TODO: do only a single tmpdir; merge this into tmpdir with git repo itself
            self.credential_store = TemporaryDirectory()
            store_path = path.join(self.credential_store.name, 'credentials')
            # write down credentials
            with open(store_path, 'w+') as credentials:
                credentials.write(
                    f'https://{self.conf.github_username}:{self.conf.github_token}@github.com/'
                    f'{self.conf.repository_owner}/{self.conf.repository_name}')
            # let git know
            with open(path.join(self.repo_path, '.git/config'), 'a+') as config:
                config.write(f'\n[credential]\n\thelper = store --file={store_path}\n')
        return path.join(self.credential_store.name, 'credentials')

    def checkout(self, target):
        """
        checkout the target

        :param target: str (branch, tag, file)
        :return: None
        """
        return run_command(self.repo_path, f'git checkout "{target}"', '', fail=True)

    def checkout_new_branch(self, branch):
        """
        Creates a new local branch
        :param branch: branch name
        :return: True on success False on fail
        """
        return run_command(self.repo_path, f'git checkout -b "{branch}"', '', fail=False)

    def fetch_tags(self):
        """
        Fetch all tags from origin
        """
        return run_command(self.repo_path, 'git fetch --tags', 'Unable to fetch tags from remote server', fail=True)

    def cleanup(self):
        """
        Cleans up the directory with repository
        :return:
        """
        self.logger.info("cleaning up the cloned repository")
        shutil.rmtree(self.repo_path)
