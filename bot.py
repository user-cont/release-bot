"""
This module provides functionality for automation of releasing projects
into various downstream services
"""
import json
import sys
import re
import tempfile
from datetime import datetime
import time
import zipfile
import os
import argparse
import subprocess
import locale
import logging
import yaml
import requests

CONFIGURATION = {"repository_name": '',
                 "repository_owner": '',
                 "github_token": '',
                 "refresh_interval": 3 * 60,
                 "debug": False,
                 "configuration": '',
                 "fedora": False,
                 "fedora_branches": [],
                 "logger": None}
REQUIRED_ITEMS = {"all": ['repository_name', 'repository_owner', 'github_token'],
                  "fedora": []}
API_ENDPOINT = "https://api.github.com/graphql"
API3_ENDPOINT = "https://api.github.com/"
PYPI_URL = "https://pypi.python.org/pypi/"


def parse_arguments():
    """Parse application arguments"""
    parser = argparse.ArgumentParser(description="Automatic releases bot")
    parser.add_argument("-d", "--debug", help="turn on debugging output",
                        action="store_true", default=False)
    parser.add_argument("-c", "--configuration", help="use custom YAML configuration",
                        default='')
    parser.add_argument("--fedora", help="enable releasing on Fedora",
                        action="store_true", default=False)

    args = parser.parse_args()
    if 'configuration' in args:
        path = args.configuration
        if not os.path.isabs(path):
            args.configuration = os.path.join(os.getcwd(), path)
        if not os.path.isfile(path):
            CONFIGURATION['logger'].error(
                f"Supplied configuration file is not found: {args.configuration}")
            sys.exit(1)
    if args.debug:
        CONFIGURATION['logger'].setLevel(logging.DEBUG)
    for key, value in vars(args).items():
        CONFIGURATION[key] = value


def set_logging(
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

    return logger


def load_configuration():
    """Load bot configuration from .yaml file"""
    if len(CONFIGURATION['configuration']) <= 0:
        # configuration not supplied, look for conf.yaml in cwd
        path = os.path.join(os.getcwd(), 'conf.yaml')
        if os.path.isfile(path):
            CONFIGURATION['configuration'] = path
        else:
            CONFIGURATION['logger'].error("Cannot find valid configuration")
            sys.exit(1)
    with open(CONFIGURATION['configuration'], 'r') as ymlfile:
        file = yaml.load(ymlfile)
    for item in file:
        if item in CONFIGURATION:
            CONFIGURATION[item] = file[item]
    # check if required items are present
    parts_required = ["all"]
    if CONFIGURATION['fedora']:
        parts_required.append('fedora')
    for part in parts_required:
        for item in REQUIRED_ITEMS[part]:
            if len(CONFIGURATION[item]) <= 0:
                CONFIGURATION['logger'].error(f"Item {item!r} is required in configuration!")
                sys.exit(1)
    # make sure the types are right where it matters
    str(CONFIGURATION['repository_name'])
    str(CONFIGURATION['repository_owner'])


def send_query(query):
    """Send query to Github v4 API and return the response"""
    query = {"query": (f'query {{repository(owner: "{CONFIGURATION["repository_owner"]}", '
                       f'name: "{CONFIGURATION["repository_name"]}") {{{query}}}}}')}
    headers = {'Authorization': 'token %s' % CONFIGURATION['github_token']}
    return requests.post(url=API_ENDPOINT, json=query, headers=headers)


def detect_api_errors(response):
    """This function looks for errors in API response"""
    if 'errors' in response:
        msg = ""
        for err in response['errors']:
            msg += "\t" + err['message'] + "\n"
        CONFIGURATION['logger'].error("There are errors in github response:\n" + msg)
        sys.exit(1)


def parse_changelog(previous_version, version, path):
    """
    Get changelog for selected version

    :param str previous_version: Version before the new one
    :param str version: A new version
    :param str path: Path to CHANGELOG.md
    :return: Changelog entry or placeholder entry if no changelog is found
    """
    if os.path.isfile(path + "/CHANGELOG.md"):
        file = open(path + '/CHANGELOG.md', 'r').read()
        # detect position of this version header
        pos_start = file.find("# " + version)
        pos_end = file.find("# " + previous_version)
        return file[pos_start + len("# " + version):pos_end].strip()
    return "No changelog provided"


def get_latest_version_pypi():
    """Get latest version of the package from PyPi"""
    response = requests.get(url=f"{PYPI_URL}{CONFIGURATION['repository_name']}/json")
    if response.status_code == 200:
        return response.json()['info']['version']
    else:
        CONFIGURATION['logger'].error(f"Pypi package doesn't exist:\n{response.text}")
        sys.exit(1)


def update_spec(spec_path, config_path, author_name, author_email):
    """
    Update spec with new version and changelog for that version, change release to 1

    :param spec_path: Path to package .spec file
    :param config_path: Path to repository configuration
    :param author_name: Merge commit author
    :param author_email: Merge commit author's email
    """
    if os.path.isfile(spec_path) and os.path.isfile(config_path):
        # make changelog and get version
        with open(config_path) as conf_file:
            release_conf = yaml.load(conf_file)
            # set changelog author
            if 'author_name' in release_conf and 'author_email' in release_conf:
                author_name = release_conf['author_name']
                author_email = release_conf['author_email']
            locale.setlocale(locale.LC_TIME, "en_US")
            changelog = (f"* {datetime.now():%a %b %d %Y} {author_name!s} "
                         f"<{author_email!s}> {release_conf['version']}-1\n")
            # add entries
            if 'changelog' in release_conf:
                for item in release_conf['changelog']:
                    changelog += f"- {item}\n"
            else:
                changelog += f"- {release_conf['version']} release"
        # change the version and add changelog in spec file
        with open(spec_path, 'r+') as spec_file:
            spec = spec_file.read()
            # replace version
            spec = re.sub(r'(Version:\s*)([0-9]|[.])*', r'\g<1>' + release_conf['version'], spec)
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
        if not os.path.isfile(config_path):
            CONFIGURATION['logger'].error("release-conf.yaml is not found in repository root!\n")
        else:
            CONFIGURATION['logger'].error("Spec file is not found in  dist-git repository!\n")
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
    shell = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=work_directory,
        universal_newlines=True)
    CONFIGURATION['logger'].debug(f"{shell.args}\n{shell.stdout}")
    if shell.returncode != 0:
        CONFIGURATION['logger'].error(f"{error_message}\n{shell.stderr}")
        if fail:
            sys.exit(1)
        return False
    return True


def release_on_pypi(project_root):
    """
    Release project on PyPi

    :param project_root: The root directory of the project
    """
    error_message = "PyPi release failed for some reason. Here's why:"
    if os.path.isdir(project_root):
        shell_command(project_root, "python setup.py sdist", error_message)
        shell_command(project_root, "python setup.py bdist_wheel", error_message)
        shell_command(project_root, "python3 setup.py bdist_wheel", error_message)
        shell_command(project_root, "twine upload dist/*", error_message)


def update_package(fedpkg_root, project_root, new_version, author_name, author_email, branch):
    """
    Pulls in new source, patches spec file, commits,
    pushes and builds new version on specified branch

    :param fedpkg_root: The root of dist-git repository
    :param project_root: The root directory of the project
    :param new_version: New version number
    :param author_name: Merge commit author
    :param author_email: Merge commit author's email
    :param branch: What Fedora branch is this
    :return: True on success, False on failure
    """
    fail = True if branch.lower() == "master" else False

    # retrieve sources
    if not shell_command(fedpkg_root,
                         "fedpkg sources",
                         "Retrieving sources failed:",
                         fail):
        return False

    # update spec file
    spec_path = f"{fedpkg_root}/{CONFIGURATION['repository_name']!r}.spec"
    conf_path = f"{project_root}/release-conf.yaml"
    update_spec(spec_path, conf_path, author_name, author_email)

    dir_listing = os.listdir(fedpkg_root)

    # get new source
    if not shell_command(fedpkg_root,
                         "spectool -g *spec",
                         "Retrieving new sources failed:",
                         fail):
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
        CONFIGURATION['logger'].warning(
            "There are no new sources, won't continue releasing to fedora")
        return False

    # add new sources
    if not shell_command(fedpkg_root,
                         f"fedpkg new-sources {sources}",
                         "Adding new sources failed:",
                         fail):
        return False

    # commit this change, push it and start a build
    if not shell_command(fedpkg_root,
                         f"fedpkg commit -m 'Update to {new_version}'",
                         "Committing on master branch failed:",
                         fail):
        return False
    if not shell_command(fedpkg_root,
                         "fedpkg push",
                         f"Pushing {branch!r} branch failed:",
                         fail):
        return False
    if not shell_command(fedpkg_root,
                         "fedpkg build",
                         f"Building {branch!r} branch failed:",
                         fail):
        return False
    return True


def release_in_fedora(project_root, new_version, author_name, author_email):
    """
    Release project in Fedora

    :param project_root: The root directory of the project
    :param new_version: New version number
    :param author_name: Merge commit author
    :param author_email: Merge commit author's email
    """
    tmp = tempfile.TemporaryDirectory()

    # clone the repository from dist-git
    shell_command(tmp.name,
                  f"fedpkg clone {CONFIGURATION['repository_name']!r}",
                  "Cloning fedora repository failed:")

    # this is now source directory
    fedpkg_root = f"{tmp.name}/{CONFIGURATION['repository_name']!r}"
    # make sure the current branch is master
    shell_command(fedpkg_root,
                  "fedpkg switch-branch master",
                  "Switching to master failed:")

    result = update_package(fedpkg_root,
                            project_root,
                            new_version,
                            author_name,
                            author_email,
                            "master")
    if not result:
        tmp.cleanup()
        return

    # load branches
    conf_path = f"{project_root}/release-conf.yaml"
    with open(conf_path, 'r') as release_conf_file:
        release_conf = yaml.load(release_conf_file)
        if 'fedora_branches' in release_conf:
            CONFIGURATION['fedora_branches'] = str(release_conf['fedora_branches'])

    # cycle through other branches and merge the changes there, or do them from scratch, push, build
    for branch in CONFIGURATION['fedora_branches']:
        if not shell_command(fedpkg_root,
                             f"fedpkg switch-branch {branch!r}",
                             f"Switching to branch {branch!r} failed:", fail=False):
            continue
        if not shell_command(fedpkg_root,
                             f"git merge master --ff-only",
                             f"Merging master to branch {branch!r} failed:", fail=False):
            CONFIGURATION['logger'].debug(
                f"Trying to make the changes on branch {branch!r} from scratch")
            update_package(fedpkg_root,
                           project_root,
                           new_version,
                           author_name,
                           author_email,
                           branch)
            continue
        if not shell_command(fedpkg_root,
                             "fedpkg push",
                             f"Pushing branch {branch!r} to Fedora failed:", fail=False):
            continue
        shell_command(fedpkg_root,
                      "fedpkg build",
                      f"Building branch {branch!r} in Fedora failed:", fail=False)

        # TODO: bodhi updates submission

    # clean directory
    tmp.cleanup()


def get_latest_version_github():
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
    response = send_query(query).text
    response = json.loads(response)

    detect_api_errors(response)

    release = response['data']['repository']['releases']['nodes'][0]
    if not release['isPrerelease'] and not release['isDraft']:
        return release['name']
    CONFIGURATION['logger'].warning("Latest github release is a Prerelease")
    return None


def walk_through_closed_prs(start='', direction='after', which="last"):
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
        response = send_query(query).text
        response = json.loads(response)
        detect_api_errors(response)
        return response


def version_tuple(version):
    """
    Converts version number to a tuple

    :param str version: Version number
    :return: Version number as a tuple
    """
    return tuple(map(int, (version.split("."))))


def main():
    """Provides bot logic"""
    CONFIGURATION['logger'] = set_logging()
    CONFIGURATION['logger'].info("Release bot reporting for duty!")

    parse_arguments()
    load_configuration()
    headers = {'Authorization': f"token {CONFIGURATION['github_token']}"}

    # check for closed merge requests
    latest = get_latest_version_pypi()
    cursor = ''
    found = False
    # try to find the latest release closed merge request
    while not found:
        response = walk_through_closed_prs(cursor, 'before')
        if not response['data']['repository']['pullRequests']['edges']:
            break
        for edge in reversed(response['data']['repository']['pullRequests']['edges']):
            cursor = edge['cursor']
            if latest + ' release' == edge['node']['title'].lower():
                CONFIGURATION['logger'].debug(
                    f'Found closed PR with PyPi release: "{latest} release"')
                found = True
                break
    # now walk through PRs since the latest version and check for a new one
    while True:
        found = False
        new_release = {'version': '0.0.0',
                       'commitish': '',
                       'merge_author_name': '',
                       'merge_author_email': '',
                       'fs_path': '',
                       'tempdir': None}
        while True:
            response = walk_through_closed_prs(cursor, which="first")
            if len(response['data']['repository']['pullRequests']['edges']) <= 0:
                break
            for edge in response['data']['repository']['pullRequests']['edges']:
                cursor = edge['cursor']
                if re.match(r'\d\.\d\.\d release', edge['node']['title'].lower()):
                    version = edge['node']['title'].split()
                    new_release['version'] = version[0]
                    merge_commit = edge['node']['mergeCommit']
                    new_release['commitish'] = merge_commit['oid']
                    new_release['merge_author_name'] = merge_commit['author']['name']
                    new_release['merge_author_email'] = merge_commit['author']['email']
                    found = True
                    break

        # if found, make a new release on github
        # this has to be done using older github api because v4 doesn't support this yet
        if found:
            CONFIGURATION['logger'].error(message=(f"found version: {new_release['version']}, "
                                                   f"commit id: {new_release['commitish']}"))
            payload = {"tag_name": new_release['version'],
                       "target_commitish": new_release['commitish'],
                       "name": new_release['version'],
                       "prerelease": False,
                       "draft": False}
            url = (f"{API3_ENDPOINT}repos/{CONFIGURATION['repository_owner']}/"
                   f"{CONFIGURATION['repository_name']}/releases")
            response = requests.post(url=url, headers=headers, json=payload)
            if response.status_code != 201:
                CONFIGURATION['logger'].error((f"Something went wrong with creating "
                                               f"new release on github:\n{response.text}"))
                sys.exit(1)
            else:
                # download the new release to a temporary directory
                temp_directory = tempfile.TemporaryDirectory()
                new_release['tempdir'] = temp_directory
                info = json.loads(response.text)
                response = requests.get(url=info['zipball_url'])
                path = temp_directory.name + '/' + new_release['version']

                # extract it
                open(path + '.zip', 'wb').write(response.content)
                archive = zipfile.ZipFile(path + '.zip')
                archive.extractall(path=path)
                dirs = os.listdir(path)
                new_release['fs_path'] = path + "/" + dirs[0]

                # parse changelog and update the release with it
                changelog = parse_changelog(latest, new_release['version'], new_release['fs_path'])
                url = (f"{API3_ENDPOINT}repos/{CONFIGURATION['repository_owner']}/"
                       f"{CONFIGURATION['repository_name']}/releases/{info['id']!s}")
                response = requests.post(url=url, json={'body': changelog}, headers=headers)
                if response.status_code != 200:
                    print(2, (f"Something went wrong during changelog "
                              f"update for a release:\n{response.text}"))
                    sys.exit(1)

        latest = get_latest_version_pypi()
        # check if a new release was made
        if version_tuple(latest) < version_tuple(new_release['version']):
            CONFIGURATION['logger'].debug("Newer version on github, triggering PyPi release")
            release_on_pypi(new_release['fs_path'])
            if CONFIGURATION['fedora']:
                CONFIGURATION['logger'].debug("Triggering Fedora release")
                release_in_fedora(new_release['fs_path'],
                                  new_release['version'],
                                  new_release['merge_author_name'],
                                  new_release['merge_author_email'])
            new_release['tempdir'].cleanup()
        else:
            CONFIGURATION['logger'].debug((f"PyPi version {latest} | "
                                           f"Github version {get_latest_version_github()} "
                                           "-> nothing to do"))
        time.sleep(CONFIGURATION['refresh_interval'])


if __name__ == '__main__':
    sys.exit(main())
