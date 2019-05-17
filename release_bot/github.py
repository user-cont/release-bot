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
from release_bot.utils import insert_in_changelog, parse_changelog, look_for_version_files

import jwt
import requests


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
    API_ENDPOINT = "https://api.github.com/graphql"
    API3_ENDPOINT = "https://api.github.com/"

    def __init__(self, configuration, git):
        """
        :param configuration: instance of Configuration
        :param git: instance of Git
        """
        self.conf = configuration
        self.logger = configuration.logger
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

    def do_request(self, query=None, method=None, json_payload=None, url=None, use_github_auth=False):
        """
        a single wrapper to make any type of request:

        * query using graphql
        * a request with selected method and json payload
        * utilizing both tokens: github app and user token

        this method returns requests.Response so that methods can play with return code

        :param query:
        :param method:
        :param json_payload:
        :param url:
        :param use_github_auth: auth as github app, not as user (default is user)
        :return: requests.Response
        """
        if query:
            self.logger.debug(f'query = {query}')
            if use_github_auth and self.github_app_session:
                response = self.github_app_session.post(url=self.API_ENDPOINT, json={'query': query})
            else:
                response = self.session.post(url=self.API_ENDPOINT, json={'query': query})
            if response.status_code == 401 and self.github_app_session:
                self.update_github_app_token()
                response = self.github_app_session.post(url=self.API_ENDPOINT, json={'query': query})
        elif method and url:
            self.logger.debug(f'{method} {url}')
            if use_github_auth and self.github_app_session:
                response = self.github_app_session.request(method=method, url=url, json=json_payload)
            else:
                response = self.session.request(method=method, url=url, json=json_payload)
            if response.status_code == 401 and self.github_app_session:
                self.update_github_app_token()
                response = self.github_app_session.request(method=method, url=url, json=json_payload)
            if not response.ok:
                self.logger.error(f"error message: {response.content}")
        else:
            raise RuntimeError("please specify query or both method and url")
        return response

    def query_repository(self, query):
        """
        Query a Github repo using GraphQL API

        :param query: str
        :return: requests.Response
        """
        repo_query = (f'query {{repository(owner: "{self.conf.repository_owner}", '
                      f'name: "{self.conf.repository_name}") {{{query}}}}}')
        return self.do_request(query=repo_query)

    def add_comment(self, subject_id):
        """Add self.comment to subject_id issue/PR"""
        if not subject_id or not self.comment:
            return
        if self.conf.dry_run:
            self.logger.info("I would add a comment to the pull request created.")
            return None
        comment = '\n'.join(self.comment)
        mutation = (f'mutation {{addComment(input:'
                    f'{{subjectId: "{subject_id}", body: "{comment}"}})' +
                    '''{
                         subject {
                           id
                         }
                       }}''')
        response = self.do_request(query=mutation, use_github_auth=True).json()
        self.detect_api_errors(response)
        self.logger.debug(f'Comment added to PR: {comment}')
        self.comment = []  # clean up
        return response

    @staticmethod
    def detect_api_errors(response):
        """This function looks for errors in API response"""
        msg = '\n'.join((err['message'] for err in response.get('errors', [])))
        if msg:
            raise ReleaseException(msg)

    def latest_release(self, cursor=''):
        """
        Get the latest project release number on Github. Ignores drafts and pre releases

        :return: Release number or 0.0.0
        """
        query = (f"releases(last: 1 " +
                 (f'before:"{cursor}"' if cursor else '') +
                 '''){
                        edges{
                         cursor
                         node {
                           isPrerelease
                           isDraft
                           tagName
                        }
                       }
                     }
                 ''')
        response = self.query_repository(query).json()
        self.detect_api_errors(response)

        # check for empty response
        edges = response['data']['repository']['releases']['edges']
        if not edges:
            self.logger.debug("There is no github release")
            return '0.0.0'

        release = edges[0]['node']
        # check for pre-release / draft
        if release['isPrerelease'] or release['isDraft']:
            self.logger.debug("Latest github release is a Prerelease/Draft")
            return self.latest_release(cursor=edges[0]['cursor'])

        return release["tagName"]

    def walk_through_prs(self, start='', direction='after', which="last", closed=True):
        """
        Searches merged pull requests

        :param start: A cursor to start at
        :param direction: Direction to go from cursor, can be 'after' or 'before'
        :param which: Indicates which part of the result list
                      should be returned, can be 'first' or 'last'
        :param closed: filters PRs by state (closed/open). True by default
        :return: edges from API query response
        """
        state = 'MERGED' if closed else 'OPEN'
        while True:
            query = (f"pullRequests(states: {state} {which}: 5 " +
                     (f'{direction}: "{start}"' if start else '') +
                     '''){
                  edges {
                    cursor
                    node {
                      id
                      title
                      number
                      mergeCommit {
                        oid
                        author {
                            name
                            email
                        }
                      }
                    }
                  }
                }''')
            response = self.query_repository(query).json()
            self.detect_api_errors(response)
            return response['data']['repository']['pullRequests']['edges']

    def walk_through_open_issues(self, start='', direction='after', which="last"):
        """
        Searches open issues for a release trigger

        :return: edges from API query response
        """
        while True:
            query = (f"issues(states: OPEN {which}: 5 " +
                     (f'{direction}: "{start}"' if start else '') +
                     '''){
                  edges {
                    cursor
                    node {
                      id
                      number
                      title
                      authorAssociation
                    }
                  }
                }''')
            response = self.query_repository(query).json()
            self.detect_api_errors(response)
            return response['data']['repository']['issues']['edges']

    def make_new_release(self, new_release):
        """
        Makes new release to Github.
        This has to be done using github api v3 because v4 (GraphQL) doesn't support this yet

        :param new_release: version number of the new release
        :return: tuple (released, new_release) - released is bool, new_release contains info about
                 the new release
        """
        payload = {"tag_name": new_release.version,
                   "target_commitish": new_release.commitish,
                   "name": new_release.version,
                   "prerelease": False,
                   "draft": False}
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/releases")
        self.logger.debug(f"About to release {new_release.version} on Github")
        response = self.do_request(method="POST", url=url, json_payload=payload, use_github_auth=True)
        if response.status_code != 201:
            msg = f"Failed to create new release on github:\n{response.text}"
            raise ReleaseException(msg)
        return True, new_release

    def update_changelog(self, new_version):
        self.git.fetch_tags()
        self.git.checkout(new_version)
        # FIXME: make the file name configurable
        p = os.path.join(self.git.repo_path, "CHANGELOG.md")
        try:
            with open(p, "r") as fd:
                changelog_content = fd.read()
        except FileNotFoundError:
            logger.info("CHANGELOG.md not found")
            return
        finally:
            self.git.checkout('master')

        # get latest release
        changelog = parse_changelog(new_version, changelog_content)
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/releases/latest")
        latest_release = self.do_request(method="GET", url=url, use_github_auth=True).json()

        # check if the changelog needs updating
        if latest_release["body"] == changelog:
            return

        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/releases/{latest_release['id']}")
        response = self.do_request(method="POST", url=url, json_payload={'body': changelog}, use_github_auth=True)
        if response.status_code != 200:
            self.logger.error((f"Something went wrong during changelog "
                               f"update for {new_version}:\n{response.text}"))

    def branch_exists(self, branch):
        """
        Makes a call to github api to check if branch already exists
        :param branch: name of the branch
        :return: True if exists, False if not
        """
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/branches/{branch}")
        response = self.do_request(method="GET", url=url)
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            self.logger.debug(response.text)
            return False
        else:
            msg = f"Unexpected response code from Github:\n{response.text}"
            raise ReleaseException(msg)

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

        payload = {'title': f'{version} release',
                   'head': branch,
                   'base': base,
                   'body': message,
                   'maintainer_can_modify': True}
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/pulls")
        self.logger.debug(f'Attempting a PR for {branch} branch')
        response = self.do_request(method="POST", url=url, json_payload=payload, use_github_auth=True)
        if response.status_code == 201:
            parsed = response.json()
            self.logger.info(f"Created PR: {parsed['html_url']}")

            # put labels on PR
            if labels is not None:
                self.put_labels_on_issue(parsed['number'], labels)

            return parsed['html_url']
        else:
            msg = (f"Something went wrong with creating "
                   f"PR on github:\n{response.text}")
            raise ReleaseException(msg)

    def make_release_pr(self, new_pr):
        """
        Makes the steps to prepare new branch for the release PR,
        like generating changelog and updating version
        :param new_pr: dict with info about the new release
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
            # from the master branch for the lastest release.
            repo.checkout('master')
            changelog = repo.get_log_since_last_release(new_pr.previous_version)
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
                new_pr.pr_url = self.make_pr(branch, f'{version}', changelog, changed,
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
        cursor = ''
        while True:
            edges = self.walk_through_prs(start=cursor, direction='before', closed=False)
            if not edges:
                self.logger.debug(f"No open PR's found")
                return False

            for edge in reversed(edges):
                cursor = edge['cursor']
                match = re.match(name, edge['node']['title'].lower())
                if match:
                    return edge['node']['number']

    def get_user_contact(self):
        """
        Makes a call to github api to get user's contact details
        :return: name and email
        """
        query = (f'query {{user(login: "{self.conf.github_username}")'
                 '''  {
                     email
                     name
                   }
                 }''')
        response = self.do_request(query=query).json()
        self.detect_api_errors(response)
        name = response['data']['user']['name']
        email = response['data']['user']['email']
        if not name:
            name = 'Release bot'
        if not email:
            email = 'bot@releasebot.bot'
        return name, email

    def close_issue(self, number):
        """
        Close an github issue
        :param number: number of the issue in repository
        :return: True on success, False on fail
        """
        payload = {'state': 'closed'}
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/issues/{number}")
        self.logger.debug(f'Attempting to close issue #{number}')
        response = self.do_request(method='PATCH', url=url, json_payload=payload, use_github_auth=True)
        if response.status_code == 200:
            self.logger.debug(f'Closed issue #{number}')
            return True
        self.logger.error(f'Failed to close issue #{number}')
        return False

    def put_labels_on_issue(self, number, labels):
        """
        Put labels on Github issue or PR
        :param number: number of issue/PR
        :param labels: list of str
        :return: True on success, False on fail
        """
        if self.conf.dry_run:
            self.logger.info("I would add labels to issue #%s", number)
            return False
        payload = {'labels': labels}
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/issues/{number}")
        self.logger.debug(f'Attempting to put labels on issue/PR #{number}')
        response = self.do_request(method='PATCH', url=url,
                                   json_payload=payload, use_github_auth=True)
        if response.status_code == 200:
            self.logger.debug(f'Following labels: #{",".join(labels)} put on issue #{number}:')
            return True
        self.logger.error(f'Failed to put labels on issue #{number}')
        return False

    def get_file(self, name):
        """
        Fetches a specific file via Github API
        :return: file content or None in case of error
        """
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/contents/{name}")
        self.logger.debug(f'Fetching {name}')
        response = self.do_request(url=url, method='GET')
        if response.status_code != 200:
            self.logger.error(f'Failed to fetch {name}')
            return None

        parsed = response.json()
        download_url = parsed['download_url']
        response = requests.get(url=download_url)
        if response.status_code != 200:
            self.logger.error(f'Failed to fetch {name}')
            return None

        return response.text
