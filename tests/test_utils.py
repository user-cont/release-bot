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
from release_bot.utils import process_version_from_title


def test_process_version_from_title():
    """Test converting title into version as per SemVer versioning"""
    latest_version = Version("0.0.1")

    title = '3.7.8 release'
    match, version = process_version_from_title(title,latest_version)
    assert version == "3.7.8"
    assert match == True
    title = 'new major release'
    match, version = process_version_from_title(title,latest_version)
    assert version == "1.0.0"
    assert match == True
    title = 'new minor release'
    match, version = process_version_from_title(title,latest_version)
    assert version == "0.1.0"
    assert match == True
    title = 'new patch release'
    match, version = process_version_from_title(title,latest_version)
    assert version == "0.0.2"
    assert match == True
    title = 'random release'
    match, version = process_version_from_title(title,latest_version)
    assert version == ""
    assert match == False
