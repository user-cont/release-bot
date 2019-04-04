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
This module is backend for WSGI.
"""
from flask import request, jsonify
from flask.views import View

from release_bot.exceptions import ReleaseException


class GithubWebhooksHandler(View):
    """
        Handler for github callbacks.
    """

    def __init__(self, release_bot, conf):
        self.release_bot = release_bot
        self.conf = conf
        self.logger = conf.logger

    def dispatch_request(self):
        self.logger.info(f'New github webhook call from '
                         f'{self.conf.repository_owner}/{self.conf.repository_name}')
        if request.is_json:
            self.parse_payload(request.get_json())
        else:
            self.logger.error("This webhook doesn't contain JSON")
        return jsonify(result={"status": 200})

    def parse_payload(self, webhook_payload):
        """
        Parse json webhook payload callback
        :param webhook_payload: json from github webhook
        """
        self.logger.info(f"release-bot v{self.conf.version} reporting for duty!")
        if 'issue' in webhook_payload.keys():
            if webhook_payload['action'] == 'opened':
                self.handle_issue()
        elif 'pull_request' in webhook_payload.keys():
            if webhook_payload['action'] == 'closed':
                if webhook_payload['pull_request']['merged'] is True:
                    self.handle_pr()
        else:
            self.logger.info("This webhook doesn't contain opened issue or merged PR")
        self.logger.debug("Done. Waiting for another github webhook callback")

    def handle_issue(self):
        """Handler for newly opened issues"""
        self.logger.info("Resolving opened issue")
        self.release_bot.git.pull()
        try:
            self.release_bot.load_release_conf()
            if (self.release_bot.new_release.get('trigger_on_issue') and
                    self.release_bot.find_open_release_issues()):
                if self.release_bot.new_release.get('labels') is not None:
                    self.release_bot.github.put_labels_on_issue(
                        self.release_bot.new_pr['issue_number'],
                        self.release_bot.new_release.get('labels'))
                self.release_bot.make_release_pull_request()
        except ReleaseException as exc:
            self.logger.error(exc)

    def handle_pr(self):
        """Handler for merged PR"""
        self.logger.info("Resolving opened PR")
        self.release_bot.git.pull()
        try:
            self.release_bot.load_release_conf()
            if self.release_bot.find_newest_release_pull_request():
                self.release_bot.make_new_github_release()
                # Try to do PyPi release regardless whether we just did github release
                # for case that in previous iteration (of the 'while True' loop)
                # we succeeded with github release, but failed with PyPi release
                self.release_bot.make_new_pypi_release()
        except ReleaseException as exc:
            self.logger.error(exc)
        self.release_bot.github.add_comment(self.release_bot.new_release.get('pr_id'))
