from ..auth import get_base_url
from ..base import APIRequestException
from ..util import http
from ..util.output import echo_error


class EdgeLbAdapter:
    def __init__(self):
        self.base_url = get_base_url() + "/service/"

    def get_pools(self, api_server):
        """Retrive a list of pool names"""
        response = http.get(self.base_url + api_server + "/v2/pools")
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Failed to list pools", response)
        data = response.json()
        for pool in data:
            yield pool["name"]

    def get_pool(self, api_server, name):
        """Get config for a specific pool"""
        response = http.get(self.base_url + api_server + "/v2/pools/%s" % name)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Failed to get pool", response)
        return response.json()

    def create_pool(self, api_server, config):
        """Create a new pool"""
        response = http.post(self.base_url + api_server + "/v2/pools", json=config)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Could not create pool %s" % config["name"], response)

    def update_pool(self, api_server, config):
        """Update an existing pool config"""
        response = http.put(self.base_url + api_server + "/v2/pools/%s" % config["name"], json=config)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Could not update pool %s" % config["name"], response)

    def delete_pool(self, api_server, name):
        response = http.delete(self.base_url + api_server + "/v2/pools/%s" % name)
        if response.ok:
            return True
        elif response.status_code == 404:
            return False
        else:
            echo_error(response.text)
            raise APIRequestException("Unknown error occured", response)

    def ping(self, api_server):
        response = http.get(self.base_url + api_server + "/ping")
        if not response.ok:
            if response.status_code == 503:
                return False
            elif response.status_code == 404:
                return False
            else:
                echo_error(response.text)
                raise APIRequestException("Could not get ping from edgelb", response)
        return True

    def update_pool_template(self, api_server, pool_name, template):
        response = http.put(self.base_url + api_server + "/v2/pools/%s/lbtemplate" % pool_name,
                            data=template.encode('utf-8'), headers={'Content-Type': 'text/plain'})
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Could not update template for pool %s" % pool_name, response)

    def get_pool_template(self, api_server, pool_name):
        response = http.get(self.base_url + api_server + "/v2/pools/%s/lbtemplate" % pool_name)
        if not response.ok:
            echo_error(response.text)
            raise APIRequestException("Failed to get pool template", response)
        return response.text
