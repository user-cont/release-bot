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
