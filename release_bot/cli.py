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

import argparse
import logging
from pathlib import Path

from .configuration import configuration


class CLI:
    @staticmethod
    def parse_arguments():
        """Parse application arguments"""
        parser = argparse.ArgumentParser(description="Automatic releases bot", prog='release-bot')
        parser.add_argument("-d", "--debug", help="turn on debugging output",
                            action="store_true", default=False)
        parser.add_argument("-c", "--configuration", help="use custom YAML configuration",
                            default='')
        parser.add_argument("-v", "--version", help="display program version", action='version',
                            version=f"%(prog)s {configuration.version}")
        parser.add_argument("-k", "--keytab", help="keytab file for fedora", default='')

        args = parser.parse_args()

        if args.configuration:
            args.configuration = Path(args.configuration).resolve()
            if not args.configuration.is_file():
                configuration.logger.error(
                    f"Supplied configuration file is not found: {args.configuration}")
                exit(1)

        if args.debug:
            configuration.logger.setLevel(logging.DEBUG)
        for key, value in vars(args).items():
            setattr(configuration, key, value)
