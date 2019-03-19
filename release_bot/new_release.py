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

class NewRelease:

    def __init__(self):
        # Init to default values.
        self.changelog = None
        self.author_name = None
        self.author_email = None
        self.pypi = None
        self.trigger_on_issue = None
        self.labels = None
        self.pr_id = None
        self.commitish = None
        self.version = None

    def update(self, changelog, author_name, author_email, pypi, trigger_on_issue, labels):
        # Update release-conf data
        self.changelog = changelog
        self.author_name = author_name
        self.author_email = author_email
        self.pypi = pypi
        self.trigger_on_issue = trigger_on_issue
        self.labels = labels

    def update_pr_details(self, version, author_name, author_email, pr_id, commitish):
        # Update attributes for making a PR
        self.author_name = author_name
        self.author_email = author_email
        self.pr_id = pr_id
        self.version = version
        self.commitish = commitish
