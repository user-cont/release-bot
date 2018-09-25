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
from semantic_version import Version, validate

from release_bot.configuration import configuration
from release_bot.exceptions import ReleaseException


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
        pos_end = file.find("# " + previous_version) if previous_version else len(file)
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
    if not os.path.isfile(spec_path):
        raise ReleaseException("No spec file found in dist-git repository!")

    # make changelog and get version
    locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
    changelog = (f"* {datetime.datetime.now():%a %b %d %Y} {new_release['author_name']!s} "
                 f"<{new_release['author_email']!s}> {new_release['version']}-1\n")
    # add entries
    if new_release.get('changelog'):
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


def run_command(work_directory, cmd, error_message, fail=True):
    """
    Execute a command

    :param work_directory: A directory to execute the command in
    :param cmd: command
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


def run_command_get_output(work_directory, cmd):
    """
    Same as run command, but more simple and returns stdout
    :param work_directory: A directory to execute the command in
    :param cmd: command
    :return: stdout of the command
    """
    cmd = shlex.split(cmd)
    shell = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=work_directory,
        universal_newlines=True)
    success = shell.returncode == 0
    if not success:
        return success, shell.stderr
    return success, shell.stdout


def insert_in_changelog(changelog, version, log):
    """
    Patches file with new changelog
    :param changelog: file with changelog
    :param version: current version
    :param log: the changelog to insert
    :return: bool success
    """
    content = f"# {version}\n\n{log}\n"
    try:
        with open(changelog, 'r+') as file:
            original = file.read()
            file.seek(0)
            file.write(content + original)
            return True
    except FileNotFoundError as exc:
        configuration.logger.warning(f"No CHANGELOG.md present in repository\n{exc}")
    return False


def look_for_version_files(repo_directory, new_version):
    """
    Walks through repository and looks for suspects that may be hiding the __version__ variable
    :param repo_directory: repository path
    :param new_version: version to update to
    :return: list of changed files
    """
    changed = []
    for root, _, files in os.walk(repo_directory):
        for file in files:
            if file in ('setup.py', '__init__.py', 'version.py'):
                filename = os.path.join(root, file)
                success = update_version(filename, new_version)
                if success:
                    changed.append(filename.replace(repo_directory + '/', '', 1))
    if len(changed) > 1:
        configuration.logger.error('Multiple version files found. Aborting version update.')
    elif not changed:
        configuration.logger.error('No version files found. Aborting version update.')

    return changed


def update_version(file, new_version):
    """
    Patches the file with new version
    :param file: file containing __version__ variable
    :param new_version: version to update the file with
    :return: True if file was changed, else False
    """
    with open(file, 'r') as input_file:
        content = input_file.read().splitlines()
        content_original = content.copy()

    changed = False
    for index, line in enumerate(content):
        if line.startswith('__version__'):
            pieces = line.split('=', maxsplit=1)
            if len(pieces) == 2:
                configuration.logger.info(f"Editing line with new version:\n{line}")
                old_version = (pieces[1].strip())[1:-1]  # strip whitespace and ' or "
                if validate(old_version):
                    configuration.logger.info(f"Replacing version {old_version} with {new_version}")
                    content[index] = f"{pieces[0].strip()} = '{new_version}'"
                    changed = True if content != content_original else False
                    break
                else:
                    configuration.logger.warning(f"Failed to validate version, aborting")
                    return False
    if changed:
        with open(file, 'w') as output:
            output.write('\n'.join(content) + '\n')
        configuration.logger.info('Version replaced.')
    return changed
