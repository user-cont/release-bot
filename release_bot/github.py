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
import logging
import os
import time
import re

from release_bot.exceptions import ReleaseException, GitException
from release_bot.utils import (
    insert_in_changelog,
    parse_changelog,
    look_for_version_files,
    GitService,
    which_service,
)
import jwt
import requests
from semantic_version import Version
from ogr.abstract import PRStatus

logger = logging.getLogger('release-bot')


# github app auth code "stolen" from https://github.com/swinton/github-app-demo.py
class JWTAuth(requests.auth.AuthBase):
    def __init__(self, iss, key, expiration=10 * 60):
        self.iss = iss
        self.key = key
        self.expiration = expiration

    def generate_token(self):
        # Generate the JWT
        payload = {
            # issued at time
            'iat': int(time.time()),
            # JWT expiration time (10 minute maximum)
            'exp': int(time.time()) + self.expiration,
            # GitHub App's identifier
            'iss': self.iss
        }

        tok = jwt.encode(payload, self.key, algorithm='RS256')

        return tok.decode('utf-8')

    def __call__(self, r):
        r.headers['Authorization'] = 'bearer {}'.format(self.generate_token())
        return r


class GitHubApp:
    def __init__(self, app_id, private_key_path):
        self.session = requests.Session()
        self.session.headers.update(dict(
            accept='application/vnd.github.machine-man-preview+json'))
        self.private_key = None
        self.private_key_path = private_key_path
        self.session.auth = JWTAuth(iss=app_id, key=self.read_private_key())
        self.domain = 'api.github.com'  # not sure if it makes sense to make this configurable

    def _request(self, method, path):
        response = self.session.request(method, 'https://{}/{}'.format(self.domain, path))
        return response.json()

    def _get(self, path):
        return self._request('GET', path)

    def _post(self, path):
        return self._request('POST', path)

    def read_private_key(self):
        if self.private_key is None:
            with open(self.private_key_path) as fp:
                self.private_key = fp.read()
        return self.private_key

    def get_app(self):
        return self._get('app')

    def get_installations(self):
        return self._get('app/installations')

    def get_installation_access_token(self, installation_id):
        return self._post('installations/{}/access_tokens'.format(installation_id))["token"]


class Github:

    def __init__(self, configuration, git):
        """
        :param configuration: instance of Configuration
        :param git: instance of Git
        """
        self.conf = configuration
        self.logger = configuration.logger
        self.project = configuration.project
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'token {configuration.github_token}'})
        self.github_app_session = None
        if self.conf.github_app_installation_id and self.conf.github_app_id and self.conf.github_app_cert_path:
            self.github_app_session = requests.Session()
            self.github_app = GitHubApp(self.conf.github_app_id, self.conf.github_app_cert_path)
            self.update_github_app_token()
        self.comment = []
        self.git = git

    def update_github_app_token(self):
        token = self.github_app.get_installation_access_token(self.conf.github_app_installation_id)
        self.logger.debug("github app token obtained")
        self.github_app_session.headers.update({'Authorization': f'token {token}'})

    def latest_release(self):
        """
        Get the latest project release number on Github

        :return: Release number or 0.0.0
        """
        releases = self.project.get_releases()
        if not releases:
            self.logger.debug("There is no github release")
            return '0.0.0'

        release_versions = [release.title for release in releases]
        release_versions.sort(key=Version)
        return release_versions[-1]

    def walk_through_prs(self, pr_status):
        """
        Searches merged pull requests

        :param pr_status: ogr.abstract.PRStatus
        :return: list of merged prs
        """
        return self.project.get_pr_list(pr_status)

    def make_new_release(self, new_release):
        """
        Makes new release to Github.

        :param new_release: version number of the new release
        :return: tuple (released, new_release) - released is bool, new_release contains info about
                 the new release
        """
        try:
            self.project.create_release(
                tag=new_release.version,
                name=new_release.version,
                message=self.get_changelog(new_release.version)
            )
        except Exception:
            msg = f"Failed to create new release on github!"
            raise ReleaseException(msg)

        return True, new_release

    def get_changelog(self, new_version):
        """
        Get changelog for new version

        :param new_version: version number
        :return:
        """
        self.git.fetch_tags()
        self.git.checkout(f'{new_version}-release')
        self.git.pull_branch(f'{new_version}-release')
        p = os.path.join(self.git.repo_path, "CHANGELOG.md")
        try:
            with open(p, "r") as fd:
                changelog_content = fd.read()
        except FileNotFoundError:
            logger.info("CHANGELOG.md not found")
            return ''
        finally:
            self.git.checkout('master')

        changelog = parse_changelog(new_version, changelog_content)
        latest_release = self.project.get_latest_release()

        # check if the changelog needs updating
        if latest_release.body == changelog:
            return ''

        return changelog

    def branch_exists(self, branch):
        """
        Check if branch already exists
        :param branch: name of the branch
        :return: True if exists, False if not
        """
        return branch in self.project.get_branches()

    def make_pr(self, branch, version, log, changed_version_files, base='master', labels=None):
        """
        Makes a pull request with info on the new release
        :param branch: name of the branch to make PR from
        :param version: version that is being released
        :param log: changelog
        :param changed_version_files: list of files that have been changed
                                      in order to update version
        :param base: base of the PR. 'master' by default
        :param labels: list of str, labels to be put on PR
        :return: url of the PR
        """
        message = (f'Hi,\n you have requested a release PR from me. Here it is!\n'
                   f'This is the changelog I created:\n'
                   f'### Changes\n{log}\n\nYou can change it by editing `CHANGELOG.md` '
                   f'in the root of this repository and pushing to `{branch}` branch'
                   f' before merging this PR.\n')
        if len(changed_version_files) == 1:
            message += 'I have also updated the  `__version__ ` in file:\n'
        elif len(changed_version_files) > 1:
            message += ('There were multiple files where  `__version__ ` was set, '
                        'so I left updating them up to you. These are the files:\n')
        elif not changed_version_files:
            message += "I didn't find any files where  `__version__` is set."

        for file in changed_version_files:
            message += f'* {file}\n'

        try:
            new_pr = self.project.pr_create(
                title=f'{version} release',
                body=message,
                target_branch=base,
                source_branch=branch
            )

            self.logger.info(f"Created PR: {new_pr}")
            if labels and which_service(self.project) == GitService.Github:
                # ogr-lib implements labeling only for Github labels
                self.project.add_pr_labels(new_pr.id, labels=labels)
            return new_pr.url
        except Exception:
            msg = (f"Something went wrong with creating "
                   f"PR on {which_service(self.project).name}")
            raise ReleaseException(msg)

    def make_release_pr(self, new_pr, gitchangelog):
        """
        Makes the steps to prepare new branch for the release PR,
        like generating changelog and updating version
        :param new_pr: object of class new_pr with info about the new release
        :param gitchangelog: bool, use gitchangelog
        :return: True on success, False on fail
        """
        repo = new_pr.repo
        version = new_pr.version
        branch = f'{version}-release'
        if self.branch_exists(branch):
            self.logger.warning(f'Branch {branch} already exists, aborting creating PR.')
            return False
        if self.conf.dry_run:
            msg = (f"I would make a new PR for release of version "
                   f"{version} based on the issue.")
            self.logger.info(msg)
            return False
        try:
            name, email = self.get_user_contact()
            repo.set_credentials(name, email)
            repo.set_credential_store()
            # The bot first checks out the master branch and from master
            # it creates the new branch, checks out to it and then perform the release
            # This makes sure that the new release_pr branch has all the commits
            # from the master branch for the latest release.
            repo.checkout('master')
            changelog = repo.get_log_since_last_release(new_pr.previous_version, gitchangelog)
            repo.checkout_new_branch(branch)
            changed = look_for_version_files(repo.repo_path, new_pr.version)
            if insert_in_changelog(f'{repo.repo_path}/CHANGELOG.md',
                                   new_pr.version, changelog):
                repo.add(['CHANGELOG.md'])
            if changed:
                repo.add(changed)
            repo.commit(f'{version} release', allow_empty=True)
            repo.push(branch)
            if not self.pr_exists(f'{version} release'):
                new_pr.pr_url = self.make_pr(branch=branch,
                                             version=f'{version}',
                                             log=changelog,
                                             changed_version_files=changed,
                                             labels=new_pr.labels)
                return True
        except GitException as exc:
            raise ReleaseException(exc)
        finally:
            repo.checkout('master')
        return False

    def pr_exists(self, name):
        """
        Makes a call to github api to check if PR already exists
        :param name: name of the PR
        :return: PR number if exists, False if not
        """
        opened_prs = self.walk_through_prs(PRStatus.open)

        if not opened_prs:
            self.logger.debug(f'No merged release PR found')
            return False

        for opened_pr in opened_prs:
            match = re.match(name, opened_pr.title.lower())
            if match:
                return opened_pr.id

    def get_user_contact(self):
        """
        Get user's contact details
        :return: name and email
        """
        name = 'Release bot'
        mail = 'bot@releasebot.bot'

        # don't set in case of Github app instance, it uses defaults
        if self.conf.github_app_id == '':
            if which_service(self.project) == GitService.Github:
                name = self.project.service.user.get_username()
                mail = self.project.service.user.get_email()
        return name, mail

    def get_file(self, name):
        """
        Fetches a specific file via Github API
        @:param: str, name of the file
        :return: file content or None in case of error
        """
        self.logger.debug(f'Fetching {name}')
        try:
            file = self.project.get_file_content(path=name)
        except FileNotFoundError:
            self.logger.error(f'Failed to fetch {name}')
            return None

        return file
