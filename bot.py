import requests
import json
import sys
import re
import tempfile
import time
import zipfile
import os
import getopt
import yaml
import subprocess
import locale

conf = {"repository_name": '',
        "repository_owner": '',
        "github_token": '',
        "refresh_interval": 3 * 60,
        "debug": False,
        "configuration": '',
        "fedora": False,
        "fedora_branches": []}
required_items = {"all": ['repository_name', 'repository_owner', 'github_token'],
                  "fedora": []}
api_endpoint = "https://api.github.com/graphql"
api3_endpoint = "https://api.github.com/"
pypi_url = "https://pypi.python.org/pypi/"


def print_help():
    print("""USAGE: python bot.py [OPTIONS] [--configuration file]
    \t -h, --help\t Displays this help
    \t -d, --debug\t Turns on debugging output
    \t -c, --configuration\t Uses custom YAML configuration
    \t --fedora\t Enable releasing on Fedora
    """)
    sys.exit(0)


def debug_print(level=0, message=""):
    levels = ["[DEBUG]", "[WARNING]", "[ERROR]"]
    if conf['debug'] or level > 0:
        print(levels[level] + " " + message + "\n", file=sys.stderr if level > 0 else sys.stdout)


def parse_arguments():
    opts, args = getopt.getopt(sys.argv[1:], "hdc:", ["help", "debug", "configuration=", "fedora"])
    for opt, arg in opts:
        if opt == '-h' or opt == '--help':
            print_help()
        elif opt == '-d' or opt == '--debug':
            conf['debug'] = True
        elif opt == '-c' or opt == '--configuration':
            path = arg
            if not os.path.isabs(path):
                path = os.path.join(os.getcwd(), path)
            if not os.path.isfile(path):
                debug_print(2, "Supplied configuration file is not found:" + path)
                sys.exit(1)
            conf['configuration'] = path
        elif opt == '--fedora':
            conf['fedora'] = True


def load_configuration():
    if len(conf['configuration']) <= 0:
        # configuration not supplied, look for conf.yaml in cwd
        path = os.path.join(os.getcwd(), 'conf.yaml')
        if os.path.isfile(path):
            conf['configuration'] = path
        else:
            debug_print(2, "Cannot find valid configuration")
            sys.exit(1)
    with open(conf['configuration'], 'r') as ymlfile:
        file = yaml.load(ymlfile)
    for item in file:
        if item in conf:
            conf[item] = file[item]
    # check if required items are present
    parts_required = ["all"]
    if conf['fedora']:
        parts_required.append('fedora')
    for part in parts_required:
        for item in required_items[part]:
            if len(conf[item]) <= 0:
                debug_print(2, "Item '" + item + "' is required in configuration!")
                sys.exit(1)


def send_query(query):
    query = {"query": 'query {repository(owner: "' + conf['repository_owner'] + '", name: "' + conf[
        'repository_name'] + '") {' + query + '}}'}
    headers = {'Authorization': 'token %s' % conf['github_token']}
    return requests.post(url=api_endpoint, json=query, headers=headers)


def detect_api_errors(response):
    if 'errors' in response:
        msg = ""
        for err in response['errors']:
            msg += "\t" + err['message'] + "\n"
        debug_print(2, "There are errors in github response:\n" + msg)
        sys.exit(1)


# returns changelog for selected version
def parse_changelog(previous_version, version, path):
    if os.path.isfile(path + "/CHANGELOG.md"):
        file = open(path + '/CHANGELOG.md', 'r').read()
        # detect position of this version header
        pos_start = file.find("# " + version)
        pos_end = file.find("# " + previous_version)
        return file[pos_start + len("# " + version):pos_end].strip()
    else:
        return "No changelog provided"


def get_latest_version_pypi():
    r = requests.get(url=pypi_url + str(conf['repository_name']) + '/json')
    if r.status_code == 200:
        return r.json()['info']['version']
    else:
        debug_print(2, "Pypi package doesn't exist:\n" + r.text)
        sys.exit(1)


# updates spec with new version and changelog for that version, changes release to 1
def update_spec(spec_path, config_path, author_name, author_email):
    if os.path.isfile(spec_path) and os.path.isfile(config_path):
        # make changelog and get version
        with open(config_path) as conf_file:
            release_conf = yaml.load(conf_file)
            # set changelog author
            if 'author_name' in release_conf and 'author_email' in release_conf:
                author_name = release_conf['author_name']
                author_email = release_conf['author_email']
            locale.setlocale(locale.LC_TIME, "en_US")
            changelog = "* " + time.strftime("%a %b %d %Y") + " " + str(author_name) + " <" + str(author_email) + "> " + \
                        release_conf['version'] + "-1\n"
            # add entries
            if 'changelog' in release_conf:
                for item in release_conf['changelog']:
                    changelog += "- " + item + "\n"
            else:
                changelog += "- " + release_conf['version'] + " release"
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
            debug_print(2, "release-conf.yaml is not found in repository root!\n")
        else:
            debug_print(2, "Spec file is not found in  dist-git repository!\n")
        sys.exit(1)


def shell_command(workdir, cmd, error_message):
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        cwd=workdir)
    output, err = p.communicate()
    debug_print(0, output.decode('utf-8').strip())
    if p.returncode != 0:
        err = err.decode('utf-8').strip()
        debug_print(2, error_message + "\n" + err)
        sys.exit(1)


def release_on_pypi(project_root):
    if os.path.isdir(project_root):
        shell_command(project_root,
                      "python setup.py sdist && python setup.py bdist_wheel && python3 setup.py bdist_wheel && twine upload dist/*",
                      "PyPi release failed for some reason. Here's why:")


def release_in_fedora(project_root, new_version, author_name, author_email):
    tmp = tempfile.TemporaryDirectory()

    # clone the repository from dist-git and change into that directory and switch to master
    shell_command(tmp.name, "fedpkg clone " + conf['repository_name'] + " && cd " + conf[
        "repository_name"] + " && fedpkg switch-branch master", "Cloning fedora repository failed:")

    # this is now source directory
    fedpkg_src = tmp.name + "/" + str(conf['repository_name'])

    # retrieve sources
    shell_command(fedpkg_src, "fedpkg sources", "Retrieving sources failed:")

    # update spec file
    spec_path = fedpkg_src + "/" + str(conf["repository_name"]) + ".spec"
    conf_path = project_root + "/release-conf.yaml"
    update_spec(spec_path, conf_path, author_name, author_email)

    dir_listing = os.listdir(fedpkg_src)

    # get new source
    shell_command(fedpkg_src, "spectool -g *spec", "Retrieving new sources failed:")

    # find new sources
    dir_new_listing = os.listdir(fedpkg_src)
    sources = ""
    for item in dir_new_listing:
        if item not in dir_listing:
            # this is a new file therefore it should be added to sources
            sources += item + " "

    # if there are no new sources, abort update
    if len(sources.strip()) <= 0:
        debug_print(1, "There are no new sources, won't continue releasing to fedora")
        tmp.cleanup()
        return

    # add new sources
    cmd = "fedpkg new-sources " + sources
    shell_command(fedpkg_src, cmd, "Adding new sources failed:")

    # commit this change and start a build
    commit_msg = "Update to " + new_version
    shell_command(fedpkg_src, 'fedpkg commit -m "' + commit_msg + '" && fedpkg push && fedpkg build',
                  "Committing or building failed:")

    # load branches
    with open(conf_path, 'r') as release_conf_file:
        release_conf = yaml.load(release_conf_file)
        if 'fedora_branches' in release_conf:
            conf['fedora_branches'] = release_conf['fedora_branches']

    # cycle through other branches and merge the changes there, push, build
    for branch in conf['fedora_branches']:
        p = subprocess.Popen("fedpkg switch-branch " + str(
            branch) + " && git merge master && fedpkg push && fedpkg build",
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True,
                             cwd=fedpkg_src)
        output, err = p.communicate()
        debug_print(0, output.decode('utf-8').strip())
        if p.returncode != 0:
            err = err.decode('utf-8').strip()
            debug_print(1, "Merging od building on branch " + branch + " failed:\n" + err)
            continue

        # TODO: bodhi updates submission

    # clean directory
    tmp.cleanup()


def get_latest_version_github():
    q = '''url
            releases(last: 1) {
                nodes {
                  id
                  isPrerelease
                  isDraft
                  name
              }
            }
        '''
    r = send_query(q).text
    r = json.loads(r)

    detect_api_errors(r)

    release = r['data']['repository']['releases']['nodes'][0]
    if not release['isPrerelease'] and not release['isDraft']:
        return release['name']
    else:
        debug_print(1, "Latest github release is a Prerelease")
        return None


# checks closed PRs
def walk_through_closed_prs(start='', direction='after', which="last"):
    while True:
        q = '''pullRequests(states: MERGED ''' + which + ''': 5 ''' + (direction + ': "' + start + '"' if len(start) > 0 else '') + ''') {
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
        }'''
        r = send_query(q).text
        r = json.loads(r)
        detect_api_errors(r)
        return r


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


def main():
    parse_arguments()
    load_configuration()
    headers = {'Authorization': 'token %s' % conf['github_token']}

    # check for closed merge requests
    latest = get_latest_version_pypi()
    cursor = ''
    found = False
    # try to find the latest release closed merge request
    while not found:
        r = walk_through_closed_prs(cursor, 'before')
        if len(r['data']['repository']['pullRequests']['edges']) == 0:
            break
        for edge in reversed(r['data']['repository']['pullRequests']['edges']):
            cursor = edge['cursor']
            if latest + ' release' == edge['node']['title'].lower():
                debug_print(0, 'Found closed PR with PyPi release: "' + latest + ' release"')
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
                       'tempdir': None,
                       }
        while True:
            r = walk_through_closed_prs(cursor, which="first")
            if len(r['data']['repository']['pullRequests']['edges']) <= 0:
                break
            for edge in r['data']['repository']['pullRequests']['edges']:
                cursor = edge['cursor']
                if re.match('\d\.\d\.\d release', edge['node']['title'].lower()):
                    version = edge['node']['title'].split()
                    new_release['version'] = version[0]
                    new_release['commitish'] = edge['node']['mergeCommit']['oid']
                    new_release['merge_author_name'] = edge['node']['mergeCommit']['author']['name']
                    new_release['merge_author_email'] = edge['node']['mergeCommit']['author']['email']
                    found = True
                    break

        # if found, make a new release on github
        # this has to be done using older github api because v4 doesn't support this yet
        if found:
            debug_print(message='found version: ' + new_release['version'] + ', commit id: ' + new_release['commitish'])
            payload = {"tag_name": new_release['version'],
                       "target_commitish": new_release['commitish'],
                       "name": new_release['version'],
                       "prerelease": False,
                       "draft": False}
            url = api3_endpoint + 'repos/' + conf['repository_owner'] + '/' + conf['repository_name'] + '/releases'
            response = requests.post(url=url, headers=headers, json=payload)
            if response.status_code != 201:
                debug_print(2, "Something went wrong with creating new release on github:\n" + response.text)
                sys.exit(1)
            else:
                # download the new release to a temporary directory
                d = tempfile.TemporaryDirectory()
                new_release['tempdir'] = d
                info = json.loads(response.text)
                r = requests.get(url=info['zipball_url'])
                path = d.name + '/' + new_release['version']

                # extract it
                open(path + '.zip', 'wb').write(r.content)
                archive = zipfile.ZipFile(path + '.zip')
                archive.extractall(path=path)
                dirs = os.listdir(path)
                new_release['fs_path'] = path + "/" + dirs[0]

                # parse changelog and update the release with it
                changelog = parse_changelog(latest, new_release['version'], new_release['fs_path'])
                url = api3_endpoint + 'repos/' + conf['repository_owner'] + '/' + conf[
                    'repository_name'] + '/releases/' + str(info['id'])
                response = requests.post(url=url, json={'body': changelog}, headers=headers)
                if response.status_code != 200:
                    print(2, "Something went wrong during changelog update for a release:\n" + response.text)
                    sys.exit(1)

        latest = get_latest_version_pypi()
        # check if a new release was made
        if version_tuple(latest) < version_tuple(new_release['version']):
            debug_print(0, "Newer version on github, triggering PyPi release")
            release_on_pypi(new_release['fs_path'])
            if conf['fedora']:
                debug_print(0, "Triggering Fedora release")
                release_in_fedora(new_release['fs_path'], new_release['version'], new_release['merge_author_name'],
                                  new_release['merge_author_email'])
            new_release['tempdir'].cleanup()
        else:
            debug_print(0,
                        "PyPi version " + latest + " | Github version " + get_latest_version_github() + " -> nothing to do")
        time.sleep(conf['refresh_interval'])


if __name__ == '__main__':
    sys.exit(main())
