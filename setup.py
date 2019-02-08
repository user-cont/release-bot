from pathlib import Path
from setuptools import setup, find_packages


version = {}
with open("./release_bot/version.py") as fp:
    exec(fp.read(), version)


setup(version=version["__version__"],
      packages=find_packages(exclude=['tests*']),
      install_requires=Path("./requirements.txt").read_text(), )
