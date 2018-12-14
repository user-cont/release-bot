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

import pytest

from release_bot.utils import parse_changelog


class TestChangelog:

    @pytest.fixture
    def empty_changelog(self):
        return ""

    @pytest.fixture
    def changelog_with_one_entry(self):
        return "# 0.0.1\n* Test entry\n* Another test entry\n"

    @pytest.fixture
    def changelog_with_two_entries(self):
        return ("# 0.0.2\n* New entry\n* Fixes\n"
                "# 0.0.1\n* Test entry\n* Another test entry\n")

    @pytest.fixture
    def changelog_with_no_changes(self):
        return ("# 0.0.2\n"
                "# 0.0.1\n* Test entry\n* Another test entry\n")

    def test_no_changelog(self):
        changelog = parse_changelog("2.0.0", "nochangelogpath")
        assert changelog == "No changelog provided"

    def test_empty_changelog(self, empty_changelog):
        changelog = parse_changelog("2.0.0", empty_changelog)
        assert changelog == "No changelog provided"

    def test_one_entry_changelog(self, changelog_with_one_entry):
        changelog = parse_changelog("0.0.1", changelog_with_one_entry)
        assert changelog == "# 0.0.1\n* Test entry\n* Another test entry\n"

    def test_wrong_version(self, changelog_with_one_entry):
        changelog = parse_changelog("0.0.2", changelog_with_one_entry)
        assert changelog == "No changelog provided"

    def test_normal_use_case(self, changelog_with_two_entries):
        changelog = parse_changelog("0.0.2", changelog_with_two_entries)
        assert changelog == "# 0.0.2\n* New entry\n* Fixes"

    def test_no_changes(self, changelog_with_no_changes):
        changelog = parse_changelog("0.0.2", changelog_with_no_changes)
        assert changelog == "# 0.0.2"
