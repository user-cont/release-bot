import release_bot.release_bot as release_bot
import pytest


class TestChangelog:

    @pytest.fixture
    def empty_changelog(self, tmpdir):
        changelog = tmpdir.join("CHANGELOG.md")
        changelog.write("")
        return tmpdir

    @pytest.fixture
    def changelog_with_one_entry(self, tmpdir):
        changelog = tmpdir.join("CHANGELOG.md")
        changelog.write("# 0.0.1\n* Test entry\n* Another test entry\n")
        return tmpdir

    @pytest.fixture
    def changelog_with_two_entries(self, tmpdir):
        changelog = tmpdir.join("CHANGELOG.md")
        changelog.write(("# 0.0.2\n* New entry\n* Fixes\n"
                         "# 0.0.1\n* Test entry\n* Another test entry\n"))
        return tmpdir

    @pytest.fixture
    def changelog_with_no_changes(self, tmpdir):
        changelog = tmpdir.join("CHANGELOG.md")
        changelog.write(("# 0.0.2\n"
                         "# 0.0.1\n* Test entry\n* Another test entry\n"))
        return tmpdir

    def test_no_changelog(self):
        changelog = release_bot.parse_changelog("1.0.0", "2.0.0", "nochangelogpath")
        assert changelog == "No changelog provided"

    def test_empty_changelog(self, empty_changelog):
        changelog = release_bot.parse_changelog("1.0.0", "2.0.0", empty_changelog)
        assert changelog == "No changelog provided"

    def test_one_entry_changelog(self, changelog_with_one_entry):
        changelog = release_bot.parse_changelog("0.0.0", "0.0.1", changelog_with_one_entry)
        assert changelog == "* Test entry\n* Another test entry"

    def test_wrong_version(self, changelog_with_one_entry):
        changelog = release_bot.parse_changelog("0.0.1", "0.0.2", changelog_with_one_entry)
        assert changelog == "No changelog provided"

    def test_wrong_version_2(self, changelog_with_one_entry):
        changelog = release_bot.parse_changelog("0.0.3", "0.0.1", changelog_with_one_entry)
        assert changelog == "No changelog provided"

    def test_normal_use_case(self, changelog_with_two_entries):
        changelog = release_bot.parse_changelog("0.0.1", "0.0.2", changelog_with_two_entries)
        assert changelog == "* New entry\n* Fixes"

    def test_no_changes(self, changelog_with_no_changes):
        changelog = release_bot.parse_changelog("0.0.1", "0.0.2", changelog_with_no_changes)
        assert changelog == "No changelog provided"
