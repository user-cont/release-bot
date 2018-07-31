from tempfile import TemporaryDirectory
from os import path

from release_bot.utils import *
from release_bot.exceptions import GitException


class Git:

    def __init__(self, url, configuration):
        self.repo = self.clone(url)
        self.repo_path = self.repo.name
        self.credential_store = None
        self.conf = configuration
        self.logger = configuration.logger

    def clone(self, url):
        temp_directory = TemporaryDirectory()
        if not shell_command(temp_directory.name, f'git clone {url} .', "Couldn't clone repository!", fail=False):
            raise GitException(f"Can't clone repository {url}")
        return temp_directory

    def get_log_since_last_release(self, latest_version):
        success, changelog = shell_command_get_output(self.repo_path,
                                                      f'git log {latest_version}... --no-merges --format=\'* %s\'')
        return changelog if success and changelog else 'No changelog provided'

    def add(self, files: list):
        for file in files:
            success = shell_command(self.repo_path, f'git add {file}', '', False)
            if not success:
                raise GitException(f"Can't git add file {file}!")

    def commit(self, message='release commit'):
        success = shell_command(self.repo_path, f'git commit -m \"{message}\"', '', False)
        if not success:
            raise GitException(f"Can't commit files!")

    def push(self, branch):
        success = shell_command(self.repo_path, f'git push origin {branch}', '', False)
        if not success:
            raise GitException(f"Can't push branch {branch} to origin!")

    def set_credentials(self, name, email):
        email = shell_command(self.repo_path, f'git config user.email "{email}"', '', fail=False)
        name = shell_command(self.repo_path, f'git config user.name "{name}"', '', fail=False)
        return email and name

    def set_credential_store(self):
        if not self.credential_store:
            self.credential_store = TemporaryDirectory()
            store_path = path.join(self.credential_store.name, 'credentials')
            # write down credentials
            with open(store_path, 'w+') as credentials:
                credentials.write(
                    f'https://{self.conf.github_username}:{self.conf.github_token}@github.com/'
                    f'{self.conf.repository_owner}/{self.conf.repository_name}')
            # let git know
            with open(os.path.join(self.repo_path, '.git/config'), 'a+') as config:
                config.write(f'\n[credential]\n\thelper = store --file={store_path}\n')
        return path.join(self.credential_store.name, 'credentials')

    def checkout_new_branch(self, branch):
        return shell_command(self.repo_path, f'git checkout -b "{branch}"', '', fail=False)

    def cleanup(self):
        self.repo.cleanup()
