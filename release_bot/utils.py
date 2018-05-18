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

import shlex
import datetime
import os
import re
import subprocess
import locale
from semantic_version import Version

from .configuration import configuration
from .exceptions import ReleaseException


def parse_changelog(previous_version, version, path):
    """
    Get changelog for selected version

    :param str previous_version: Version before the new one
    :param str version: A new version
    :param str path: Path to CHANGELOG.md
    :return: Changelog entry or placeholder entry if no changelog is found
    """
    if os.path.isfile(path + "/CHANGELOG.md") and \
            Version.coerce(previous_version) < Version.coerce(version):
        file = open(path + '/CHANGELOG.md', 'r').read()
        # detect position of this version header
        pos_start = file.find("# " + version)
        pos_end = file.find("# " + previous_version)
        changelog = file[pos_start + len("# " + version):(pos_end if pos_end >= 0 else len(file))].strip()
        if changelog:
            return changelog
    return "No changelog provided"


def update_spec(spec_path, new_release):
    """
    Update spec with new version and changelog for that version, change release to 1

    :param spec_path: Path to package .spec file
    :param new_release: an array containing info about new release, see main() for definition
    """
    if os.path.isfile(spec_path):
        # make changelog and get version
        locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
        changelog = (f"* {datetime.datetime.now():%a %b %d %Y} {new_release['author_name']!s} "
                     f"<{new_release['author_email']!s}> {new_release['version']}-1\n")
        # add entries
        if new_release['changelog']:
            for item in new_release['changelog']:
                changelog += f"- {item}\n"
        else:
            changelog += f"- {new_release['version']} release\n"
        # change the version and add changelog in spec file
        with open(spec_path, 'r+') as spec_file:
            spec = spec_file.read()
            # replace version
            spec = re.sub(r'(Version:\s*)([0-9]|[.])*', r'\g<1>' + new_release['version'], spec)
            # make release 1
            spec = re.sub(r'(Release:\s*)([0-9]*)(.*)', r'\g<1>1\g<3>', spec)
            # insert changelog
            spec = re.sub(r'(%changelog\n)', r'\g<1>' + changelog + '\n', spec)
            # write and close
            spec_file.seek(0)
            spec_file.write(spec)
            spec_file.truncate()
            spec_file.close()
    else:
        raise ReleaseException("No spec file found in dist-git repository!")


def shell_command(work_directory, cmd, error_message, fail=True):
    """
    Execute a shell command

    :param work_directory: A directory to execute the command in
    :param cmd: The shell command
    :param error_message: An error message to return in case of failure
    :param fail: If failure should cause termination of the bot
    :return: Boolean indicating success/failure
    """
    cmd = shlex.split(cmd)
    shell = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=work_directory,
        universal_newlines=True)
    configuration.logger.debug(f"{shell.args}\n{shell.stdout}")
    if shell.returncode != 0:
        configuration.logger.error(f"{error_message}\n{shell.stderr}")
        if fail:
            raise ReleaseException(f"{shell.args!r} failed with {error_message!r}")
        return False
    return True
