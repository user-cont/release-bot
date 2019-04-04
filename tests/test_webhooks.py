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

import pytest
from flask import Flask
from flexmock import flexmock
import json

from release_bot.webhooks import GithubWebhooksHandler


@pytest.fixture()
def flask_instance():
    """
    Create flask instance for tests.
    Mock all necessary dependencies.
    :return: flask instance for tests
    """

    release_bot = flexmock()
    configuration = flexmock(
        logger=flexmock(),
        repository_owner='repo-owner',
        repository_name='repo-name',
        version="0.0.0"
    )

    flexmock(
        configuration.logger,
        info="info",
        error="error",
        debug="debug")

    app = Flask(__name__)
    app.add_url_rule('/webhook-handler/',
                     view_func=GithubWebhooksHandler.as_view('github_webhooks_handler',
                                                             release_bot=release_bot,
                                                             conf=configuration),
                     methods=['POST', ])

    test_client = app.test_client()
    return test_client


def test_bad_requests(flask_instance):
    """Test GET method request on different routes"""
    response = flask_instance.get('/')
    assert response.status_code == 404
    response = flask_instance.get('/webhook-handler/')
    assert response.status_code == 405


def test_json_requests(flask_instance):
    """Test if POST method which contains JSON call correct methods"""
    flexmock(GithubWebhooksHandler).should_receive("handle_issue").once()
    flexmock(GithubWebhooksHandler).should_receive("handle_pr").once()

    json_dummy_dict = {
      'dummy': 'dummy',
    }
    # will not call handle_issue or handle_pr within GithubWebhooksHandler instance
    response = flask_instance.post('/webhook-handler/', data=json.dumps(json_dummy_dict),
                                   content_type='application/json')
    assert response.status_code == 200

    json_expected_dict = {
        'action': 'opened',
        'issue': {
            'dummy': 'dummy'
        }
    }
    # call handle_issue once within GithubWebhooksHandler instance
    response = flask_instance.post('/webhook-handler/', data=json.dumps(json_expected_dict),
                                   content_type='application/json')
    assert response.status_code == 200

    json_expected_dict = {
        'action': 'closed',
        'pull_request': {
            'merged': True,
            'dummy': 'dummy'
        }
    }
    # call handle_pr once within GithubWebhooksHandler instance
    response = flask_instance.post('/webhook-handler/', data=json.dumps(json_expected_dict),
                                   content_type='application/json')
    assert response.status_code == 200

