import io
import unittest
from unittest import mock
import requests_mock
from dcosdeploy.util import http
from dcosdeploy.auth import StaticTokenAuth


@mock.patch("dcosdeploy.util.http.get_base_url", lambda: "https://my.cluster")
@mock.patch("dcosdeploy.util.http.get_auth", lambda: StaticTokenAuth("testtoken"))
class HttpTest(unittest.TestCase):

    def _test_verb(self, verb):
        with requests_mock.Mocker() as m:
            getattr(m, verb)('https://my.cluster/foobar', text='foobar')
            response = getattr(http, verb)("/foobar", headers={"Foo": "bar"})
            self.assertEqual(response.text, "foobar")
            self.assertEqual(m.last_request.headers.get("Authorization", ""), "token=testtoken")
            self.assertEqual(m.last_request.headers.get("Foo", ""), "bar")

    def test_http(self):
        self._test_verb("get")
        self._test_verb("post")
        self._test_verb("put")
        self._test_verb("delete")
        self._test_verb("patch")

        with requests_mock.Mocker() as m:
            m.get('https://my.cluster/foobar', text='foobar')
            response = http.get("foobar")
            self.assertEqual(response.text, "foobar")

        with requests_mock.Mocker() as m:
            m.get('https://other.domain', text='foobar')
            response = http.get("https://other.domain")
            self.assertEqual(response.text, "foobar")
