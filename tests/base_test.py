import unittest
from dcosdeploy.base import APIRequestException


class BaseTest(unittest.TestCase):
    def test_apirequestexception(self):
        expression = "foo"
        response = "bar"
        with self.assertRaises(APIRequestException) as context:
            raise APIRequestException(expression, response)
        self.assertEqual(context.exception.args[0], expression)
        self.assertEqual(context.exception.response, response)
        