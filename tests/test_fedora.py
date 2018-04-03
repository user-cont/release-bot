import os
import sys
import release_bot.release_bot as release_bot
from release_bot.release_bot import tempfile
import pytest
import subprocess
from flexmock import flexmock


class TestFedora:

    def run_cmd(self, cmd, work_directory):
        shell = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=work_directory,
            universal_newlines=True)
        return shell

    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        release_bot.CONFIGURATION['logger'] = release_bot.set_logging(level=10)
        release_bot.CONFIGURATION['debug'] = True

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    def fake_spectool_func(self, directory, branch, fail=True):
        source_path = os.path.join(directory, f"{branch}_source.tar.gz")
        with open(source_path, "w") as file:
            file.write("Stuff")
        return True

    def fake_clone_func(self, directory, name):
        if os.path.isdir(directory):
            release_bot.shell_command(directory,
                                      f"fedpkg clone {name!r} -a",
                                      "Cloning fedora repository failed:")
            return os.path.join(directory, name)
        else:
            release_bot.CONFIGURATION['logger'].error(f"Cannot clone fedpkg repository into non-existent directory:")
            sys.exit(1)

    def fake_repository_clone_func(self, directory, name, non_ff=False):
        self.create_fake_repository(directory, non_ff)
        return directory

    def create_fake_repository(self, directory, non_ff=False):
        self.run_cmd("git init .", directory)
        self.run_cmd("git checkout -b master", directory)
        filename = os.path.join(directory, "example.spec")
        with open(os.path.join(os.path.dirname(__file__), "src/example.spec")) as file:
            with open(filename, "w") as new_file:
                new_file.write(file.read())
        self.run_cmd("git add .", directory)
        self.run_cmd("git commit -m 'Initial commit'", directory)
        self.run_cmd("git checkout -b f28", directory)
        if non_ff:
            with open(os.path.join(os.path.dirname(__file__), "src/example_updated.spec")) as file:
                with open(filename, "w") as new_file:
                    new_file.write(file.read())
            self.run_cmd("git add .", directory)
            self.run_cmd("git commit -m 'Initial commit 2'", directory)
        else:
            self.run_cmd("git merge master", directory)
        self.run_cmd("git checkout master", directory)

    @pytest.fixture
    def new_release(self):
        new_release = {'version': '9.9.9',
                       'commitish': '',
                       'author_name': 'John Doe',
                       'author_email': 'jdoe@example.com',
                       'python_versions': [3],
                       'fedora_branches': ["f28"],
                       'fedora': True,
                       'changelog': ['Test'],
                       'fs_path': '',
                       'tempdir': None}
        return new_release

    @pytest.fixture()
    def no_sources(self):
        flexmock(release_bot, fedpkg_sources=True)

    @pytest.fixture()
    def no_build(self):
        flexmock(release_bot, fedpkg_build=True)

    @pytest.fixture()
    def no_push(self):
        flexmock(release_bot, fedpkg_push=True)

    @pytest.fixture()
    def no_new_sources(self):
        flexmock(release_bot, fedpkg_new_sources=True)

    @pytest.fixture()
    def fake_spectool(self):
        (flexmock(release_bot)
         .should_receive("fedpkg_spectool")
         .replace_with(lambda directory, branch, fail: self.fake_spectool_func(directory, branch, fail)))

    @pytest.fixture
    def fake_repository_clone(self, tmpdir):
        (flexmock(release_bot)
         .should_receive("fedpkg_clone_repository")
         .replace_with(lambda directory, name: self.fake_repository_clone_func(tmpdir, name)))
        return tmpdir

    @pytest.fixture
    def fake_repository_clone_no_ff(self, tmpdir):
        (flexmock(release_bot)
         .should_receive("fedpkg_clone_repository")
         .replace_with(lambda directory, name: self.fake_repository_clone_func(tmpdir, name, True)))
        return tmpdir

    @pytest.fixture
    def fake_clone(self):
        (flexmock(release_bot)
         .should_receive("fedpkg_clone_repository")
         .replace_with(lambda directory, name: self.fake_clone_func(directory, name)))

    @pytest.fixture
    def no_lint(self):
        flexmock(release_bot, fedpkg_lint=True)

    @pytest.fixture
    def fake_tmp_clean(self):
        (flexmock(release_bot.tempfile.TemporaryDirectory)
         .should_receive("cleanup")
         .replace_with(lambda: None))

    @pytest.fixture
    def package(self):
        return 'fedpkg'

    @pytest.fixture
    def non_existent_path(self, tmpdir):
        path = os.path.join(tmpdir, 'foo')
        return path

    @pytest.fixture
    def tmp(self, tmpdir):
        return tmpdir

    @pytest.fixture
    def fake_repository(self, tmpdir):
        self.create_fake_repository(tmpdir)
        return tmpdir

    @pytest.fixture
    def example_spec(self, tmpdir):
        spec = tmpdir.join("example.spec")
        with open(os.path.join(os.path.dirname(__file__), "src/example.spec")) as file:
            spec.write(file.read())
        return spec

    def test_wrong_dir_clone(self, non_existent_path, package, fake_clone):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_clone_repository(non_existent_path, package)
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_wrong_dir_switch(self, non_existent_path):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_switch_branch(non_existent_path, 'master')
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_wrong_dir_build(self, non_existent_path):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_build(non_existent_path, 'master')
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_wrong_dir_push(self, non_existent_path):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_push(non_existent_path, 'master')
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_wrong_dir_merge(self, non_existent_path):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_merge(non_existent_path, 'master')
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_wrong_dir_commit(self, non_existent_path):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_commit(non_existent_path, 'master', "Some message")
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_wrong_dir_sources(self, non_existent_path):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_sources(non_existent_path, 'master')
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_wrong_dir_spectool(self, non_existent_path):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_spectool(non_existent_path, 'master')
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_wrong_dir_lint(self, non_existent_path):
        with pytest.raises(SystemExit) as error:
            release_bot.fedpkg_lint(non_existent_path, 'master')
        assert error.type == SystemExit
        assert error.value.code == 1

    def test_clone(self, tmp, package, fake_clone):
        directory = release_bot.fedpkg_clone_repository(tmp, package)
        assert os.path.isfile(os.path.join(directory, f"{package}.spec"))
        assert os.path.isdir(os.path.join(directory, ".git"))

    def test_switch_branch(self, fake_repository):
        release_bot.fedpkg_switch_branch(fake_repository, "f28", False)
        assert "f28" == self.run_cmd("git rev-parse --abbrev-ref HEAD", fake_repository).stdout.strip()
        release_bot.fedpkg_switch_branch(fake_repository, "master", False)
        assert "master" == self.run_cmd("git rev-parse --abbrev-ref HEAD", fake_repository).stdout.strip()

    def test_commit(self, fake_repository):
        spec_path = os.path.join(fake_repository, "example.spec")
        with open(spec_path, "r+") as spec_file:
            spec = spec_file.read() + "\n Test test"
            spec_file.write(spec)

        branch = "master"
        commit_message = "Test commit"
        assert release_bot.fedpkg_commit(fake_repository, "master", commit_message, False)
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B {branch}| cat | head -n 1",
                                              fake_repository).stdout.strip()

    def test_lint(self, tmp, package, fake_clone):
        directory = release_bot.fedpkg_clone_repository(tmp, package)
        spec_path = os.path.join(directory, f"{package}.spec")
        assert release_bot.fedpkg_lint(directory, "master", False)
        with open(spec_path, "r+") as spec_file:
            spec = spec_file.read() + "\n Test test"
            spec_file.write(spec)
            assert not release_bot.fedpkg_lint(directory, "master", False)

    def test_sources(self, tmp, package, fake_clone):
        directory = release_bot.fedpkg_clone_repository(tmp, package)
        file_number = len(os.listdir(directory))
        assert release_bot.fedpkg_sources(directory, "master", False)
        assert file_number != len(os.listdir(directory))

    def test_spectool(self, tmp, package, fake_clone):
        directory = release_bot.fedpkg_clone_repository(tmp, package)
        file_number = len(os.listdir(directory))
        assert release_bot.fedpkg_spectool(directory, "master", False)
        assert file_number != len(os.listdir(directory))

    def test_workflow(self, fake_repository):
        spec_path = os.path.join(fake_repository, "example.spec")
        with open(spec_path, "r+") as spec_file:
            spec = spec_file.read() + "\n Test test"
            spec_file.write(spec)
        commit_message = "Update"
        assert release_bot.fedpkg_commit(fake_repository, "master", commit_message, False)
        assert release_bot.fedpkg_switch_branch(fake_repository, "f28", False)
        assert release_bot.fedpkg_merge(fake_repository, "f28", True, False)
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B f28 | cat | head -n 1",
                                              fake_repository).stdout.strip()

    def test_update_package(self, no_build, no_push, no_sources, no_new_sources, fake_spectool,
                            no_lint, new_release, fake_repository):
        release_bot.CONFIGURATION['repository_name'] = 'example'
        commit_message = f"Update to {new_release['version']}"
        assert release_bot.update_package(fake_repository, "f28", new_release)
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B | cat | head -n 1",
                                              fake_repository).stdout.strip()

    def test_release_in_fedora(self, no_build, no_push, no_sources, no_new_sources, fake_spectool,
                               no_lint, fake_repository_clone, new_release, fake_tmp_clean):
        release_bot.CONFIGURATION['repository_name'] = 'example'
        release_bot.release_in_fedora(new_release)
        commit_message = f"Update to {new_release['version']}"
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B master| cat | head -n 1",
                                              fake_repository_clone).stdout.strip()
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B f28 | cat | head -n 1",
                                              fake_repository_clone).stdout.strip()

    def test_release_in_fedora_non_ff(self, no_build, no_push, no_sources, no_new_sources, no_lint,
                                      fake_spectool, fake_repository_clone_no_ff, new_release, fake_tmp_clean):
        release_bot.CONFIGURATION['repository_name'] = 'example'
        release_bot.release_in_fedora(new_release)
        commit_message = f"Update to {new_release['version']}"
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B master| cat | head -n 1",
                                              fake_repository_clone_no_ff).stdout.strip()
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B f28 | cat | head -n 1",
                                              fake_repository_clone_no_ff).stdout.strip()
