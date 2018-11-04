import requests
from dcosdeploy.auth import get_base_url, get_auth


class EdgeLbAdapter(object):
    def __init__(self):
        self.base_url = get_base_url() + "/service/edgelb/"

    def get_pools(self):
        """Retrive a list of pool names"""
        response = requests.get(self.base_url + "v2/pools", auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Failed to list pools")
        data = response.json()
        for pool in data:
            yield pool["name"]

    def get_pool(self, name):
        """Get config for a specific pool"""
        response = requests.get(self.base_url + "v2/pools/%s" % name, auth=get_auth(), verify=False)
        if not response.ok:
            print(response.text)
            raise Exception("Failed to get pool")
        return response.json()

    def create_pool(self, config):
        """Create a new pool"""
        response = requests.post(self.base_url + "v2/pools", json=config, auth=get_auth(), verify=False)
        if not response.ok:
            raise Exception("Could not create pool %s: %s " % (config["name"], response.text))

    def update_pool(self, config):
        """Update an existing pool config"""
        response = requests.put(self.base_url + "v2/pools/%s" % config["name"], json=config, auth=get_auth(), verify=False)
        if not response.ok:
            raise Exception("Could not update pool %s: %s " % (config["name"], response.text))

    def ping(self):
        response = requests.get(self.base_url + "ping", auth=get_auth(), verify=False)
        if not response.ok:
            if response.status_code == 503:
                return False
            else:
                raise Exception("Could not get ping from edgelb: %s" % response.text)
        return True
