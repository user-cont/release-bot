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

from os import getenv
from celery import Celery


class Celerizer:
    """Creates instance used by celery lib"""
    def __init__(self):
        self._celery_app = None

    @property
    def celery_app(self):
        if self._celery_app is None:
            redis_host = getenv("REDIS_SERVICE_HOST", "localhost")
            redis_port = getenv("REDIS_SERVICE_PORT", "6379")
            redis_db = getenv("REDIS_SERVICE_DB", "0")
            redis_url = "redis://{host}:{port}/{db}".format(
                host=redis_host, port=redis_port, db=redis_db
            )

            # http://docs.celeryproject.org/en/latest/reference/celery.html#celery.Celery
            self._celery_app = Celery(backend=redis_url, broker=redis_url)
        return self._celery_app


celerizer = Celerizer()
celery_app = celerizer.celery_app
