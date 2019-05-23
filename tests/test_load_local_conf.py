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

from pathlib import Path

import pytest
from flexmock import flexmock

from release_bot.configuration import configuration, Configuration


class TestLoadLocalConf:
    """ This class contains tests for loading the release-bot
    configuration from conf.yaml"""

    def setup_method(self):
        """ Setup any state tied to the execution of the given method in a
        class. setup_method is invoked for every test method of a class.
        """
        configuration.set_logging(level=10)
        configuration.debug = True

    def teardown_method(self, method):
        """ Teardown any state that was previously setup with a setup_method
        call.
        """

    @pytest.fixture
    def conf_with_clone_url(self):
        """Returns a valid configuration with clone_url option"""
        return Path(__file__).parent / "src/conf_with_clone_url.yaml"

    @pytest.fixture
    def conf_with_gitchangelog(self):
        """Returns a valid configuration with clone_url option"""
        return Path(__file__).parent / "src/conf_with_gitchangelog.yaml"

    @pytest.fixture
    def sample_conf(self):
        """Return a sample configuration file"""
        return Path(__file__).parent / "src/sample_conf.yaml"

    @pytest.fixture
    def non_existing_conf(self):
        """Return a non-existing configuration file"""
        return ""

    def test_non_existing_conf(self):
        """Test if missing conf.yaml generates an error"""
        flexmock(Path, is_file=lambda: False)
        c = Configuration()
        with pytest.raises(SystemExit) as error:
            c.load_configuration()
        assert error.type == SystemExit
        assert error.value.code == 1    

    def test_conf_with_clone_url(self, conf_with_clone_url):
        """Tests if the user-defined clone_url is loaded"""
        configuration.configuration = conf_with_clone_url
        configuration.load_configuration()
        assert configuration.clone_url == 'https://github.com/test/url.git'

    def test_conf_without_clone_url(self, sample_conf):
        """Tests if default clone_url is used when not specified in conf.yaml"""
        configuration.configuration = sample_conf
        configuration.load_configuration()
        assert configuration.clone_url == 'https://github.com/repo_owner/random_repo.git'

    def test_missing_required_items(self, sample_conf):
        """Tests if missing required items generate an error"""
        old_value = configuration.REQUIRED_ITEMS['conf']
        configuration.REQUIRED_ITEMS['conf'] = ['test-key']
        configuration.configuration = sample_conf
        with pytest.raises(SystemExit) as error:
            configuration.load_configuration()
        configuration.REQUIRED_ITEMS['conf'] = old_value
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_conf_with_gitchangelog(self, conf_with_gitchangelog):
        configuration.configuration = conf_with_gitchangelog
        configuration.load_configuration()
        assert configuration.gitchangelog
