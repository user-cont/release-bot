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
            path = Path(args.configuration)
            if not path.is_absolute():
                args.configuration = path.resolve()
            if not path.is_file():
                configuration.logger.error(
                    f"Supplied configuration file is not found: {args.configuration}")
                exit(1)
        if args.debug:
            configuration.logger.setLevel(logging.DEBUG)
        for key, value in vars(args).items():
            setattr(configuration, key, value)
