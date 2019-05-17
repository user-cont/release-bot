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

from glob import glob
import os
import requests

from release_bot.exceptions import ReleaseException
from release_bot.utils import run_command


class PyPi:

    PYPI_URL = "https://pypi.org/pypi/"

    def __init__(self, configuration, git):
        """

        :param configuration: instance of Configuration
        :param git: instance of Git
        """
        self.conf = configuration
        self.logger = configuration.logger
        self.git = git

    def latest_version(self):
        """Get latest version of the package from PyPi or 0.0.0"""
        response = requests.get(url=f"{self.PYPI_URL}{self.conf.pypi_project}/json")
        if response.status_code == 200:
            return response.json()['info']['version']
        elif response.status_code == 404:
            return '0.0.0'
        else:
            msg = f"Error getting latest version from PyPi:\n{response.text}"
            raise ReleaseException(msg)

    @staticmethod
    def build_sdist(project_root):
        """
        Builds source distribution out of setup.py

        :param project_root: location of setup.py
        """
        if os.path.isfile(os.path.join(project_root, 'setup.py')):
            run_command(project_root, "python3 setup.py sdist", "Cannot build sdist:")
        else:
            raise ReleaseException("Cannot find setup.py:")

    @staticmethod
    def build_wheel(project_root):
        """
        Builds wheel for specified version of python

        :param project_root: location of setup.py
        """
        if not os.path.isfile(os.path.join(project_root, 'setup.py')):
            raise ReleaseException("Cannot find setup.py:")

        run_command(project_root, "python3 setup.py bdist_wheel", "Cannot build wheel:")

    def upload(self, project_root):
        """
        Uploads the package distribution to PyPi

        :param project_root: directory with dist/ folder
        """
        if os.path.isdir(os.path.join(project_root, 'dist')):
            spec_files = glob(os.path.join(project_root, "dist/*"))
            files = ""
            for file in spec_files:
                files += f"{file} "
            self.logger.debug(f"Uploading {files} to PyPi")
            run_command(project_root, f"twine upload {files}",
                        "Cannot upload python distribution:")
        else:
            raise ReleaseException("dist/ folder cannot be found:")

    def release(self):
        """
        Release project on PyPi
        """
        project_root = self.git.repo_path
        if os.path.isdir(project_root):
            self.logger.debug("About to release on PyPi")
            self.build_sdist(project_root)
            self.build_wheel(project_root)
            if self.conf.dry_run:
                return False
            self.upload(project_root)
        else:
            raise ReleaseException("Cannot find project root for PyPi release:")
