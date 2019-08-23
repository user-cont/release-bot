"""
Unit tests for github module
"""

from flexmock import flexmock
from ogr.abstract import GitTag, GitProject
from ogr.services.github import GithubRelease

from release_bot.configuration import configuration
from release_bot.git import Git
from release_bot.github import Github


def test_latest_release():
    r1 = GithubRelease(
                tag_name='',
                url='',
                created_at='',
                tarball_url='',
                git_tag=GitTag(name='0.0.1', commit_sha='123'),
                project=flexmock(GitProject),
                raw_release=flexmock(title='0.0.1')
                )

    r2 = GithubRelease(
        tag_name='',
        url='',
        created_at='',
        tarball_url='',
        git_tag=GitTag(name='0.0.2', commit_sha='123'),
        project=flexmock(GitProject),
        raw_release=flexmock(title='0.0.2')
    )

    mocked_releases = [r1, r2]

    git = flexmock(Git)
    c = flexmock(configuration)
    c.project = flexmock(get_releases=lambda: mocked_releases)
    github = Github(c, git)

    obtained_release = github.latest_release()
    assert obtained_release == "0.0.2"

    mocked_releases = []
    c.project = flexmock(get_releases=lambda: mocked_releases)
    github = Github(c, git)
    obtained_release = github.latest_release()
    assert obtained_release == "0.0.0"
