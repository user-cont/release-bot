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

from release_bot.celerizer import celery_app


class GithubWebhooksHandler(View):
    """
        Handler for github callbacks.
    """

    def __init__(self, conf):
        self.logger = conf.logger

    def dispatch_request(self):
        self.logger.info(f'New github webhook call from detected')
        if request.is_json:
            celery_app.send_task(name="task.celery_task.parse_web_hook_payload",
                                 kwargs={"webhook_payload": request.get_json()})
        else:
            self.logger.error("This webhook doesn't contain JSON")
        return jsonify(result={"status": 200})
