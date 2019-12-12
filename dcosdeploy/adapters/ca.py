from ..auth import get_base_url
from ..util import http


class CAAdapter(object):
    def __init__(self):
        self.base_url = get_base_url() + "/ca/api/v2/"

    def generate_key(self, dn, hosts=list(), algorithm="rsa", size=2048):
        data = {
          "names": [
            dn
          ],
          "hosts": hosts,
          "key": {
            "algo": algorithm,
            "size": size
          }
        }
        response = http.post(self.base_url+"newkey", json=data)
        if not response.ok:
            raise Exception("Failed to generate key: %s" % response.text)
        return response.json()["result"]["certificate_request"], response.json()["result"]["private_key"]

    def sign_csr(self, csr, hosts=list()):
        data = {
          "certificate_request": csr,
          "hosts": hosts
        }
        response = http.post(self.base_url+"sign", json=data)
        if not response.ok:
            raise Exception("Failed to sign cert: %s" % response.text)
        return response.json()["result"]["certificate"]
