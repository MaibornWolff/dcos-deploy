from ..auth import get_base_url
from ..util import http
from ..util.output import echo_error


class SecretsAdapter(object):
    def __init__(self):
        self.base_url = get_base_url() + "/secrets/v1/"
        self._cache_secrets_list = None

    def list_secrets(self):
        """Retrive a list of secrets names"""
        if not self._cache_secrets_list:
            response = http.get(self.base_url + "secret/default/?list=true")
            if not response.ok:
                echo_error(response.text)
                raise Exception("Failed to list secrets")
            self._cache_secrets_list = response.json()["array"]
        return self._cache_secrets_list

    def get_secret(self, name):
        """Get value of a specific secret"""
        if name[0] == "/":
            name = name[1:]
        response = http.get(self.base_url + "secret/default/%s" % name)
        if response.status_code == 404:
            return None
        if not response.ok:
            echo_error(response.text)
            raise Exception("Failed to get secret")
        if response.headers.get("Content-Type") == "application/json":
            return response.json()["value"]
        else:
            return response.content

    def write_secret(self, name, value=None, file_content=None, update=True):
        """Write a secret, set either value or file_content but not both."""
        if update:
            func = http.patch
        else:
            func = http.put
        if name[0] == "/":
            name = name[1:]
        path = self.base_url + "secret/default/%s" % name
        if value:
            data = {"value": value}
            response = func(path, json=data)
        elif file_content:
            response = func(path, data=file_content, headers={'Content-Type': 'application/octet-stream'})
        else:
            raise Exception("You must either specify value or file_content")
        if not response.ok:
            echo_error(response.text)
            raise Exception("Failed to create secret")

    def delete_secret(self, name):
        response = http.delete(self.base_url + "secret/default/%s" % name)
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            raise Exception("Could not delete secret %s: %s " % (name, response.text))
