"""
Unit tests for github module
"""

from flexmock import flexmock
from ogr.abstract import Release, GitTag

from release_bot.github import Github
from release_bot.git import Git
from release_bot.configuration import configuration


def test_latest_release():
    mocked_releases = [
        Release(title='0.0.1',
                body='',
                tag_name='',
                url='',
                created_at='',
                tarball_url='',
                git_tag=GitTag(name='0.0.1', commit_sha='123')
                ),
        Release(title='0.0.2',
                body='',
                tag_name='',
                url='',
                created_at='',
                tarball_url='',
                git_tag=GitTag(name='0.0.2', commit_sha='123')
                )
    ]

    git = flexmock(Git)
    c = flexmock(configuration)
    c.project = flexmock(get_releases=lambda: mocked_releases)
    github = Github(c, git)

    obtained_release = github.latest_release()
    assert obtained_release == '0.0.2'

    mocked_releases = []
    c.project = flexmock(get_releases=lambda: mocked_releases)
    github = Github(c, git)
    obtained_release = github.latest_release()
    assert obtained_release == '0.0.0'
