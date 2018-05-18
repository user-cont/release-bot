import os
import pytest
import subprocess
from tempfile import TemporaryDirectory
from flexmock import flexmock
from pathlib import Path

from release_bot.configuration import configuration
from release_bot.exceptions import ReleaseException
from release_bot.fedora import Fedora
from release_bot.utils import shell_command


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
        configuration.set_logging(level=10)
        configuration.debug = True
        self.fedora = Fedora(configuration)

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """

    def fake_spectool_func(self, directory, branch, fail=True):
        source_path = Path(directory) / f"{branch}_source.tar.gz"
        source_path.touch()
        return True

    def fake_clone_func(self, directory, name):
        directory = Path(directory)
        if not directory.is_dir():
            raise ReleaseException(f"Cannot clone into non-existent directory {directory}:")

        shell_command(directory,
                      f"fedpkg clone {name!r} --anonymous",
                      "Cloning fedora repository failed:")
        return str(directory / name)

    def fake_repository_clone_func(self, directory, name, non_ff=False):
        self.create_fake_repository(directory, non_ff)
        return directory

    def create_fake_repository(self, directory, non_ff=False):
        self.run_cmd("git init .", directory)
        self.run_cmd("git checkout -b master", directory)
        spec_content = Path(__file__).parent.joinpath("src/example.spec").read_text()
        Path(directory).joinpath("example.spec").write_text(spec_content)
        self.run_cmd("git add .", directory)
        self.run_cmd("git commit -m 'Initial commit'", directory)
        self.run_cmd("git checkout -b f28", directory)
        if non_ff:
            spec_content = Path(__file__).parent.joinpath("src/example_updated.spec").read_text()
            Path(directory).joinpath("example.spec").write_text(spec_content)
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
        flexmock(self.fedora, fedpkg_sources=True)

    @pytest.fixture()
    def no_build(self):
        flexmock(self.fedora, fedpkg_build=True)

    @pytest.fixture()
    def no_push(self):
        flexmock(self.fedora, fedpkg_push=True)

    @pytest.fixture()
    def no_new_sources(self):
        flexmock(self.fedora, fedpkg_new_sources=True)

    @pytest.fixture()
    def no_ticket_init(self):
        flexmock(self.fedora, init_ticket=True)

    @pytest.fixture()
    def fake_spectool(self):
        (flexmock(self.fedora)
         .should_receive("fedpkg_spectool")
         .replace_with(lambda directory, branch, fail: self.fake_spectool_func(directory, branch, fail)))

    @pytest.fixture
    def fake_repository_clone(self, tmpdir):
        (flexmock(self.fedora)
         .should_receive("fedpkg_clone_repository")
         .replace_with(lambda directory, name: self.fake_repository_clone_func(tmpdir, name)))
        return tmpdir

    @pytest.fixture
    def fake_repository_clone_no_ff(self, tmpdir):
        (flexmock(self.fedora)
         .should_receive("fedpkg_clone_repository")
         .replace_with(lambda directory, name: self.fake_repository_clone_func(tmpdir, name, True)))
        return tmpdir

    @pytest.fixture
    def fake_clone(self):
        (flexmock(self.fedora)
         .should_receive("fedpkg_clone_repository")
         .replace_with(lambda directory, name: self.fake_clone_func(directory, name)))

    @pytest.fixture
    def no_lint(self):
        flexmock(self.fedora, fedpkg_lint=True)

    @pytest.fixture
    def fake_tmp_clean(self):
        (flexmock(TemporaryDirectory)
         .should_receive("cleanup")
         .replace_with(lambda: None))

    @pytest.fixture
    def package(self):
        return 'zip'

    @pytest.fixture
    def non_existent_path(self, tmpdir):
        path = Path(str(tmpdir))/'fooo'
        return str(path)

    @pytest.fixture
    def tmp(self, tmpdir):
        return tmpdir

    @pytest.fixture
    def fake_repository(self, tmpdir):
        self.create_fake_repository(tmpdir)
        return Path(str(tmpdir))

    @pytest.fixture
    def example_spec(self, tmpdir):
        spec_content = (Path(__file__).parent/"src/example.spec").read_text()
        spec = Path(str(tmpdir))/"example.spec"
        spec.write_text(spec_content)
        return str(spec)

    def test_wrong_dir_clone(self, non_existent_path, package, fake_clone):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_clone_repository(non_existent_path, package)

    def test_wrong_dir_switch(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_switch_branch(non_existent_path, 'master')

    def test_wrong_dir_build(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_build(non_existent_path, 'master')

    def test_wrong_dir_push(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_push(non_existent_path, 'master')

    def test_wrong_dir_merge(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_merge(non_existent_path, 'master')

    def test_wrong_dir_commit(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_commit(non_existent_path, 'master', "Some message")

    def test_wrong_dir_sources(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_sources(non_existent_path, 'master')

    def test_wrong_dir_spectool(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_spectool(non_existent_path, 'master')

    def test_wrong_dir_lint(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.fedora.fedpkg_lint(non_existent_path, 'master')

    def test_clone(self, tmp, package, fake_clone):
        directory = Path(self.fedora.fedpkg_clone_repository(tmp, package))
        assert (directory/f"{package}.spec").is_file()
        assert (directory/".git").is_dir()

    def test_switch_branch(self, fake_repository):
        self.fedora.fedpkg_switch_branch(fake_repository, "f28", False)
        assert "f28" == self.run_cmd("git rev-parse --abbrev-ref HEAD", fake_repository).stdout.strip()
        self.fedora.fedpkg_switch_branch(fake_repository, "master", False)
        assert "master" == self.run_cmd("git rev-parse --abbrev-ref HEAD", fake_repository).stdout.strip()

    def test_commit(self, fake_repository):
        spec_path = fake_repository/"example.spec"
        spec_content = spec_path.read_text() + "\n Test test"
        spec_path.write_text(spec_content)

        branch = "master"
        commit_message = "Test commit"
        assert self.fedora.fedpkg_commit(fake_repository, "master", commit_message, False)
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B {branch}| cat | head -n 1",
                                              fake_repository).stdout.strip()

    def test_lint(self, tmp, package, fake_clone):
        directory = Path(self.fedora.fedpkg_clone_repository(tmp, package))
        assert self.fedora.fedpkg_lint(str(directory), "master", False)

        spec_path = directory/f"{package}.spec"
        with spec_path.open('r+') as spec_file:
            spec = spec_file.read() + "\n Test test"
            spec_file.write(spec)
            assert not self.fedora.fedpkg_lint(str(directory), "master", False)

    def test_sources(self, tmp, package, fake_clone):
        directory = self.fedora.fedpkg_clone_repository(tmp, package)
        file_number = len(os.listdir(directory))
        assert self.fedora.fedpkg_sources(directory, "master", False)
        assert file_number != len(os.listdir(directory))

    def test_spectool(self, tmp, package, fake_clone):
        directory = self.fedora.fedpkg_clone_repository(tmp, package)
        file_number = len(os.listdir(directory))
        assert self.fedora.fedpkg_spectool(directory, "master", False)
        assert file_number != len(os.listdir(directory))

    def test_workflow(self, fake_repository):
        spec_path = fake_repository/"example.spec"
        spec_content = spec_path.read_text() + "\n Test test"
        spec_path.write_text(spec_content)

        commit_message = "Update"
        assert self.fedora.fedpkg_commit(fake_repository, "master", commit_message, False)
        assert self.fedora.fedpkg_switch_branch(fake_repository, "f28", False)
        assert self.fedora.fedpkg_merge(fake_repository, "f28", True, False)
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B f28 | cat | head -n 1",
                                              fake_repository).stdout.strip()

    def test_update_package(self, no_build, no_push, no_sources, no_new_sources, fake_spectool,
                            no_lint, new_release, fake_repository):
        configuration.repository_name = 'example'
        commit_message = f"Update to {new_release['version']}"
        assert self.fedora.update_package(fake_repository, "f28", new_release)
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B | cat | head -n 1",
                                              fake_repository).stdout.strip()

    def test_release_in_fedora(self, no_build, no_push, no_sources, no_new_sources, fake_spectool,
                               no_lint, fake_repository_clone, new_release, fake_tmp_clean,
                               no_ticket_init):
        configuration.repository_name = 'example'
        self.fedora.release(new_release)
        commit_message = f"Update to {new_release['version']}"
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B master| cat | head -n 1",
                                              fake_repository_clone).stdout.strip()
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B f28 | cat | head -n 1",
                                              fake_repository_clone).stdout.strip()

    def test_release_in_fedora_non_ff(self, no_build, no_push, no_sources, no_new_sources, no_lint,
                                      fake_spectool, fake_repository_clone_no_ff, new_release,
                                      no_ticket_init, fake_tmp_clean):
        configuration.repository_name = 'example'
        self.fedora.release(new_release)
        commit_message = f"Update to {new_release['version']}"
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B master| cat | head -n 1",
                                              fake_repository_clone_no_ff).stdout.strip()
        assert commit_message == self.run_cmd(f"git log -1 --pretty=%B f28 | cat | head -n 1",
                                              fake_repository_clone_no_ff).stdout.strip()
