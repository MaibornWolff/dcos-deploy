from ..auth import get_base_url
from ..util import http
from ..util.output import echo_error


class EdgeLbAdapter(object):
    def __init__(self):
        self.base_url = get_base_url() + "/service/"

    def get_pools(self, api_server):
        """Retrive a list of pool names"""
        response = http.get(self.base_url + api_server + "/v2/pools")
        if not response.ok:
            echo_error(response.text)
            raise Exception("Failed to list pools")
        data = response.json()
        for pool in data:
            yield pool["name"]

    def get_pool(self, api_server, name):
        """Get config for a specific pool"""
        response = http.get(self.base_url + api_server + "/v2/pools/%s" % name)
        if not response.ok:
            echo_error(response.text)
            raise Exception("Failed to get pool")
        return response.json()

    def create_pool(self, api_server, config):
        """Create a new pool"""
        response = http.post(self.base_url + api_server + "/v2/pools", json=config)
        if not response.ok:
            raise Exception("Could not create pool %s: %s " % (config["name"], response.text))

    def update_pool(self, api_server, config):
        """Update an existing pool config"""
        response = http.put(self.base_url + api_server + "/v2/pools/%s" % config["name"], json=config)
        if not response.ok:
            raise Exception("Could not update pool %s: %s " % (config["name"], response.text))

    def delete_pool(self, api_server, name):
        response = http.delete(self.base_url + api_server + "/v2/pools/%s" % name)
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            raise Exception("Unknown error occured: %s" % response.text)

    def ping(self, api_server):
        response = http.get(self.base_url + api_server + "/ping")
        if not response.ok:
            if response.status_code == 503:
                return False
            elif response.status_code == 404:
                return False
            else:
                raise Exception("Could not get ping from edgelb: %s" % response.text)
        return True
