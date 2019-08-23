# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from pathlib import Path
from os import getenv

from release_bot.celerizer import celery_app
from release_bot.exceptions import ReleaseException
from release_bot.configuration import configuration
from release_bot.releasebot import ReleaseBot


@celery_app.task(bind=True, name="task.celery_task.parse_web_hook_payload")
def parse_web_hook_payload(self, webhook_payload):
    """
    Parse json webhook payload callback
    :param webhook_payload: json from github webhook
    """
    if 'issue' in webhook_payload.keys():
        if webhook_payload['action'] == 'opened':
            handle_issue(webhook_payload)
    elif 'pull_request' in webhook_payload.keys():
        if webhook_payload['action'] == 'closed':
            if webhook_payload['pull_request']['merged'] is True:
                handle_pr(webhook_payload)


def handle_issue(webhook_payload):
    """Handler for newly opened issues"""
    # configuration.configuration = Path(
    #     '/Users/marusinm/Documents/Python/tmp/bot-test-conf/conf.yaml').resolve()
    configuration.configuration = Path(getenv("CONF_PATH", "/secrets/prod/conf.yaml")).resolve()

    # add configuration from Github webhook
    configuration.repository_name = webhook_payload['repository']['name']
    configuration.repository_owner = webhook_payload['repository']['owner']['login']
    configuration.github_username = webhook_payload['issue']['user']['login']
    configuration.clone_url = webhook_payload['repository']['clone_url']
    configuration.load_configuration()  # load the rest of configuration if there is any

    logger = configuration.logger
    release_bot = ReleaseBot(configuration)

    logger.info("Resolving opened issue")
    release_bot.git.pull()
    try:
        release_bot.load_release_conf()
        if (release_bot.new_release.trigger_on_issue and
                release_bot.find_open_release_issues()):
            if release_bot.new_release.labels is not None:
                release_bot.project.add_issue_labels(
                    release_bot.new_pr.issue_number,
                    release_bot.new_release.labels)
            release_bot.make_release_pull_request()
    except ReleaseException as exc:
        logger.error(exc)


def handle_pr(webhook_payload):
    """Handler for merged PR"""
    # configuration.configuration = Path(
    #     '/Users/marusinm/Documents/Python/tmp/bot-test-conf/conf.yaml').resolve()
    configuration.configuration = Path(getenv("CONF_PATH", "/secrets/prod/conf.yaml")).resolve()

    # add configuration from Github webhook
    configuration.repository_name = webhook_payload['repository']['name']
    configuration.repository_owner = webhook_payload['repository']['owner']['login']
    configuration.github_username = webhook_payload['pull_request']['user']['login']
    configuration.clone_url = webhook_payload['repository']['clone_url']
    configuration.load_configuration()  # load the rest of configuration if there is any

    logger = configuration.logger
    release_bot = ReleaseBot(configuration)

    logger.info("Resolving opened PR")
    release_bot.git.pull()
    try:
        release_bot.load_release_conf()
        if release_bot.find_newest_release_pull_request():
            release_bot.make_new_github_release()
            # Try to do PyPi release regardless whether we just did github release
            # for case that in previous iteration (of the 'while True' loop)
            # we succeeded with github release, but failed with PyPi release
            release_bot.make_new_pypi_release()
    except ReleaseException as exc:
        logger.error(exc)

    msg = ''.join(release_bot.github.comment)
    release_bot.project.pr_comment(release_bot.new_release.pr_number, msg)
    release_bot.github.comment = []  # clean up


