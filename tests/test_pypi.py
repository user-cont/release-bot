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

import os
import re
import shutil
import subprocess
from glob import glob
from pathlib import Path

import pytest
from flexmock import flexmock

from release_bot.configuration import configuration, Configuration
from release_bot.exceptions import ReleaseException
from release_bot.git import Git
from release_bot.pypi import PyPi
from release_bot.utils import set_git_credentials

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))


class TestPypi:
    def setup_method(self, method):
        """setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        configuration.set_logging(level=10)
        configuration.debug = True

    def teardown_method(self, method):
        """teardown any state that was previously setup with a setup_method
        call.
        """
        if re.match(r"test_install_.", method.__name__) or re.match(
            r"test_release_.", method.__name__
        ):
            self.run_cmd("pip2 uninstall rlsbot-test -y", "/")
            self.run_cmd("pip3 uninstall rlsbot-test -y", "/")

    def run_cmd(self, cmd, work_directory):
        shell = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=work_directory,
            universal_newlines=True,
        )
        if shell.returncode:
            raise RuntimeError(
                "Error while running command {}:\n{}".format(cmd, shell.stderr)
            )
        return shell

    @pytest.fixture
    def pypi(self, tmpdir):
        conf = Configuration()
        path = str(tmpdir)
        src = Path(__file__).parent / "src/rlsbot_test"
        shutil.copy2(str(src / "setup.py"), path)
        shutil.copy2(str(src / "rlsbot_test.py"), path)
        self.run_cmd("git init .", work_directory=str(tmpdir))
        set_git_credentials(str(tmpdir), "Release Bot", "bot@example.com")
        self.run_cmd("git add .", work_directory=str(tmpdir))
        self.run_cmd("git commit -m 'initial commit'", work_directory=str(tmpdir))
        git_repo = Git(str(tmpdir), conf)
        pypi = PyPi(configuration, git_repo)
        (flexmock(pypi).should_receive("upload").replace_with(lambda x: None))
        return pypi

    @pytest.fixture
    def non_existent_path(self, tmpdir):
        path = Path(str(tmpdir)) / "fooo"
        return str(path)

    def test_missing_setup_sdist(self, non_existent_path, pypi):
        with pytest.raises(ReleaseException):
            pypi.build_sdist(non_existent_path)

    def test_missing_setup_wheel(self, non_existent_path, pypi):
        with pytest.raises(ReleaseException):
            pypi.build_wheel(non_existent_path)

    def test_missing_project_wrapper(self, pypi):
        pypi.git.repo_path = "nope"
        with pytest.raises(ReleaseException):
            pypi.release()

    def test_sdist(self, pypi):
        repo_path = pypi.git.repo_path
        pypi.build_sdist(repo_path)
        assert os.path.isfile(os.path.join(repo_path, "dist/rlsbot-test-1.0.0.tar.gz"))

    def test_wheel(self, pypi):
        repo_path = pypi.git.repo_path
        pypi.build_wheel(repo_path)
        assert glob(os.path.join(repo_path, "dist/rlsbot_test-1.0.0-py3*.whl"))

    def test_install(self, pypi):
        repo_path = pypi.git.repo_path
        pypi.build_sdist(repo_path)
        pypi.build_wheel(repo_path)
        whl = glob(os.path.join(repo_path, "dist/rlsbot_test-1.0.0-py3*.whl"))[0]
        assert self.run_cmd(f"pip3 install --user {whl}", repo_path).returncode == 0
        assert self.run_cmd("pip3 show rlsbot-test", repo_path).returncode == 0
        assert self.run_cmd("$HOME/.local/bin/rlsbot-test", repo_path).returncode == 0

    def test_full_release(self, pypi):
        repo_path = pypi.git.repo_path
        pypi.release()
        assert os.path.isfile(os.path.join(repo_path, "dist/rlsbot-test-1.0.0.tar.gz"))
        whl = glob(os.path.join(repo_path, "dist/rlsbot_test-1.0.0-py3*.whl"))[0]
        assert whl
        assert self.run_cmd(f"pip3 install --user {whl}", repo_path).returncode == 0
        assert self.run_cmd("pip3 show rlsbot-test", repo_path).returncode == 0
        assert self.run_cmd("$HOME/.local/bin/rlsbot-test", repo_path).returncode == 0
