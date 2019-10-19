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
""" Tests parts of bot workflow"""
import os
import warnings
from pathlib import Path

import pytest
import yaml
from flexmock import flexmock

from ogr.abstract import PRComment

from release_bot.releasebot import ReleaseBot
from release_bot.utils import GitService, which_service, which_username
from tests.conftest import prepare_conf

from .github_utils import RELEASE_CONF, GithubUtils

DEFAULT_REFRESH_INTERVAL = 1


@pytest.mark.skipif(not os.environ.get('GITHUB_TOKEN'),
                    reason="missing GITHUB_TOKEN environment variable")
class TestBot:
    """ Tests parts of bot workflow"""

    def setup_method(self):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        configuration = prepare_conf()

        self.g_utils = GithubUtils()
        self.github_user = self.g_utils.github_user

        self.g_utils.create_repo()
        self.g_utils.setup_repo()

        # set conf
        configuration.repository_name = self.g_utils.repo
        configuration.repository_owner = self.github_user
        configuration.github_username = self.github_user
        configuration.clone_url = f'https://github.com/{self.github_user}/{self.g_utils.repo}.git'
        configuration.refresh_interval = DEFAULT_REFRESH_INTERVAL 
        configuration.project = configuration.get_project()

        self.release_bot = ReleaseBot(configuration)

    def teardown_method(self):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        if self.g_utils.repo:
            try:
                self.g_utils.delete_repo()
            except Exception as ex:
                # no need to fail the test, just warn
                warnings.warn(f"Could not delete repository {self.g_utils.repo}: {ex!r}")

    @pytest.fixture()
    def open_issue(self):
        """Opens release issue in a repository"""
        return self.g_utils.open_issue("0.0.1 release")

    @pytest.fixture()
    def multiple_release_issues(self):
        """Opens two release issues in a repository"""
        self.g_utils.open_issue("0.0.1 release")
        self.g_utils.open_issue("0.0.2 release")

    def open_pr(self):
        """Opens two release issues in a repository"""
        conf = yaml.safe_load(RELEASE_CONF) or {}
        self.release_bot.new_release.update(
            changelog=conf.get('changelog'),
            author_name=conf.get('author_name'),
            author_email=conf.get('author_email'),
            pypi=conf.get('pypi'),
            trigger_on_issue=conf.get('trigger_on_issue'),
            labels=conf.get('labels')
        )
        self.g_utils.open_issue("0.0.1 release")
        self.release_bot.find_open_release_issues()
        # Testing dry-run mode
        self.release_bot.conf.dry_run = True
        assert not self.release_bot.make_release_pull_request()
        self.release_bot.conf.dry_run = False
        self.release_bot.make_release_pull_request()
        pr_number = self.release_bot.github.pr_exists("0.0.1 release")
        assert pr_number and self.g_utils.merge_pull_request(pr_number)

    @pytest.fixture()
    def open_pr_fixture(self):
        self.open_pr()

    @pytest.fixture()
    def github_release(self):
        """Setups environment for releasing on Github"""
        self.open_pr()
        assert self.release_bot.find_newest_release_pull_request()
        self.release_bot.make_new_github_release()
        assert self.release_bot.github.latest_release() == "0.0.1"

    @pytest.fixture()
    def mock_upload(self):
        """Mocks upload to PyPi"""
        flexmock(self.release_bot.pypi, upload=True)

    @pytest.fixture()
    def mock_get_latest_version(self):
        flexmock(self.release_bot.pypi, latest_version=lambda: "0.0.0")

    def test_load_release_conf(self):
        """Tests loading release configuration from repository"""
        self.release_bot.load_release_conf()
        conf = yaml.safe_load(RELEASE_CONF) or {}
        if conf.get('pypi') is None:
            conf['pypi'] = True
        for key, value in conf.items():
            assert getattr(self.release_bot.new_release, key) == value

    def test_git_service(self):
        git_service = self.release_bot.git_service
        assert git_service == GitService.Github

    def test_which_service(self):
        git_service = which_service(self.release_bot.project)
        assert git_service == GitService.Github

    def test_which_username(self):
        git_username = which_username(self.release_bot.conf)
        assert git_username == self.github_user
        assert git_username == self.release_bot.conf.github_username

    def test_find_open_rls_issue(self, open_issue):
        """Tests if bot can find opened release issue"""
        assert self.release_bot.find_open_release_issues()
        assert self.release_bot.new_pr.version == '0.0.1'
        assert self.release_bot.new_pr.issue_number == open_issue

    def test_find_open_rls_issue_none(self):
        """Tests if bot can find opened release issue"""
        assert not self.release_bot.find_open_release_issues()

    def test_find_open_rls_issue_more(self, multiple_release_issues):
        """Tests if bot can find opened release issue"""
        assert not self.release_bot.find_open_release_issues()

    def test_pr_from_issue(self, open_issue):
        """Tests if bot can make a pull request from release issue"""
        self.release_bot.load_release_conf()
        self.release_bot.find_open_release_issues()
        assert self.release_bot.make_release_pull_request()
        assert self.release_bot.github.pr_exists("0.0.1 release")

    def test_github_release(self, open_pr_fixture):
        """Tests releasing on Github"""
        assert self.release_bot.find_newest_release_pull_request()
        # Testing dry-run mode
        self.release_bot.conf.dry_run = True
        assert self.release_bot.make_new_github_release() is None
        self.release_bot.conf.dry_run = False
        self.release_bot.make_new_github_release()
        assert self.release_bot.github.latest_release() == "0.0.1"

    def test_pypi_release(self, mock_upload, github_release, mock_get_latest_version):
        """Test PyPi release"""
        self.release_bot.load_release_conf()
        # Testing dry-run mode
        self.release_bot.conf.dry_run = True
        assert not self.release_bot.make_new_pypi_release()
        self.release_bot.conf.dry_run = False
        assert self.release_bot.make_new_pypi_release()
        path = Path(self.release_bot.git.repo_path)
        assert list(path.glob(f'dist/release_bot_test_{self.g_utils.random_string}-0.0.1-py3*.whl'))
        assert (path / f'dist/release_bot_test_{self.g_utils.random_string}-0.0.1.tar.gz').is_file()
        self.release_bot.new_release.pypi = False
        assert not self.release_bot.make_new_pypi_release()

    @pytest.mark.timeout(max(30, DEFAULT_REFRESH_INTERVAL))
    def test_run_once(self):
        """Test that the bot runs only once and exits."""
        flexmock(self.release_bot.conf, refresh_interval=None)

        (flexmock(self.release_bot.project)  # make sure it interes the loop
         .should_receive('pr_comment')
         .once()
         .and_return(PRComment("Fake comment", "FakeAuthor"))
        )
        self.release_bot.run()
