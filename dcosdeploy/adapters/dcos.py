import uuid
import base64
import json
import sys
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from dcosdeploy.auth import get_base_url, get_auth

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class DcosAdapter(object):
    def __init__(self):
        self.base_url = get_base_url()

    def verify_connectivity(self):
        # Dummy call to verify if connection and authentication token work
        response = requests.get(self.base_url+"/mesos_dns/v1/hosts/master.mesos", auth=get_auth(), verify=False)
        return response.ok

    def get_cluster_info(self):
        response = requests.get(self.base_url+"/dcos-metadata/dcos-version.json", auth=get_auth(), verify=False)
        if not response.ok:
            raise Exception("Unknown error occured: %s" % response.text)
        info = response.json()
        return dict(version=info["version"], variant=info["dcos-variant"])
    
    def get_nodes(self):
        response = requests.get(self.base_url+"/system/health/v1/nodes", auth=get_auth(), verify=False)
        if not response.ok:
            raise Exception("Unknown error occured: %s" % response.text)
        return response.json()["nodes"]

    def get_node_counts(self):
        master_count = 0
        agent_count = 0
        public_agent_count = 0
        for node in self.get_nodes():
            if node["role"] == "master":
                master_count += 1
            elif node["role"] == "agent":
                agent_count += 1
            elif node["role"] == "agent_public":
                public_agent_count += 1
        return dict(master=master_count, agent=agent_count, public_agent=public_agent_count)



def fail_on_missing_connectivity():
    connected = DcosAdapter().verify_connectivity()
    if not connected:
        print("Authentication failed. Please run `dcos auth login`.")
        sys.exit(1)
