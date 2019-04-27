import sys
import requests
from dcosdeploy.auth import get_base_url, get_auth

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def verify_connectivity():
    # Dummy call to verify if connection and authentication token work
    response = requests.get(get_base_url()+"/mesos_dns/v1/hosts/master.mesos", auth=get_auth(), verify=False)
    if not response.ok:
        print("Authentication failed. Please run `dcos auth login`.")
        sys.exit(1)
            