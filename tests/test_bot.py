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

import os
import pytest
import yaml
from flexmock import flexmock
from pathlib import Path

from release_bot.configuration import configuration
from release_bot.releasebot import ReleaseBot
from github_utils import GithubUtils, RELEASE_CONF


@pytest.mark.skipif(not GithubUtils._github_api_status(), reason="Github api is down")
@pytest.mark.skipif(not os.environ.get('GITHUB_TOKEN') and not os.environ.get('GITHUB_USER'),
                    reason="missing GITHUB_TOKEN and GITHUB_USER variables")
class TestBot:
    github_token = os.environ.get('GITHUB_TOKEN')
    github_user = os.environ.get('GITHUB_USER')
    headers = {'Authorization': f'token {github_token}'}

    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        configuration.set_logging(level=10)
        configuration.debug = True

        self.gu = GithubUtils(self.github_token, self.github_user)

        self.gu._create_repo()
        self.gu._setup_repo()

        # set conf
        configuration.repository_name = self.gu.repo
        configuration.repository_owner = self.github_user
        configuration.github_token = self.github_token
        configuration.github_username = self.github_user
        configuration.refresh_interval = 1

        self.rb = ReleaseBot(configuration)

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        if self.gu.repo:
            self.gu._delete_repo()

    @pytest.fixture()
    def open_issue(self):
        """Opens releaseissue in a repository"""
        return self.gu._open_issue("0.0.1 release")

    @pytest.fixture()
    def multiple_release_issues(self):
        """Opens two release issues in a repository"""
        self.gu._open_issue("0.0.1 release")
        self.gu._open_issue("0.0.2 release")

    @pytest.fixture()
    def open_pr(self):
        """Opens two release issues in a repository"""
        conf = yaml.safe_load(RELEASE_CONF) or {}
        self.rb.new_release.update(conf)
        self.open_issue()
        self.rb.find_open_release_issues()
        self.rb.make_release_pull_request()
        pr_number = self.rb.github.pr_exists("0.0.1 release")
        assert pr_number
        assert self.gu._merge_pull_request(pr_number)

    @pytest.fixture()
    def github_release(self):
        self.open_pr()
        assert self.rb.find_newest_release_pull_request()
        self.rb.make_new_github_release()
        assert self.rb.github.latest_release() == "0.0.1"

    @pytest.fixture()
    def mock_upload(self):
        flexmock(self.rb.pypi, upload=True)

    def test_load_release_conf(self):
        self.rb.load_release_conf()
        conf = yaml.safe_load(RELEASE_CONF) or {}
        for key, value in conf.items():
            assert self.rb.new_release[key] == value

    def test_find_open_release_issue(self, open_issue):
        assert self.rb.find_open_release_issues()
        assert self.rb.new_pr['version'] == '0.0.1'
        assert self.rb.new_pr['issue_number'] == open_issue

    def test_find_open_release_issue_no_issue(self):
        assert not self.rb.find_open_release_issues()

    def test_find_open_release_issue_multiple(self, multiple_release_issues):
        assert not self.rb.find_open_release_issues()

    def test_pr_from_issue(self, open_issue):
        self.rb.load_release_conf()
        self.rb.find_open_release_issues()
        assert self.rb.make_release_pull_request()
        assert self.rb.github.pr_exists("0.0.1 release")

    def test_github_release(self, open_pr):
        assert self.rb.find_newest_release_pull_request()
        self.rb.make_new_github_release()
        assert self.rb.github.latest_release() == "0.0.1"

    def test_pypi_release(self, mock_upload, github_release):
        assert self.rb.make_new_pypi_release()
        path = Path(self.rb.new_release['fs_path'])
        assert list(path.glob(f'dist/release_bot_test_{self.gu.random_string}-0.0.1-py3*.whl'))
        assert (path / f'dist/release_bot_test_{self.gu.random_string}-0.0.1.tar.gz').is_file()
