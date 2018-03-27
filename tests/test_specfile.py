import release_bot.release_bot as release_bot
import pytest
import os
# import datetime from release_bot, because it needs to be patched
from release_bot.release_bot import datetime

FAKE_TIME = datetime.datetime(2018, 12, 24, 17, 35, 55)


class TestSpecFile:

    @pytest.fixture
    def patch_datetime_now(self, monkeypatch):
        class MyDateTime:
            @classmethod
            def now(cls):
                return FAKE_TIME

        monkeypatch.setattr(datetime, 'datetime', MyDateTime)

    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        release_bot.CONFIGURATION['logger'] = release_bot.set_logging(level=70)
        release_bot.CONFIGURATION['debug'] = True

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    @pytest.fixture
    def valid_conf(self, tmpdir):
        conf = tmpdir.join("release-conf.yaml")
        conf.write("version: 0.0.2")
        return conf

    @pytest.fixture
    def valid_spec(self, tmpdir):
        spec = tmpdir.join("example.spec")
        with open(os.path.join(os.path.dirname(__file__), "src/example.spec")) as file:
            spec.write(file.read())
        return spec

    @pytest.fixture
    def spec_updated(self, tmpdir):
        spec = tmpdir.join("example_updated.spec")
        with open(os.path.join(os.path.dirname(__file__), "src/example_updated.spec")) as file:
            spec.write(file.read())
        return spec

    @pytest.fixture
    def spec_updated_changelog(self, tmpdir):
        spec = tmpdir.join("example_updated_changelog.spec")
        with open(os.path.join(os.path.dirname(__file__), "src/example_updated_changelog.spec")) as file:
            spec.write(file.read())
        return spec

    @pytest.fixture
    def valid_email(self):
        return "jdoe@example.com"

    @pytest.fixture
    def valid_name(self):
        return "John Doe"

    @pytest.fixture
    def valid_new_release(self):
        new_release = {'version': '0.0.2',
                       'commitish': 'xxx',
                       'author_name': 'John Doe',
                       'author_email': 'jdoe@example.com',
                       'python_versions': [],
                       'fedora': False,
                       'fedora_branches': [],
                       'changelog': [],
                       'fs_path': '',
                       'tempdir': None}
        return new_release

    def test_missing_spec(self, valid_new_release):
        with pytest.raises(SystemExit) as error:
            release_bot.update_spec("", valid_new_release)
        assert error.type == SystemExit
        assert error.value.code == 1

    # test with no defined changelog
    def test_valid_conf(self, valid_spec, valid_new_release, spec_updated, patch_datetime_now):
        release_bot.update_spec(valid_spec, valid_new_release)
        with open(valid_spec) as spec, open(spec_updated) as original:
            assert spec.read() == original.read()

    # test with defined changelog
    def test_valid_conf_changelog(self, valid_spec, valid_new_release,
                                  spec_updated_changelog, patch_datetime_now):
        valid_new_release['changelog'] = ['Changelog entry 1', 'Changelog entry 2']
        release_bot.update_spec(valid_spec, valid_new_release)
        with open(valid_spec) as spec, open(spec_updated_changelog) as original:
            assert spec.read() == original.read()
