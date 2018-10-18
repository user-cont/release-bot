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

from os import listdir
import re
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import requests

from release_bot.git import Git
from release_bot.exceptions import ReleaseException, GitException
from release_bot.utils import insert_in_changelog, parse_changelog, look_for_version_files


class Github:
    API_ENDPOINT = "https://api.github.com/graphql"
    API3_ENDPOINT = "https://api.github.com/"

    def __init__(self, configuration):
        self.conf = configuration
        self.logger = configuration.logger
        self.headers = {'Authorization': f'token {configuration.github_token}'}
        self.comment = []

    def send_query(self, query):
        """Send query to Github v4 API and return the response"""
        return requests.post(url=self.API_ENDPOINT, json={'query': query}, headers=self.headers)

    def query_repository(self, query):
        """Query Github repository"""
        repo_query = (f'query {{repository(owner: "{self.conf.repository_owner}", '
                      f'name: "{self.conf.repository_name}") {{{query}}}}}')
        return self.send_query(repo_query)

    def add_comment(self, subject_id):
        """Add self.comment to subject_id issue/PR"""
        if not subject_id or not self.comment:
            return
        comment = '\n'.join(self.comment)
        mutation = (f'mutation {{addComment(input:'
                    f'{{subjectId: "{subject_id}", body: "{comment}"}})' +
                    '''{
                         subject {
                           id
                         }
                       }}''')
        response = self.send_query(mutation).json()
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
                           name
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

        return release['name']

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
        payload = {"tag_name": new_release['version'],
                   "target_commitish": new_release['commitish'],
                   "name": new_release['version'],
                   "prerelease": False,
                   "draft": False}
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/releases")
        self.logger.debug(f"About to release {new_release['version']} on Github")
        response = requests.post(url=url, headers=self.headers, json=payload)
        if response.status_code != 201:
            msg = f"Failed to create new release on github:\n{response.text}"
            raise ReleaseException(msg)

        released = True
        new_release = self.download_extract_zip(new_release)
        self.update_changelog(self.latest_release(),
                              new_release['version'], new_release['fs_path'],
                              response.json()['id'])
        return released, new_release

    def download_extract_zip(self, new_release):
        url = f"https://github.com/{self.conf.repository_owner}/{self.conf.repository_name}/" \
              f"archive/{new_release['version']}.zip"

        # download the new release to a temporary directory
        temp_directory = TemporaryDirectory()
        new_release['tempdir'] = temp_directory
        response = requests.get(url=url)
        path = temp_directory.name + '/' + new_release['version']

        # extract it
        open(path + '.zip', 'wb').write(response.content)
        archive = ZipFile(path + '.zip')
        archive.extractall(path=path)
        dirs = listdir(path)
        new_release['fs_path'] = path + "/" + dirs[0]

        return new_release

    def update_changelog(self, previous_release, new_version, fs_path, id_):
        # parse changelog and update the release with it
        changelog = parse_changelog(previous_release, new_version, fs_path)
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/releases/{id_!s}")
        response = requests.post(url=url, json={'body': changelog}, headers=self.headers)
        if response.status_code != 200:
            self.logger.error((f"Something went wrong during changelog "
                               f"update for {new_version}:\n{response.text}"))

    def clone_repository(self):
        """
        Clones repository from configuration
        :return: Git object with cloned repository
        """
        url = f'https://github.com/{self.conf.repository_owner}/{self.conf.repository_name}.git'
        return Git(url, self.conf)

    def branch_exists(self, branch):
        """
        Makes a call to github api to check if branch already exists
        :param branch: name of the branch
        :return: True if exists, False if not
        """
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/branches/{branch}")
        response = requests.get(url=url, headers=self.headers)
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
        response = requests.post(url=url, headers=self.headers, json=payload)
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
        repo = new_pr['repo']
        version = new_pr['version']
        branch = f'{version}-release'
        if self.branch_exists(branch):
            self.logger.warning(f'Branch {branch} already exists, aborting creating PR.')
            return False
        try:
            name, email = self.get_user_contact()
            repo.set_credentials(name, email)
            repo.set_credential_store()
            changelog = repo.get_log_since_last_release(new_pr['previous_version'])
            repo.checkout_new_branch(branch)
            changed = look_for_version_files(repo.repo_path, new_pr['version'])
            if insert_in_changelog(f'{repo.repo_path}/CHANGELOG.md',
                                   new_pr['version'], changelog):
                repo.add(['CHANGELOG.md'])
            if changed:
                repo.add(changed)
            repo.commit(f'{version} release', allow_empty=True)
            repo.push(branch)
            if not self.pr_exists(f'{version} release'):
                new_pr['pr_url'] = self.make_pr(branch, f'{version}', changelog, changed,
                                                labels=new_pr.get('labels'))
                return True
        except GitException as exc:
            raise ReleaseException(exc)
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
        response = self.send_query(query).json()
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
        response = requests.patch(url=url, headers=self.headers, json=payload)
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
        payload = {'labels': labels}
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/issues/{number}")
        self.logger.debug(f'Attempting to put labels on issue/PR #{number}')
        response = requests.patch(url=url, headers=self.headers, json=payload)
        if response.status_code == 200:
            self.logger.debug(f'Following labels: #{",".join(labels)} put on issue #{number}:')
            return True
        self.logger.error(f'Failed to put labels on issue #{number}')
        return False

    def get_configuration(self):
        """
        Fetches release-conf.yaml via Github API
        :return: release-conf.yaml contents or False in case of error
        """
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/contents/release-conf.yaml")
        self.logger.debug(f'Fetching release-conf.yaml')
        response = requests.get(url=url, headers=self.headers)
        if response.status_code != 200:
            self.logger.error(f'Failed to fetch release-conf.yaml')
            return False

        parsed = response.json()
        download_url = parsed['download_url']
        response = requests.get(url=download_url)
        if response.status_code != 200:
            self.logger.error(f'Failed to fetch release-conf.yaml')
            return False

        return response.text
