import io
import os
import unittest
from unittest import mock
from dcosdeploy.util import global_config, output


FOOBAR = "foobar"


class OutputTest(unittest.TestCase):
    def test_echo(self):
        global_config.silent = False
        stdout = _mock_output(lambda: output.echo(FOOBAR))
        self.assertEqual(stdout, FOOBAR+"\n")
        global_config.silent = True
        stdout = _mock_output(lambda: output.echo(FOOBAR))
        self.assertEqual(stdout, "")

    def test_echo_error(self):
        stderr = _mock_output(lambda: output.echo_error(FOOBAR), stderr=True)
        self.assertEqual(stderr, FOOBAR+"\n")

    def test_echo_debug(self):
        global_config.silent = False
        stdout = _mock_output(lambda: output.echo_debug(FOOBAR))
        self.assertEqual(stdout, "")
        global_config.debug = True
        stdout = _mock_output(lambda: output.echo_debug(FOOBAR))
        self.assertEqual(stdout, FOOBAR+"\n")
        global_config.silent = True
        global_config.debug = False

    def test_echo_diff(self):
        global_config.silent = True
        stdout = _mock_output(lambda: output.echo_diff(FOOBAR, FOOBAR))
        self.assertEqual(stdout, "")
        global_config.silent = False
        global_config.debug = False
        stdout = _mock_output(lambda: output.echo_diff(FOOBAR, FOOBAR))
        self.assertEqual(stdout, FOOBAR+"\n")
        global_config.silent = False
        global_config.debug = True
        stdout = _mock_output(lambda: output.echo_diff(FOOBAR, FOOBAR))
        self.assertEqual(stdout, FOOBAR+":"+"\n"+FOOBAR+"\n")
        global_config.silent = True


def _mock_output(func, stderr=False):
    channel = "sys.stderr" if stderr else "sys.stdout"
    with mock.patch(channel, new = io.StringIO()) as fake_stdout:
        func()
        return fake_stdout.getvalue()
