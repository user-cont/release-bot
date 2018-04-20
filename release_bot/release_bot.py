"""
This module provides functionality for automation of releasing projects
into various downstream services
"""
import sys
import re
import shlex
import glob
import tempfile
import datetime
import time
import zipfile
import os
import argparse
import subprocess
import locale
import logging
import yaml
import requests
from pathlib import Path
from semantic_version import Version, validate


class Configuration:
    # note that required items need to reference strings as their length is checked
    REQUIRED_ITEMS = {"conf": ['repository_name', 'repository_owner', 'github_token'],
                      "release-conf": ['python_versions']}

    def __init__(self):
        self._release_bot_version = ''
        self.repository_name = ''
        self.repository_owner = ''
        self.github_token = ''
        self.refresh_interval = 3 * 60
        self.debug = False
        self.configuration = ''
        self.keytab = ''
        self.fas_username = ''
        self.logger = None
        self.set_logging()

    @property
    def version(self):
        if not self._release_bot_version:
            globals_ = {}
            exec((Path(__file__).parent / "version.py").read_text(), globals_)
            self._release_bot_version = globals_['__version__']
        return self._release_bot_version

    def set_logging(self,
                    logger_name="release-bot",
                    level=logging.INFO,
                    handler_class=logging.StreamHandler,
                    handler_kwargs=None,
                    msg_format='%(asctime)s.%(msecs).03d %(filename)-17s %(levelname)-6s %(message)s',
                    date_format='%H:%M:%S'):
        """
        Set personal logger for this library.
        :param logger_name: str, name of the logger
        :param level: int, see logging.{DEBUG,INFO,ERROR,...}: level of logger and handler
        :param handler_class: logging.Handler instance, default is StreamHandler (/dev/stderr)
        :param handler_kwargs: dict, keyword arguments to handler's constructor
        :param msg_format: str, formatting style
        :param date_format: str, date style in the logs
        :return: logger instance
        """
        logger = logging.getLogger(logger_name)
        # do we want to propagate to root logger?
        # logger.propagate = False
        logger.setLevel(level)

        handler_kwargs = handler_kwargs or {}
        handler = handler_class(**handler_kwargs)

        formatter = logging.Formatter(msg_format, date_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        self.logger = logger

    def load_configuration(self):
        """Load bot configuration from .yaml file"""
        if not self.configuration:
            # configuration not supplied, look for conf.yaml in cwd
            path = os.path.join(os.getcwd(), 'conf.yaml')
            if os.path.isfile(path):
                self.configuration = path
            else:
                self.logger.error("Cannot find valid configuration")
                sys.exit(1)
        with open(self.configuration, 'r') as ymlfile:
            file = yaml.load(ymlfile)
        for item in file:
            if hasattr(self, item):
                setattr(self, item, file[item])
        # check if required items are present
        parts_required = ["conf"]
        for part in parts_required:
            for item in self.REQUIRED_ITEMS[part]:
                if item not in file:
                    self.logger.error(f"Item {item!r} is required in configuration!")
                    sys.exit(1)
        self.logger.debug(f"Loaded configuration for {self.repository_owner}/{self.repository_name}")

    def load_release_conf(self, conf_path):
        """
        Load items from release-conf.yaml

        :param conf_path: path to release-conf.yaml
        :return dict with configuration
        """
        if not os.path.isfile(conf_path):
            self.logger.error("No release-conf.yaml found in "
                              f"{self.repository_owner}/{self.repository_name} repository root!\n"
                              "You have to add one for releasing to PyPi/Fedora")
            if self.REQUIRED_ITEMS['release-conf']:
                sys.exit(1)

        with open(conf_path) as conf_file:
            parsed_conf = yaml.load(conf_file) or {}
            parsed_conf = {k: v for (k, v) in parsed_conf.items() if v}
            for item in self.REQUIRED_ITEMS['release-conf']:
                if item not in parsed_conf:
                    self.logger.error(f"Item {item!r} is required in release-conf!")
                    sys.exit(1)
            if 'python_versions' in parsed_conf:
                for index, version in enumerate(parsed_conf['python_versions']):
                    parsed_conf['python_versions'][index] = int(version)
            if 'fedora_branches' in parsed_conf:
                for index, branch in enumerate(parsed_conf['fedora_branches']):
                    parsed_conf['fedora_branches'][index] = str(branch)
            if parsed_conf['fedora'] and not self.fas_username:
                self.logger.warning("Can't release to fedora if there is no FAS username, disabling")
                parsed_conf['fedora'] = False
        return parsed_conf


configuration = Configuration()


def parse_arguments():
    """Parse application arguments"""
    parser = argparse.ArgumentParser(description="Automatic releases bot", prog='release-bot')
    parser.add_argument("-d", "--debug", help="turn on debugging output",
                        action="store_true", default=False)
    parser.add_argument("-c", "--configuration", help="use custom YAML configuration",
                        default='')
    parser.add_argument("-v", "--version", help="display program version", action='version',
                        version=f"%(prog)s {configuration.version}")
    parser.add_argument("-k", "--keytab", help="keytab file for fedora", default='')

    args = parser.parse_args()
    if args.configuration:
        path = args.configuration
        if not os.path.isabs(path):
            args.configuration = os.path.join(os.getcwd(), path)
        if not os.path.isfile(path):
            configuration.logger.error(
                f"Supplied configuration file is not found: {args.configuration}")
            sys.exit(1)
    if args.debug:
        configuration.logger.setLevel(logging.DEBUG)
    for key, value in vars(args).items():
        setattr(configuration, key, value)


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
        configuration.logger.error("No spec file found in dist-git repository!\n")
        sys.exit(1)


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
            sys.exit(1)
        return False
    return True


class Github:

    API_ENDPOINT = "https://api.github.com/graphql"
    API3_ENDPOINT = "https://api.github.com/"

    def __init__(self, configuration):
        self.conf = configuration
        self.logger = configuration.logger
        self.headers = {'Authorization': f'token {configuration.github_token}'}

    def send_query(self, query):
        """Send query to Github v4 API and return the response"""
        query = {"query": (f'query {{repository(owner: "{self.conf.repository_owner}", '
                           f'name: "{self.conf.repository_name}") {{{query}}}}}')}
        return requests.post(url=self.API_ENDPOINT, json=query, headers=self.headers)

    def detect_api_errors(self, response):
        """This function looks for errors in API response"""
        if 'errors' in response:
            msg = ""
            for err in response['errors']:
                msg += "\t" + err['message'] + "\n"
            self.logger.error("There are errors in github response:\n" + msg)
            sys.exit(1)

    def latest_version(self):
        """
        Get the latest project release number on Github

        :return: Version number or None
        """
        query = '''url
                releases(last: 1) {
                    nodes {
                      id
                      isPrerelease
                      isDraft
                      name
                  }
                }
            '''
        response = self.send_query(query).json()
        self.detect_api_errors(response)

        # check for empty response
        if response['data']['repository']['releases']['nodes']:
            release = response['data']['repository']['releases']['nodes'][0]
            if not release['isPrerelease'] and not release['isDraft']:
                return release['name']
            self.logger.debug("Latest github release is a Prerelease")
        else:
            self.logger.debug("There is no latest github release")
            return '0.0.0'
        return None

    def walk_through_closed_prs(self, start='', direction='after', which="last"):
        """
        Searches merged pull requests

        :param start: A cursor to start at
        :param direction: Direction to go from cursor
        :param which: Indicates which part of the result list
                      should be returned, can be 'first' or 'last'
        :return: API query response as an array
        """
        while True:
            query = (f"pullRequests(states: MERGED {which}: 5 " +
                     (f'{direction}: "{start}"' if start else '') +
                     '''){
                  edges {
                    cursor
                    node {
                      id
                      title
                      mergeCommit {
                        oid
                        author {
                            name
                            email
                        }
                      }
                    }
                  }
                }''')
            response = self.send_query(query).json()
            self.detect_api_errors(response)
            return response

    def make_new_release(self, new_release, previous_pypi_release):
        self.logger.info((f"found version: {new_release['version']}, "
                          f"commit id: {new_release['commitish']}"))
        payload = {"tag_name": new_release['version'],
                   "target_commitish": new_release['commitish'],
                   "name": new_release['version'],
                   "prerelease": False,
                   "draft": False}
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/releases")
        self.logger.info(f"Releasing {new_release['version']} on Github")
        response = requests.post(url=url, headers=self.headers, json=payload)
        if response.status_code != 201:
            response_get = requests.get(url=url, headers=self.headers)
            if (response_get.status_code == 200 and
                    [r for r in response_get.json() if r.get('name') == new_release['version']]):
                self.logger.warning(f"{new_release['version']} "
                                    f"has already been released on github")
                # to fill in new_release['fs_path'] so that we can continue with PyPi upload
                new_release = self.download_extract_zip(new_release)
            else:
                self.logger.error((f"Something went wrong with creating "
                                   f"new release on github:\n{response.text}"))
                sys.exit(1)
        else:
            new_release = self.download_extract_zip(new_release)
            self.update_changelog(previous_pypi_release,
                                  new_release['version'], new_release['fs_path'],
                                  response.json()['id'])
        return new_release

    def download_extract_zip(self, new_release):
        url = f"https://github.com/{self.conf.repository_owner}/{self.conf.repository_name}/" \
              f"archive/{new_release['version']}.zip"

        # download the new release to a temporary directory
        temp_directory = tempfile.TemporaryDirectory()
        new_release['tempdir'] = temp_directory
        response = requests.get(url=url)
        path = temp_directory.name + '/' + new_release['version']

        # extract it
        open(path + '.zip', 'wb').write(response.content)
        archive = zipfile.ZipFile(path + '.zip')
        archive.extractall(path=path)
        dirs = os.listdir(path)
        new_release['fs_path'] = path + "/" + dirs[0]

        return new_release

    def update_changelog(self, previous_pypi_release, new_version, fs_path, id_):
        # parse changelog and update the release with it
        changelog = parse_changelog(previous_pypi_release, new_version, fs_path)
        url = (f"{self.API3_ENDPOINT}repos/{self.conf.repository_owner}/"
               f"{self.conf.repository_name}/releases/{id_!s}")
        response = requests.post(url=url, json={'body': changelog}, headers=self.headers)
        if response.status_code != 200:
            self.logger.error((f"Something went wrong during changelog "
                               f"update for {new_version}:\n{response.text}"))


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
            self.logger.error(f"Pypi package '{self.conf.repository_name}' "
                              f"doesn't exist:\n{response.text}")
            sys.exit(1)

    def build_sdist(self, project_root):
        """
        Builds source distribution out of setup.py

        :param project_root: location of setup.py
        """
        if os.path.isfile(os.path.join(project_root, 'setup.py')):
            shell_command(project_root, "python setup.py sdist", "Cannot build sdist:")
        else:
            self.logger.error(f"Cannot find setup.py:")
            sys.exit(1)

    def build_wheel(self, project_root, python_version):
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
            self.logger.error(f"Unsupported python version: {python_version}")
            sys.exit(1)

        if not os.path.isfile(os.path.join(project_root, 'setup.py')):
            self.logger.error(f"Cannot find setup.py:")
            sys.exit(1)

        shell_command(project_root, f"{interpreter} setup.py bdist_wheel",
                      f"Cannot build wheel for python {python_version}")

    def upload(self, project_root):
        """
        Uploads the package distribution to PyPi

        :param project_root: directory with dist/ folder
        """
        if os.path.isdir(os.path.join(project_root, 'dist')):
            spec_files = glob.glob(os.path.join(project_root, "dist/*"))
            files = ""
            for file in spec_files:
                files += f"{file} "
            self.logger.debug(f"Uploading {files} to PyPi")
            shell_command(project_root, f"twine upload {files}",
                          "Cannot upload python distribution:")
        else:
            self.logger.error(f"dist/ folder cannot be found:")
            sys.exit(1)

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
            self.logger.error("Cannot find project root for PyPi release:")
            sys.exit(1)


class Fedora:
    def __init__(self, configuration):
        self.conf = configuration
        self.logger = configuration.logger

    def fedpkg_clone_repository(self, directory, name):
        if os.path.isdir(directory):
            shell_command(directory,
                          f"fedpkg clone {name!r}",
                          "Cloning fedora repository failed:")
            return os.path.join(directory, name)
        else:
            self.logger.error(f"Cannot clone fedpkg repository into non-existent directory:")
            sys.exit(1)

    def fedpkg_switch_branch(self, directory, branch, fail=True):
        if os.path.isdir(directory):
            return shell_command(directory,
                                 f"fedpkg switch-branch {branch}",
                                 f"Switching to {branch} failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    def fedpkg_build(self, directory, branch, scratch=False, fail=True):
        if os.path.isdir(directory):
            return shell_command(directory,
                                 f"fedpkg build {'--scratch' if scratch else ''}",
                                 f"Building branch {branch!r} in Fedora failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    def fedpkg_push(self, directory, branch, fail=True):
        if os.path.isdir(directory):
            return shell_command(directory,
                                 f"fedpkg push",
                                 f"Pushing branch {branch!r} to Fedora failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    def fedpkg_merge(self, directory, branch, ff_only=True, fail=True):
        if os.path.isdir(directory):
            return shell_command(directory,
                                 f"git merge master {'--ff-only' if ff_only else ''}",
                                 f"Merging master to branch {branch!r} failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    def fedpkg_commit(self, directory, branch, message, fail=True):
        if os.path.isdir(directory):
            return shell_command(directory,
                                 f"fedpkg commit -m '{message}'",
                                 f"Committing on branch {branch} failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    def fedpkg_sources(self, directory, branch, fail=True):
        if os.path.isdir(directory):
            return shell_command(directory,
                                 "fedpkg sources",
                                 f"Retrieving sources for branch {branch} failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    def fedpkg_spectool(self, directory, branch, fail=True):
        if os.path.isdir(directory):
            spec_files = glob.glob(os.path.join(directory, "*spec"))
            files = ""
            for file in spec_files:
                files += f"{file} "
            return shell_command(directory,
                                 f"spectool -g {files}",
                                 f"Retrieving new sources for branch {branch} failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    def fedpkg_lint(self, directory, branch, fail=True):
        if os.path.isdir(directory):
            return shell_command(directory,
                                 "fedpkg lint",
                                 f"Spec lint on branch {branch} failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    def fedpkg_new_sources(self, directory, branch, sources="", fail=True):
        if os.path.isdir(directory):
            return shell_command(directory,
                                 f"fedpkg new-sources {sources}",
                                 f"Adding new sources on branch {branch} failed:", fail)
        else:
            self.logger.error(f"Cannot access fedpkg repository:")
            sys.exit(1)

    @staticmethod
    def init_ticket(keytab, fas_username):
        if not fas_username:
            return False
        if keytab and os.path.isfile(keytab):
            cmd = f"kinit {fas_username}@FEDORAPROJECT.ORG -k -t {keytab}"
        else:
            # there is no keytab, but user still migh have active ticket - try to renew it
            cmd = f"kinit -R {fas_username}@FEDORAPROJECT.ORG"
        return shell_command(os.getcwd(), cmd, "Failed to init kerberos ticket:", False)

    def update_package(self, fedpkg_root, branch, new_release):
        """
        Pulls in new source, patches spec file, commits,
        pushes and builds new version on specified branch

        :param fedpkg_root: The root of dist-git repository
        :param branch: What Fedora branch is this
        :param new_release: an array containing info about new release, see main() for definition
        :return: True on success, False on failure
        """
        fail = True if branch.lower() == "master" else False

        # retrieve sources
        if not self.fedpkg_sources(fedpkg_root, branch, fail):
            return False

        # update spec file
        spec_path = os.path.join(fedpkg_root, f"{self.conf.repository_name}.spec")
        update_spec(spec_path, new_release)

        # check if spec file is valid
        if not self.fedpkg_lint(fedpkg_root, branch, fail):
            return False

        dir_listing = os.listdir(fedpkg_root)

        # get new source
        if not self.fedpkg_spectool(fedpkg_root, branch, fail):
            return False

        # find new sources
        dir_new_listing = os.listdir(fedpkg_root)
        sources = ""
        for item in dir_new_listing:
            if item not in dir_listing:
                # this is a new file therefore it should be added to sources
                sources += f"{item!r} "

        # if there are no new sources, abort update
        if len(sources.strip()) <= 0:
            self.logger.warning(
                "There are no new sources, won't continue releasing to fedora")
            return False

        # add new sources
        if not self.fedpkg_new_sources(fedpkg_root, branch, sources, fail):
            return False

        # commit this change, push it and start a build
        if not self.fedpkg_commit(fedpkg_root, branch, f"Update to {new_release['version']}", fail):
            return False
        if not self.fedpkg_push(fedpkg_root, branch, fail):
            return False
        if not self.fedpkg_build(fedpkg_root, branch, False, fail):
            return False
        return True

    def release(self, new_release):
        """
        Release project in Fedora

        :param new_release: an array containing info about new release, see main() for definition
        :return: True on successful release, False on unsuccessful
        """
        status = self.init_ticket(self.conf.keytab, self.conf.fas_username)
        if not status:
            self.logger.warning(
                f"Can't obtain a valid kerberos ticket, skipping fedora release")
            return False
        tmp = tempfile.TemporaryDirectory()

        # clone the repository from dist-git
        fedpkg_root = self.fedpkg_clone_repository(tmp.name, self.conf.repository_name)

        # make sure the current branch is master
        self.fedpkg_switch_branch(fedpkg_root, "master")

        # update package
        result = self.update_package(fedpkg_root, "master", new_release)
        if not result:
            tmp.cleanup()
            return False

        # cycle through other branches and merge the changes there, or do them from scratch, push, build
        for branch in new_release['fedora_branches']:
            if not self.fedpkg_switch_branch(fedpkg_root, branch, fail=False):
                continue
            if not self.fedpkg_merge(fedpkg_root, branch, True, False):
                self.logger.debug(
                    f"Trying to make the changes on branch {branch!r} from scratch")
                self.update_package(fedpkg_root, branch, new_release)
                continue
            if not self.fedpkg_push(fedpkg_root, branch, False):
                continue
                self.fedpkg_build(fedpkg_root, branch, False, False)

            # TODO: bodhi updates submission

        # clean directory
        tmp.cleanup()
        return True


class ReleaseBot:

    def __init__(self, configuration):
        self.conf = configuration
        self.github = Github(configuration)
        self.pypi = PyPi(configuration)
        self.fedora = Fedora(configuration)
        self.logger = configuration.logger
        self.logger.info(f"release-bot v{configuration.version} reporting for duty!")
        self.new_release = {}

    def find_pull_request_with_latest_pypi_release(self):
        latest_pypi = self.pypi.latest_version()
        self.logger.debug(f"Latest PyPi release: {latest_pypi}")

        cursor = ''
        found = False
        # try to find closed PR with latest_pypi version
        while not found:
            response = self.github.walk_through_closed_prs(cursor, 'before')
            if not response['data']['repository']['pullRequests']['edges']:
                self.logger.debug(f'No closed PR with the latest {latest_pypi} PyPI release found')
                cursor = ''
                break
            for edge in reversed(response['data']['repository']['pullRequests']['edges']):
                cursor = edge['cursor']
                if latest_pypi + ' release' == edge['node']['title'].lower():
                    self.logger.debug(
                        f'Found closed PR with the latest {latest_pypi} PyPi release')
                    found = True
                    break
        return cursor

    def check_for_new_pull_request_since_latest_pypi(self, cursor):
        while True:
            response = self.github.walk_through_closed_prs(cursor, which="first")
            if not response['data']['repository']['pullRequests']['edges']:
                self.logger.debug('No newer release PR found')
                self.new_release = {}
                return False
            for edge in response['data']['repository']['pullRequests']['edges']:
                cursor = edge['cursor']
                match = re.match(r'(.+) release', edge['node']['title'].lower())
                if match and validate(match[1]):
                    merge_commit = edge['node']['mergeCommit']
                    self.logger.debug(f'Found newer PR with version {match[1]}')
                    self.new_release = {'version': match[1],
                                        'commitish': merge_commit['oid'],
                                        'author_name': merge_commit['author']['name'],
                                        'author_email': merge_commit['author']['email']}
                    return True

    def make_new_pypi_release(self):
        # check if a new release was made
        latest_pypi = self.pypi.latest_version()
        if Version.coerce(latest_pypi) < Version.coerce(self.new_release['version']):
            self.logger.info("Newer version on github, triggering PyPi release")
            # load release configuration from release-conf.yaml in repository
            release_conf = self.conf.load_release_conf(os.path.join(self.new_release['fs_path'],
                                                                    'release-conf.yaml'))
            self.new_release.update(release_conf)
            self.pypi.release(self.new_release)
            if self.new_release['fedora']:
                self.logger.info("Triggering Fedora release")
                self.fedora.release(self.new_release)
            self.new_release['tempdir'].cleanup()
        else:
            self.logger.debug((f"PyPi version {latest_pypi} | "
                               f"Github version {self.github.latest_version()} -> nothing to do"))

    def make_new_github_release(self):
        self.new_release = self.github.make_new_release(self.new_release,
                                                        self.pypi.latest_version())
        return self.new_release

    def run(self):
        while True:
            cursor = self.find_pull_request_with_latest_pypi_release()
            # now walk through PRs since the latest_pypi version and check for a new one
            if cursor and self.check_for_new_pull_request_since_latest_pypi(cursor):
                # if found, make a new release on github
                # this has to be done using older github api because v4 doesn't support this yet
                if self.make_new_github_release():
                    self.make_new_pypi_release()
            time.sleep(self.conf.refresh_interval)


def main():
    parse_arguments()
    configuration.load_configuration()

    rb = ReleaseBot(configuration)
    rb.run()


if __name__ == '__main__':
    sys.exit(main())
