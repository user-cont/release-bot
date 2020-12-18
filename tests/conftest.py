import os

from release_bot.configuration import configuration


def prepare_conf():
    configuration.set_logging(level=10)
    configuration.debug = True
    configuration.github_token = os.environ.get("GITHUB_TOKEN")
    return configuration
