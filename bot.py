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

conf = {"repository_name": '',
        "repository_owner": '',
        "github_token": '',
        "refresh_interval": 3 * 60,
        "debug": False,
        "configuration": ''}
required_items = ['repository_name', 'repository_owner', 'github_token']


def print_help():
    print("""USAGE: python bot.py [OPTIONS] [--configuration file]
    \t -h, --help\t Displays this help
    \t -d, --debug\t Turns on debugging output
    \t -c, --configuration\t Uses custom YAML configuration
    """)
    sys.exit(0)


def debug_print(level=0, message=""):
    levels = ["[DEBUG]", "[WARNING]", "[ERROR]"]
    if conf['debug'] or level > 0:
        print(levels[level] + " " + message, file=sys.stderr if level > 0 else sys.stdout + "\n")


def parse_arguments(conf):
    opts, args = getopt.getopt(sys.argv[1:], "hdc:", ["help", "debug", "configuration="])
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


def load_configuration(conf):
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
    for item in required_items:
        if len(conf[item]) <= 0:
            debug_print(2, "Item '" + item + "' is required in configuration!")
            sys.exit(1)


parse_arguments(conf)
load_configuration(conf)

api_endpoint = "https://api.github.com/graphql"
api3_endpoint = "https://api.github.com/"
headers = {'Authorization': 'token %s' % conf['github_token']}
pypi_url = "https://pypi.python.org/pypi/" + conf['repository_name'] + "/json"
debug = True


def send_query(query):
    query = {"query": 'query {repository(owner: "' + conf['repository_owner'] + '", name: "' + conf[
        'repository_name'] + '") {' + query + '}}'}
    debug_print(message=str(query))
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
    r = requests.get(url=pypi_url)
    if r.status_code == 200:
        return r.json()['info']['version']
    else:
        debug_print(2, "Pypi package doesn't exist:\n" + r.text)


def release_on_pypi(project_root):
    if os.path.isdir(project_root):
        p = subprocess.Popen(
            "cd " + project_root + " && python setup.py sdist && python setup.py bdist_wheel && python3 setup.py bdist_wheel && twine upload dist/*",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        output, err = p.communicate()
        debug_print(0, output.decode('utf-8').strip())
        if p.returncode != 0:
            err = err.decode('utf-8').strip()
            debug_print(2, "PyPi release failed for some reason. Here's why:\n" + err)
            sys.exit(1)


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
def walk_through_closed_prs(start='', direction='after'):
    while True:
        q = '''pullRequests(states: MERGED last: 5 ''' + (direction + ': "' + start + '"' if len(start) > 0 else '') + ''') {
          edges {
            cursor
            node {
              id
              title
              mergedAt
              mergeCommit {
                oid
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
        print(edge['node']['title'])
        cursor = edge['cursor']
        if latest + ' release' == edge['node']['title'].lower():
            print('found!')
            found = True
# now walk through PRs since the latest version and check for a new one
while True:
    found = False
    new_release = {'version': '0.0.0', 'commitish': '', 'fs_path': '', 'tempdir': None}
    while not found:
        r = walk_through_closed_prs(cursor)
        if len(r['data']['repository']['pullRequests']['edges']) <= 0:
            break
        for edge in r['data']['repository']['pullRequests']['edges']:
            print(edge['node']['title'])
            cursor = edge['cursor']
            if re.match('\d\.\d\.\d release', edge['node']['title'].lower()):
                version = edge['node']['title'].split()
                new_release['version'] = version[0]
                new_release['commitish'] = edge['node']['mergeCommit']['oid']
                found = True

    # if found, make a new release on github
    # this has to be done using older github api because v4 doesn't support this yet
    if found:
        debug_print(message='found version: ' + new_release['version'] + ' , commit id: ' + new_release['commitish'])
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
        new_release['tempdir'].cleanup()
    time.sleep(conf['refresh_interval'])
