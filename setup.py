import yaml

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


def get_requirements():
    with open("./requirements.txt") as file:
        return file.readlines()


def get_version():
    with open("./release-conf.yaml") as file:
        conf = yaml.load(file)
        return conf['version']


setup(
    name='release-bot',
    version=get_version(),
    py_modules=['release_bot'],
    package_data={
        'conf': ['release-conf.yaml']
    },
    python_requires='>=3.6',
    url='https://github.com/kosciCZ/release-bot/',
    license='GPLv3+',
    author='Red Hat',
    author_email='user-cont@redhat.com',
    description='Automated releasing from GitHub repositories',
    install_requires=get_requirements(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3'
    ],
    entry_points={'console_scripts': [
            'release-bot=release_bot:main',
        ]}
)
