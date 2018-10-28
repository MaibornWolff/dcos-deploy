import requests
from dcosdeploy.auth import get_auth, get_base_url


class CAAdapter(object):
    def __init__(self):
        self.base_url = get_base_url() + "/ca/api/v2/"

    def generate_key(self, dn, hosts=list(), size=2048):
        data = {
          "names": [
            dn
          ],
          "hosts": hosts,
          "key": {
            "algo": "rsa",
            "size": size
          }
        }
        response = requests.post(self.base_url+"newkey", json=data, auth=get_auth(), verify=False)
        if not response.ok:
            raise Exception("Failed to generate key: %s" % response.text)
        return response.json()["result"]["certificate_request"], response.json()["result"]["private_key"]

    def sign_csr(self, csr, hosts=list()):
        data = {
          "certificate_request": csr,
          "hosts": hosts
        }
        response = requests.post(self.base_url+"sign", json=data, auth=get_auth(), verify=False)
        if not response.ok:
            raise Exception("Failed to sign cert: %s" % response.text)
        return response.json()["result"]["certificate"]
