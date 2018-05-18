import subprocess
import re
import shutil
import pytest
from flexmock import flexmock
from pathlib import Path

from release_bot.configuration import configuration
from release_bot.exceptions import ReleaseException
from release_bot.pypi import PyPi


class TestPypi2:

    def setup_method(self, method):
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        configuration.set_logging(level=10)
        configuration.debug = True
        self.pypi = PyPi(configuration)

    def teardown_method(self, method):
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        if re.match(r'test_install_.', method.__name__) or re.match(r'test_release_.', method.__name__):
            self.run_cmd('pip2 uninstall rlsbot-test -y', "/")
            self.run_cmd('pip3 uninstall rlsbot-test -y', "/")

    def run_cmd(self, cmd, work_directory):
        shell = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=work_directory,
            universal_newlines=True)
        return shell

    @pytest.fixture
    def minimal_conf_array(self, tmpdir):
        return {'python_versions': [2, 3],
                'fs_path': tmpdir}

    @pytest.fixture
    def package_setup(self, tmpdir):
        path = Path(str(tmpdir))/"rlsbot-test"
        src = Path(__file__).parent/"src/rlsbot-test"
        shutil.copytree(str(src), str(path))
        return path

    @pytest.fixture()
    def no_upload(self):
        (flexmock(self.pypi)
         .should_receive("upload")
         .replace_with(lambda x: None))

    @pytest.fixture
    def non_existent_path(self, tmpdir):
        path = Path(str(tmpdir))/'fooo'
        return str(path)

    def test_missing_setup_sdist(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.pypi.build_sdist(non_existent_path)

    def test_missing_setup_wheel(self, non_existent_path):
        with pytest.raises(ReleaseException):
            self.pypi.build_wheel(non_existent_path, 2)

    def test_missing_project_wrapper(self, minimal_conf_array, non_existent_path):
        minimal_conf_array['fs_path'] = non_existent_path
        with pytest.raises(ReleaseException):
            self.pypi.release(minimal_conf_array)

    def test_sdist(self, package_setup):
        self.pypi.build_sdist(package_setup)
        assert (package_setup/'dist/rlsbot-test-1.0.0.tar.gz').is_file()

    def test_wheel_2(self, package_setup):
        self.pypi.build_wheel(package_setup, 2)
        assert list(package_setup.glob('dist/rlsbot_test-1.0.0-py2*.whl'))

    def test_install_2(self, package_setup):
        self.pypi.build_sdist(package_setup)
        self.pypi.build_wheel(package_setup, 2)
        wheel2 = list(package_setup.glob('dist/rlsbot_test-1.0.0-py2*.whl'))
        assert self.run_cmd(f'pip2 install --user {wheel2[0]}', package_setup).returncode == 0
        assert self.run_cmd(f'pip2 show rlsbot-test', package_setup).returncode == 0
        assert self.run_cmd(f'$HOME/.local/bin/rlsbot-test', package_setup).returncode == 0

    def test_release_2(self, minimal_conf_array, package_setup, no_upload):
        minimal_conf_array['fs_path'] = package_setup
        self.pypi.release(minimal_conf_array)
        assert (package_setup/'dist/rlsbot-test-1.0.0.tar.gz').is_file()
        wheel2 = list(package_setup.glob('dist/rlsbot_test-1.0.0-py2*.whl'))
        assert wheel2
        assert self.run_cmd(f'pip2 install --user {wheel2[0]}', package_setup).returncode == 0
        assert self.run_cmd(f'pip2 show rlsbot-test', package_setup).returncode == 0
        assert self.run_cmd(f'$HOME/.local/bin/rlsbot-test', package_setup).returncode == 0
