#!/usr/bin/python3

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
from setuptools import setup

REQUIREMENTS = Path("./requirements.txt").read_text()
TEST_REQUIREMENTS = Path("./test-requirements.txt").read_text()

setup(
    # to install test requirements, run `pip install -e ".[tests]"`
    extras_require={
        'tests': TEST_REQUIREMENTS
    },
    install_requires=REQUIREMENTS
)
