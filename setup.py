from setuptools import setup, find_packages


def get_requirements():
    with open("./requirements.txt") as fp:
        return fp.readlines()


version = {}
with open("./release_bot/version.py") as fp:
    exec(fp.read(), version)


setup(version=version["__version__"],
      packages=find_packages(exclude=['tests*']),
      install_requires=get_requirements(), )
