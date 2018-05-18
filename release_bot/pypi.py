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

from .exceptions import ReleaseException
from .utils import shell_command


class PyPi:

    PYPI_URL = "https://pypi.org/pypi/"

    def __init__(self, configuration):
        self.conf = configuration
        self.logger = configuration.logger

    def latest_version(self):
        """Get latest version of the package from PyPi"""
        response = requests.get(url=f"{self.PYPI_URL}{self.conf.repository_name}/json")
        if response.status_code == 200:
            return response.json()['info']['version']
        else:
            msg = f"Pypi package {self.conf.repository_name!r} doesn't exist:\n{response.text}"
            raise ReleaseException(msg)

    @staticmethod
    def build_sdist(project_root):
        """
        Builds source distribution out of setup.py

        :param project_root: location of setup.py
        """
        if os.path.isfile(os.path.join(project_root, 'setup.py')):
            shell_command(project_root, "python setup.py sdist", "Cannot build sdist:")
        else:
            raise ReleaseException("Cannot find setup.py:")

    @staticmethod
    def build_wheel(project_root, python_version):
        """
        Builds wheel for specified version of python

        :param project_root: location of setup.py
        :param python_version: python version to build wheel for
        """
        interpreter = "python2"
        if python_version == 3:
            interpreter = "python3"
        elif python_version != 2:
            # no other versions of python other than 2 and three are supported
            raise ReleaseException(f"Unsupported python version: {python_version}")

        if not os.path.isfile(os.path.join(project_root, 'setup.py')):
            raise ReleaseException("Cannot find setup.py:")

        shell_command(project_root, f"{interpreter} setup.py bdist_wheel",
                      f"Cannot build wheel for python {python_version}")

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
            shell_command(project_root, f"twine upload {files}",
                          "Cannot upload python distribution:")
        else:
            raise ReleaseException("dist/ folder cannot be found:")

    def release(self, conf_array):
        """
        Release project on PyPi

        :param conf_array: structure with information about the new release
        """
        project_root = conf_array['fs_path']
        if os.path.isdir(project_root):
            self.logger.debug("About to release on PyPi")
            self.build_sdist(project_root)
            for version in conf_array['python_versions']:
                self.build_wheel(project_root, version)
            self.upload(project_root)
        else:
            raise ReleaseException("Cannot find project root for PyPi release:")
