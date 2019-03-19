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

class NewPR:

    def __init__(self):
        self.version = None
        self.issue_id = None
        self.issue_number = None
        self.labels = None
        self.pr_url = None
        self.previous_version = None
        self.repo = None

    def update_new_pr_details(self, version, issue_id, issue_number, labels):
        self.version = version
        self.issue_id = issue_id
        self.issue_number = issue_number
        self.labels = labels
