try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


def get_requirements():
    with open("./requirements.txt") as file:
        return file.readlines()


version = {}
with open("./release_bot/version.py") as fp:
    exec(fp.read(), version)

setup(
    name='release-bot',
    version=version["__version__"],
    packages=['release_bot'],
    python_requires='>=3.6',
    url='https://github.com/user-cont/release-bot',
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
        'release-bot=release_bot.releasebot:main',
    ]}
)
