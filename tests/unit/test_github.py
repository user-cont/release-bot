"""
Unit tests for github module
"""

import pytest
from flexmock import flexmock

from release_bot.github import Github
from tests.conftest import prepare_conf


class MockedResponse(object):
    def __init__(self, q):
        self.q = q

    def json(self):
        return self.q


def mock_latest_release():
    data = {'data': {'repository': {'releases': {'edges': [{'cursor': 'trololollololl',
                                                            'node': {'isDraft': False,
                                                                     'isPrerelease': False,
                                                                     'name': '0.6.0'}}]}}}}

    def no_release():
        def r(_):
            return MockedResponse({'data': {'repository': {'releases': {'edges': []}}}})
        flexmock(Github, query_repository=r)
        return "0.0.0"

    def good_release():
        def r(_):
            return MockedResponse(data)
        flexmock(Github, query_repository=r)
        return "0.6.0"

    def draft_release():
        draft_data = {'data': {'repository': {'releases': {'edges': [{'cursor': 'trololollololl',
                                                                      'node': {'isDraft': True,
                                                                               'isPrerelease': False,
                                                                               'name': '1.0.0'}}]}}}}
        flexmock(Github).should_receive("query_repository")\
            .and_return(MockedResponse(draft_data))\
            .and_return(MockedResponse(data))
        return "0.6.0"

    def pre_release():
        pre_data = {'data': {'repository': {'releases': {'edges': [{'cursor': 'trololollololl',
                                                                    'node': {'isDraft': False,
                                                                             'isPrerelease': True,
                                                                             'name': '1.0.0'}}]}}}}
        flexmock(Github).should_receive("query_repository")\
            .and_return(MockedResponse(pre_data))\
            .and_return(MockedResponse(data))
        return "0.6.0"

    return (
        no_release,
        good_release,
        draft_release,
        pre_release
    )


@pytest.mark.parametrize("expected_f", mock_latest_release())
def test_latest_release(expected_f):
    expected = expected_f()
    co = prepare_conf()
    g = Github(co, None)
    assert g.latest_release() == expected
