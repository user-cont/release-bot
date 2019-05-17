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

from release_bot.configuration import configuration, Configuration


class TestLoadReleaseConf:

    def setup_method(self):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        configuration.set_logging(level=10)
        configuration.debug = True

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    @pytest.fixture
    def empty_conf(self):
        """
        Emulates an empty configuration
        :return:
        """
        return ""

    @pytest.fixture
    def non_existing_conf(self):
        """
        Emulates missing configuration
        :return:
        """
        return False

    @pytest.fixture
    def valid_new_release(self):
        """
        Emulates valid new_release dict
        :return:
        """
        new_release = {'version': '0.1.0',
                       'commitish': 'xxx',
                       'author_name': 'John Doe',
                       'author_email': 'jdoe@example.com',
                       'changelog': [],
                       'tempdir': None}
        return new_release

    @pytest.fixture
    def missing_items_conf(self):
        """
        Emulates configuration with missing required items
        :return:
        """
        return (Path(__file__).parent / "src/missing_items_conf.yaml").read_text()

    @pytest.fixture
    def missing_author_conf(self):
        """
        Emulates configuration with missing author
        :return:
        """
        return (Path(__file__).parent / "src/missing_author.yaml").read_text()

    @pytest.fixture
    def valid_conf(self):
        """
        Emulates valid configuration
        :return:
        """
        return (Path(__file__).parent / "src/release-conf.yaml").read_text()

    @pytest.fixture
    def different_pypi_name_conf(self):
        """
        Emulates configuration with different pypi project name
        :return:
        """
        return (Path(__file__).parent / "src/different-pypi-name.yaml").read_text()

    def test_empty_conf(self, empty_conf):
        # if there are any required items, this test must fail
        if configuration.REQUIRED_ITEMS['release-conf']:
            with pytest.raises(SystemExit) as error:
                configuration.load_release_conf(empty_conf)
            assert error.type == SystemExit
            assert error.value.code == 1

    def test_non_exiting_conf(self, non_existing_conf):
        # if there are any required items, this test must fail
        if configuration.REQUIRED_ITEMS['release-conf']:
            with pytest.raises(SystemExit) as error:
                configuration.load_release_conf(non_existing_conf)
            assert error.type == SystemExit
            assert error.value.code == 1

    def test_missing_required_items(self, missing_items_conf):
        backup = configuration.REQUIRED_ITEMS['release-conf']
        # set trigger_on_issue as required
        configuration.REQUIRED_ITEMS['release-conf'] = ['trigger_on_issue']
        with pytest.raises(SystemExit) as error:
            configuration.load_release_conf(missing_items_conf)
        assert error.type == SystemExit
        assert error.value.code == 1
        configuration.REQUIRED_ITEMS['release-conf'] = backup

    def test_author_overwrites(self, missing_author_conf, valid_new_release):
        author_name = valid_new_release['author_name']
        author_email = valid_new_release['author_email']

        release_conf = configuration.load_release_conf(missing_author_conf)
        valid_new_release.update(release_conf)

        assert valid_new_release['author_name'] == author_name
        assert valid_new_release['author_email'] == author_email

    def test_normal_use_case(self, valid_conf, valid_new_release):
        # test if all items in configuration are properly loaded
        release_conf = configuration.load_release_conf(valid_conf)
        valid_new_release.update(release_conf)
        assert valid_new_release['changelog'] == ['Example changelog entry',
                                                  'Another changelog entry']
        assert valid_new_release['author_name'] == 'John Smith'
        assert valid_new_release['author_email'] == 'jsmith@example.com'
        assert valid_new_release['labels'] == ['bot', 'release-bot', 'user-cont']

    def test_set_pypi_name_from_release_conf(self, different_pypi_name_conf):
        parsed_conf = configuration.load_release_conf(different_pypi_name_conf)
        configuration.set_pypi_project(parsed_conf)
        assert configuration.pypi_project == "release-botos"

    def test_set_pypi_name_from_setup_cfg(self, valid_conf):
        parsed_conf = configuration.load_release_conf(valid_conf)
        setup_cfg = Path(__file__).parent.joinpath("src/test-setup.cfg").read_text()
        configuration.set_pypi_project(parsed_conf, setup_cfg)
        assert configuration.pypi_project == "release-botos"
