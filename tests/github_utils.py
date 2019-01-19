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
This module provides functions that help test github dependent part of the bot
"""

from pathlib import Path
import string
import base64
import random
import requests
import yaml

API_ENDPOINT = "https://api.github.com/graphql"
API3_ENDPOINT = "https://api.github.com/"

RELEASE_CONF = yaml.dump({"python_versions": [3], "trigger_on_issue": True})


class GithubUtils:
    """Functions to help test github part of the bot"""
    def __init__(self, github_token):
        self.headers = {'Authorization': f'token {github_token}'}
        self.repo = None
        self.random_string = None

        # This token needs github api token scope to delete repositories. If deleting a repo fails with
        # a message saying that you need to be admin for such action it means the token doesn't have it.
        # We suggest creating a new token with such scope:
        #   https://github.com/settings/tokens/new
        self.github_token = github_token
        self.github_user = self.get_username()

    def get_username(self):
        """ Get username for the provided token """
        url = f"{API3_ENDPOINT}user"
        response = requests.get(url=url, headers=self.headers)

        response.raise_for_status()

        return response.json()["login"]

    def create_repo(self):
        """Creates a new github repository with example files"""
        url = f"{API3_ENDPOINT}user/repos"
        self.random_string = ''.join(
            [random.choice(string.ascii_letters + string.digits) for n in range(16)])
        name = 'release-bot-test-' + self.random_string
        payload = {"name": name,
                   "auto_init": True}
        response = requests.post(url=url, headers=self.headers, json=payload)

        if response.status_code != 201:
            raise Exception(f'Failed creating repository {self.github_user}/{name}:'
                            f'\n{response.text}')
        self.repo = name

        return name

    def setup_repo(self):
        """Fills repo with release-conf.yaml and setup.py"""
        self.upload_file_to_github(RELEASE_CONF, 'release-conf.yaml')

        setup = (Path(__file__).parent / "src/example_setup.py.txt").read_text()
        setup = setup.format(name=self.repo.replace('-', '_'),
                             user=self.github_user,
                             repo=self.repo)
        self.upload_file_to_github(setup, 'setup.py')

        init = (Path(__file__).parent / "src/release_bot_test/__init__.py.txt").read_text()
        self.upload_file_to_github(init, 'release_bot_test/__init__.py')

        main = (Path(__file__).parent / "src/release_bot_test/release_bot_test.py.txt").read_text()
        self.upload_file_to_github(main, 'release_bot_test/release_bot_test.py')

    def upload_file_to_github(self, file, path):
        """Uploads file to path in github repository"""
        url = f"{API3_ENDPOINT}repos/{self.github_user}/{self.repo}/contents"
        payload = {"content": base64.b64encode(file.encode('utf-8')).decode('utf-8'),
                   "message": f"Create {path}"}
        response = requests.put(url=f'{url}/{path}', headers=self.headers, json=payload)

        if response.status_code != 201:
            raise Exception(f'Failed creating {path} in {self.github_user}/{self.repo}:'
                            f'\n{response.text}')

    def delete_repo(self):
        """Deletes previously setup github repository"""
        url = f"{API3_ENDPOINT}repos/{self.github_user}/{self.repo}"
        response = requests.delete(url=url, headers=self.headers)

        if response.status_code != 204:
            raise Exception(f'Failed deleting repository {self.github_user}/{self.repo}\n'
                            f'{response.text}')
        self.repo = None

    def open_issue(self, title="Test issue"):
        """Opens issue in a repository"""
        url = f"{API3_ENDPOINT}repos/{self.github_user}/{self.repo}/issues"
        payload = {'title': title}
        response = requests.post(url=url, headers=self.headers, json=payload)

        if response.status_code != 201:
            raise Exception(f'Failed creating issue in repository {self.github_user}/{self.repo}\n'
                            f'{response.text}')
        parsed = response.json()
        return parsed['number']

    def merge_pull_request(self, number):
        """Merges open pull request in a repository"""
        url = f"{API3_ENDPOINT}repos/{self.github_user}/{self.repo}/pulls/{number}/merge"
        response = requests.put(url=url, headers=self.headers)

        if response.status_code != 200:
            raise Exception(f'Failed merging PR #{number} in repository '
                            f'{self.github_user}/{self.repo}\n'
                            f'{response.text}')
        return True

    def count_comments(self, number):
        """Counts comments on issue/PR"""
        url = f"{API3_ENDPOINT}repos/{self.github_user}/{self.repo}/issues/{number}/comments"
        response = requests.get(url=url, headers=self.headers)

        if response.status_code != 200:
            raise Exception(f'Failed counting comments on issue #{number} '
                            f'in repository {self.github_user}/{self.repo}\n'
                            f'{response.text}')
        parsed = response.json()
        return len(parsed)

    @staticmethod
    def github_api_status():
        """Checks status of Github API"""
        url = f"https://status.github.com/api/status.json"
        response = requests.get(url=url)

        if response.status_code != 200:
            return False
        parsed = response.json()
        if parsed['status'] != 'good':
            return False
        return True
