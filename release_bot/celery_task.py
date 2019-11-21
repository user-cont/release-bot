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

from pathlib import Path
from os import getenv
import redis

from release_bot.celerizer import celery_app
from release_bot.exceptions import ReleaseException
from release_bot.configuration import configuration
from release_bot.releasebot import ReleaseBot

DEFAULT_CONF_FILE = "/home/release-bot/.config/conf.yaml"


@celery_app.task(name="task.celery_task.parse_web_hook_payload")
def parse_web_hook_payload(webhook_payload):
    """
    Parse json webhook payload callback
    :param webhook_payload: json from github webhook
    """
    db = get_redis_instance()
    if 'issue' in webhook_payload.keys():
        if webhook_payload['action'] == 'opened':
            handle_issue(webhook_payload, db)
    elif 'pull_request' in webhook_payload.keys():
        if webhook_payload['action'] == 'closed':
            if webhook_payload['pull_request']['merged'] is True:
                handle_pr(webhook_payload, db)
    elif 'installation' in webhook_payload.keys():
        if webhook_payload['action'] == 'added':  # detect new repo installation
            installation_id = webhook_payload['installation']['id']
            repositories_added = webhook_payload['repositories_added']
            save_new_installations(installation_id, repositories_added, db)

        if webhook_payload['action'] == 'removed':  # detect when repo uninstall app
            repositories_removed = webhook_payload['repositories_removed']
            delete_installations(repositories_removed, db)


def get_redis_instance():
    db = redis.Redis(
        host=getenv("REDIS_SERVICE_HOST", "localhost"),
        port=getenv("REDIS_SERVICE_PORT", "6379"),
        db=1,  # 0 is used by Celery
        decode_responses=True,
    )
    return db


def set_configuration(webhook_payload, db, issue=True):
    """
    Prepare configuration from parsed web hook payload and return ReleaseBot instance with logger
    :param webhook_payload: payload from web hook
    :param issue: if true parse Github issue payload otherwise parse Github pull request payload
    :return: ReleaseBot instance, configuration logger
    """
    configuration.configuration = Path(getenv("CONF_PATH",
                                              DEFAULT_CONF_FILE)).resolve()

    # add configuration from Github webhook
    configuration.repository_name = webhook_payload['repository']['name']
    configuration.repository_owner = webhook_payload['repository']['owner']['login']
    if issue:
        configuration.github_username = webhook_payload['issue']['user']['login']
    else:
        configuration.github_username = webhook_payload['pull_request']['user']['login']

    repo_installation_id = db.get(webhook_payload['repository']['full_name'])
    configuration.github_app_installation_id = repo_installation_id

    configuration.load_configuration()  # load the rest of configuration if there is any

    # create url for github app to enable access over http
    configuration.clone_url = f'https://x-access-token:' \
        f'{configuration.github_token}@github.com/' \
        f'{configuration.repository_owner}/{configuration.repository_name}.git'

    return ReleaseBot(configuration), configuration.logger


def handle_issue(webhook_payload, db):
    """
    Handler for newly opened issues
    :param webhook_payload: json data from webhook
    :param db: Redis instance
    :return:
    """
    release_bot, logger = set_configuration(webhook_payload, db=db, issue=True)

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


def handle_pr(webhook_payload, db):
    """
    Handler for merged PR
    :param webhook_payload: json data from webhook
    :param db: Redis instance
    :return:
    """
    release_bot, logger = set_configuration(webhook_payload, db=db, issue=False)

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


def save_new_installations(installation_id, repositories_added, db):
    """
    Save repo which installed release-bot github app with it installation id
    :param installation_id: installation identifier from initial installation web hook
    :param repositories_added: repositories which user choose for release-bot installation
    :param db: Redis instance
    :return: True if data was saved successfully into Redis
    """
    with db.pipeline() as pipe:
        for repo in repositories_added:
            pipe.set(repo["full_name"], installation_id)
        pipe.execute()
    return db.save()


def delete_installations(repositories_removed, db):
    """
    Delete repo from Redis when user uninstall release-bot app from such repo
    :param repositories_removed: repositories which user choose to uninstall from the release-bot
    :param db: Redis instance
    :return: True if data was deleted successfully into Redis
    """
    with db.pipeline() as pipe:
        for repo in repositories_removed:
            pipe.delete(repo["full_name"])
        pipe.execute()
    return db.save()
