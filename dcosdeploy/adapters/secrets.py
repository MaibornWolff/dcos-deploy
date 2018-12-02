import requests
from dcosdeploy.auth import get_base_url, get_auth


class SecretsAdapter(object):
    def __init__(self):
        self.base_url = get_base_url() + "/secrets/v1/"
        self._cache_secrets_list = None

    def list_secrets(self):
        """Retrive a list of secrets names"""
        if not self._cache_secrets_list:
            response = requests.get(self.base_url + "secret/default/?list=true", auth=get_auth(), verify=False)
            if not response.ok:
                print(response.text)
                raise Exception("Failed to list secrets")
            self._cache_secrets_list = response.json()["array"]
        return self._cache_secrets_list

    def get_secret(self, name):
        """Get value of a specific secret"""
        if name[0] == "/":
            name = name[1:]
        response = requests.get(self.base_url + "secret/default/%s" % name, auth=get_auth(), verify=False)
        if response.status_code == 404:
            return None
        if not response.ok:
            print(response.text)
            raise Exception("Failed to get secret")
        if response.headers.get("Content-Type") == "application/json":
            return response.json()["value"]
        else:
            return response.content

    def write_secret(self, name, value=None, file_content=None, update=True):
        """Write a secret, set either value or file_content but not both."""
        if update:
            func = requests.patch
        else:
            func = requests.put
        if name[0] == "/":
            name = name[1:]
        path = self.base_url + "secret/default/%s" % name
        if value:
            data = {"value": value}
            response = func(path, json=data, auth=get_auth(), verify=False)
        elif file_content:
            response = func(path, data=file_content, headers={'Content-Type': 'application/octet-stream'}, auth=get_auth(), verify=False)
        else:
            raise Exception("You must either specify value or file_content")
        if not response.ok:
            print(response.text)
            raise Exception("Failed to create secret")

    def delete_secret(self, name):
        response = requests.delete(self.base_url + "secret/default/%s" % name, auth=get_auth(), verify=False)
        if response.status_code == 404:
            return
        if not response.ok:
            raise Exception("Could not delete secret %s: %s " % (name, response.text))
