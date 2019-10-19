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

"""
This module initializes a repo to be used by ReleaseBot
"""
import os
import re
import yaml

from release_bot.utils import run_command_get_output

TEMPLATE_STRING = """{{#general_title}}
# {{{title}}}

{{/general_title}}
{{#versions}}

{{#sections}}
### {{{label}}}

{{#commits}}
* {{{subject}}} [{{{author}}}]
{{#body}}

{{{body_indented}}}
{{/body}}

{{/commits}}
{{/sections}}

{{/versions}}"""

GITCHANGELOG_RC_STRING = """
output_engine =  mustache("markdown.tpl")
"""

class Init:
    """
    Creates all of the required configuration script required for the ReleaseBot
    """
    def __init__(self):
        self.conf = {
            'repository_name': '<repository_name>',
            'repository_owner': '<owner_of_repository>',
            'github_token': '<your_github_token>',
            'refresh_interval': '180',
            'github_username': '<your_github_username>',
            'gitchangelog': False,
        }
        self.release_conf = {
            'trigger_on_issue': True,
            'author_email': '<your_email>',
            'author_name': '<your_name>',
            'labels': []
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is KeyboardInterrupt:
            print("\nOperation aborted by user.")
            return True
        return exc_type is None

    def run(self, silent):
        """
        Performs all the init tasks
        """
        self.create_conf(silent)
        self.append_to_gitignore()
        if self.conf['gitchangelog']:
            self.create_template()
            self.create_gitchangelog_rc()
        if silent:
            conclude = """Successfully initialized the repository
Please first modify all value with '< >' in the release.conf.
Then commit all of the changes made to the repo and
from shell run 'release-bot -c conf.yaml"""
        else:
            conclude = """Successfully initialized the repository
Please commit all of the changes made to the repo and
from shell run 'release-bot -c conf.yaml'"""

        print(conclude)

    def create_conf(self, silent):
        """
        Create the release-conf.yaml and conf.yaml
        """
        cwd = os.getcwd()
        self.release_conf['author_email'] = run_command_get_output(cwd, f'git config user.email')[1].strip()
        self.release_conf['author_name'] = run_command_get_output(cwd, f'git config user.name')[1].strip()
        if self.release_conf['author_email'] == "":
            print("WARNING: your e-mail ID from git config is not set."+
                  "\nPlease set it using 'git config user.email \"email@example.com\"'")
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", self.release_conf["author_email"]):
            print("WARNING: your e-mail ID from git config is not a valid e-mail address.")
        if self.release_conf['author_name'] == "":
            print("WARNING: your username from git config is not set." +
                  "\nPlease set it using 'git config user.name \"John Doe\"'")
        if not silent:
            self.conf['repository_name'] = input('Please enter the repository name:')
            self.conf['repository_owner'] = input('Please enter the repository owner:')
            print("""For details on how to get github token checkout
    'https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/'""")
            self.conf['github_token'] = input('Please enter your valid github token:')
            refresh_interval = "dummy"
            while not (refresh_interval.isdigit() or refresh_interval == ""):
                refresh_interval = input("""In how many seconds would you like the
    bot to check for updates (Default 180):""")
            if refresh_interval > 0:
                self.conf['refresh_interval'] = int(refresh_interval)
            else:
                self.conf['refresh_interval'] = None
            is_owner_user = input('Are you the owner of the repo? (Y/n):')
            if is_owner_user.lower() == 'y' or is_owner_user == '':
                self.conf['github_username'] = self.conf['repository_owner']
            else:
                self.conf['github_username'] = input('Please enter your github usename:')
            trigger_on_issue = input('Would you like to trigger release from issue? (Y/n):')
            self.release_conf['trigger_on_issue'] = bool(
                trigger_on_issue.lower() == 'y' or trigger_on_issue == ''
            )
            gitchangelog = input(
                'Would you like to use gitchangelog to generate next-gen changelogs? (Y/n):'
                )
            self.conf['gitchangelog'] = bool(
                gitchangelog.lower() == 'y' or gitchangelog == ''
            )

        self.create_yaml(self.conf, 'conf.yaml')
        self.create_yaml(self.release_conf, 'release-conf.yaml')

    @staticmethod
    def append_to_gitignore():
        """
        Append conf.yaml to the gitignore
        """
        with open('.gitignore', 'a+') as gitignore_file:
            gitignore_file.write('\nconf.yaml')


    @staticmethod
    def create_yaml(_dict, file_name):
        """
        Create or overwrite yaml file
        :param dict: dict to be converted to yaml
        :param filename: name of the yaml file to create
        """
        def dump_yaml():
            """
            Dumps the yaml into the file
            """
            with open(file_name, 'w') as yaml_file:
                yaml.safe_dump(_dict, yaml_file, default_flow_style=False)

        if not os.path.isfile(file_name):
            dump_yaml()
        else:
            should_overrite = input(
                file_name+" already exists, would you like to overwrite it? (y/N):"
                )
            if should_overrite.lower() == 'y':
                dump_yaml()

    @staticmethod
    def create_template():
        """
        Creates template file for the Markdown output
        """
        with open('markdown.tpl', 'w') as template_file:
            template_file.write(TEMPLATE_STRING)

    @staticmethod
    def create_gitchangelog_rc():
        """
        Creates the .gitchangelog.rc file for the git change log config
        """
        with open('.gitchangelog.rc', 'w') as gitchangelog_rc_file:
            gitchangelog_rc_file.write(GITCHANGELOG_RC_STRING)
