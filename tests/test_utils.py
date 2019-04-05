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
"""Tests utility functions"""

from semantic_version import Version
from release_bot.utils import (process_version_from_title,
                               look_for_version_files)


def test_process_version_from_title():
    """Test converting title into version as per SemVer versioning"""
    latest_version = Version("0.0.1")

    title = '3.7.8 release'
    match, version = process_version_from_title(title, latest_version)
    assert version == "3.7.8"
    assert match is True
    title = 'new major release'
    match, version = process_version_from_title(title, latest_version)
    assert version == "1.0.0"
    assert match is True
    title = 'new minor release'
    match, version = process_version_from_title(title, latest_version)
    assert version == "0.1.0"
    assert match is True
    title = 'new patch release'
    match, version = process_version_from_title(title, latest_version)
    assert version == "0.0.2"
    assert match is True
    title = 'random release'
    match, version = process_version_from_title(title, latest_version)
    assert version == ""
    assert match is False


def test_look_for_version_files(tmp_path):
    """Test finding the correct files with all possible version variables"""
    dir1 = tmp_path / "subdir"
    dir1.mkdir()

    file1 = dir1 / "__init__.py"
    file1.write_text('__version__="1.2.3"')

    assert look_for_version_files(str(dir1), "1.2.4") == ["__init__.py"]

    file2 = dir1 / "setup.py"
    file2.write_text('version="1.2.3"')

    assert look_for_version_files(str(dir1), "1.2.4") == ["setup.py"]

    assert set(look_for_version_files(str(dir1), "1.2.5")) == {"setup.py",
                                                          "__init__.py"}
