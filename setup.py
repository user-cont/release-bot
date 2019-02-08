try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


def get_requirements():
    with open("./requirements.txt") as fp:
        return fp.readlines()


version = {}
with open("./release_bot/version.py") as fp:
    exec(fp.read(), version)


setup(version=version["__version__"],
      packages=['release_bot'],
      install_requires=get_requirements(), )
