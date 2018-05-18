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
import requests
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from .exceptions import ReleaseException
from .utils import parse_changelog


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

    def latest_release(self):
        """
        Get the latest project release number on Github

        :return: Release number or None
        """
        query = '''url
                releases(last: 1) {
                    nodes {
                      id
                      isPrerelease
                      isDraft
                      name
                  }
                }
            '''
        response = self.query_repository(query).json()
        self.detect_api_errors(response)

        # check for empty response
        nodes = response['data']['repository']['releases']['nodes']
        if not nodes:
            self.logger.debug("There is no github release")
            return None

        release = nodes[0]
        # check for pre-release / draft
        if release['isPrerelease'] or release['isDraft']:
            self.logger.debug("Latest github release is a Prerelease/Draft")
            return None

        return release['name']

    def walk_through_closed_prs(self, start='', direction='after', which="last"):
        """
        Searches merged pull requests

        :param start: A cursor to start at
        :param direction: Direction to go from cursor, can be 'after' or 'before'
        :param which: Indicates which part of the result list
                      should be returned, can be 'first' or 'last'
        :return: edges from API query response
        """
        while True:
            query = (f"pullRequests(states: MERGED {which}: 5 " +
                     (f'{direction}: "{start}"' if start else '') +
                     '''){
                  edges {
                    cursor
                    node {
                      id
                      title
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

    def make_new_release(self, new_release, previous_pypi_release):
        """
        This has to be done using github api v3 because v4 (GraphQL) doesn't support this yet

        :param new_release:
        :param previous_pypi_release:
        :return:
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
            response_get = requests.get(url=url, headers=self.headers)
            if (response_get.status_code == 200 and
                    [r for r in response_get.json() if r.get('name') == new_release['version']]):
                self.logger.info(f"{new_release['version']} has already been released on Github")
                # to fill in new_release['fs_path'] so that we can continue with PyPi upload
                new_release = self.download_extract_zip(new_release)
                released = False
            else:
                msg = (f"Something went wrong with creating "
                       f"new release on github:\n{response.text}")
                raise ReleaseException(msg)
        else:
            released = True
            new_release = self.download_extract_zip(new_release)
            self.update_changelog(previous_pypi_release,
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

    def update_changelog(self, previous_pypi_release, new_version, fs_path, id_):
        # parse changelog and update the release with it
        changelog = parse_changelog(previous_pypi_release, new_version, fs_path)
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/releases/{id_!s}")
        response = requests.post(url=url, json={'body': changelog}, headers=self.headers)
        if response.status_code != 200:
            self.logger.error((f"Something went wrong during changelog "
                               f"update for {new_version}:\n{response.text}"))
